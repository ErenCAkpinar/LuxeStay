from datetime import date
from decimal import Decimal

from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.test import RequestFactory
from django.test import TestCase
from django.urls import reverse

from .admin import BookingAdmin
from .models import Booking, Hotel, PaymentMethod, Review, SavedHotel, UserProfile


User = get_user_model()


class AuthenticationFlowTests(TestCase):
    def test_signup_creates_user_and_logs_in(self):
        response = self.client.post(
            reverse("signup"),
            {
                "firstName": "Ada",
                "lastName": "Lovelace",
                "email": "ada@example.com",
                "password": "StrongPass123!",
                "terms": "on",
            },
        )

        self.assertRedirects(response, reverse("dashboard"))
        self.assertTrue(User.objects.filter(email="ada@example.com").exists())

    def test_login_with_email(self):
        User.objects.create_user(
            username="ada@example.com",
            email="ada@example.com",
            password="StrongPass123!",
        )

        response = self.client.post(
            reverse("login"),
            {"email": "ada@example.com", "password": "StrongPass123!"},
        )

        self.assertRedirects(response, reverse("dashboard"))

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse("dashboard"))

        self.assertRedirects(response, f"{reverse('login')}?next={reverse('dashboard')}")


class HotelSearchTests(TestCase):
    fixtures = []

    def setUp(self):
        Hotel.objects.all().delete()
        Hotel.objects.create(
            code="h1",
            name="Azure Coast Resort & Spa",
            city="Antalya",
            country="Turkey",
            location="Antalya Beachfront, Turkey",
            category="beach",
            property_type="resort",
            amenities="Pool, WiFi, Spa",
            image_url="https://example.com/antalya.jpg",
            rating="4.8",
            review_count=1240,
            original_price=320,
            current_price=240,
            max_guests=5,
            rooms_left=4,
        )
        Hotel.objects.create(
            code="h2",
            name="Grand Bosphorus Hotel",
            city="Istanbul",
            country="Turkey",
            location="Istanbul, Turkey",
            category="city",
            property_type="hotel",
            amenities="Pool, WiFi, Spa",
            image_url="https://example.com/istanbul.jpg",
            rating="4.7",
            review_count=892,
            original_price=310,
            current_price=224,
            max_guests=4,
            rooms_left=3,
        )

    def test_destination_search_filters_hotels(self):
        response = self.client.get(reverse("hotels"), {"destination": "Antalya", "guests": "2"})

        self.assertContains(response, "Azure Coast Resort")
        self.assertNotContains(response, "Grand Bosphorus")

    def test_empty_search_shows_no_results_state(self):
        response = self.client.get(reverse("hotels"), {"destination": "Nowhere"})

        self.assertContains(response, "No matching stays found")

    def test_sidebar_filters_limit_hotel_results(self):
        response = self.client.get(
            reverse("hotels"),
            {
                "min_price": "250",
                "max_price": "230",
                "property_type": "resort",
                "amenity": "spa",
                "guest_rating": "9",
            },
        )

        self.assertContains(response, "Azure Coast Resort")
        self.assertNotContains(response, "Grand Bosphorus")
        self.assertContains(response, 'name="min_price" placeholder="Min" value="230"')
        self.assertContains(response, 'name="max_price" placeholder="Max" value="250"')
        self.assertContains(response, 'name="property_type" value="resort" checked')
        self.assertContains(response, 'name="amenity" value="spa" checked')
        self.assertContains(response, 'name="guest_rating" value="9" checked')

    def test_star_filter_uses_rating_buckets(self):
        Hotel.objects.create(
            code="h3",
            name="Budget City Hostel",
            city="Istanbul",
            country="Turkey",
            location="Istanbul, Turkey",
            category="city",
            property_type="hostel",
            amenities="WiFi",
            image_url="https://example.com/hostel.jpg",
            rating="3.8",
            review_count=110,
            original_price=100,
            current_price=80,
            max_guests=2,
            rooms_left=8,
        )

        response = self.client.get(reverse("hotels"), {"star": "3"})

        self.assertContains(response, "Budget City Hostel")
        self.assertNotContains(response, "Azure Coast Resort")
        self.assertNotContains(response, "Grand Bosphorus")
        self.assertContains(response, 'name="star" value="3" checked')

    def test_search_pages_load_date_range_guard(self):
        home_response = self.client.get(reverse("home"))
        hotels_response = self.client.get(reverse("hotels"))

        self.assertContains(home_response, "/static/shared/js/date-range.js")
        self.assertContains(hotels_response, "/static/shared/js/date-range.js")


class BookingFlowTests(TestCase):
    def setUp(self):
        Hotel.objects.all().delete()
        self.hotel = Hotel.objects.create(
            code="h1",
            name="Azure Coast Resort & Spa",
            city="Antalya",
            country="Turkey",
            location="Antalya Beachfront, Turkey",
            category="beach",
            property_type="resort",
            amenities="Pool, WiFi, Spa",
            image_url="https://example.com/antalya.jpg",
            rating="4.8",
            review_count=1240,
            original_price=320,
            current_price=240,
            max_guests=5,
            rooms_left=5,
        )
        self.user = User.objects.create_user(
            username="booker@example.com",
            email="booker@example.com",
            password="StrongPass123!",
            first_name="Booker",
            last_name="Demo",
        )
        self.client.login(username="booker@example.com", password="StrongPass123!")

    def test_payment_creates_booking_and_decrements_stock(self):
        response = self.client.post(
            reverse("guest-details"),
            {
                "hotel_code": self.hotel.code,
                "checkIn": "2026-09-10",
                "checkOut": "2026-09-14",
                "guests": "2",
                "room_name": "Junior Suite",
                "guest_first_name": "Booker",
                "guest_last_name": "Demo",
                "guest_email": "booker@example.com",
            },
        )
        self.assertRedirects(response, reverse("payment"))

        response = self.client.post(
            reverse("payment"),
            {
                "agree_terms": "on",
                "agree_cancel": "on",
                "payment_method": Booking.PAYMENT_CARD,
                "cardholder_name": "Booker Demo",
                "card_number": "4111 1111 1111 1111",
                "expiry": "12/30",
                "cvv": "123",
            },
        )

        self.assertRedirects(response, reverse("booking-confirmed"))
        booking = Booking.objects.get(user=self.user)
        self.assertEqual(len(booking.booking_reference), 9)
        self.assertEqual(booking.check_in, date(2026, 9, 10))
        self.assertEqual(booking.room_name, "Junior Suite")
        self.assertEqual(booking.total_amount, Decimal("1536.00"))
        self.hotel.refresh_from_db()
        self.assertEqual(self.hotel.rooms_left, 4)

        dashboard_response = self.client.get(reverse("dashboard"))
        self.assertContains(dashboard_response, "My Bookings")
        self.assertContains(dashboard_response, "Recent Payments")
        self.assertContains(dashboard_response, booking.display_reference)

    def test_payment_rejects_invalid_card_expiry(self):
        self.client.post(
            reverse("guest-details"),
            {
                "hotel_code": self.hotel.code,
                "checkIn": "2026-09-10",
                "checkOut": "2026-09-14",
                "guests": "2",
                "guest_first_name": "Booker",
                "guest_last_name": "Demo",
                "guest_email": "booker@example.com",
            },
        )

        response = self.client.post(
            reverse("payment"),
            {
                "agree_terms": "on",
                "agree_cancel": "on",
                "payment_method": Booking.PAYMENT_CARD,
                "cardholder_name": "Booker Demo",
                "card_number": "4111 1111 1111 1111",
                "expiry": "13/30",
                "cvv": "123",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Expiry date must be a valid future date in MM/YY format.")
        self.assertFalse(Booking.objects.filter(user=self.user).exists())

    def test_cancelled_booking_appears_cancelled_on_dashboard(self):
        booking = Booking.objects.create(
            user=self.user,
            hotel=self.hotel,
            guest_first_name="Booker",
            guest_last_name="Demo",
            guest_email="booker@example.com",
            check_in=date(2026, 6, 1),
            check_out=date(2026, 6, 5),
            guests=2,
            total_amount="1152.00",
            status=Booking.STATUS_CANCELLED,
        )

        response = self.client.get(reverse("dashboard-bookings"))

        self.assertContains(response, booking.display_reference)
        self.assertContains(response, "CANCELLED")
        self.assertContains(response, "status-cancelled")

    def test_admin_cancelling_booking_restores_room_stock(self):
        self.hotel.rooms_left = 4
        self.hotel.save(update_fields=["rooms_left"])
        booking = Booking.objects.create(
            user=self.user,
            hotel=self.hotel,
            guest_first_name="Booker",
            guest_last_name="Demo",
            guest_email="booker@example.com",
            check_in=date(2026, 6, 1),
            check_out=date(2026, 6, 5),
            guests=2,
            total_amount="1152.00",
            status=Booking.STATUS_CONFIRMED,
        )
        booking.status = Booking.STATUS_CANCELLED
        request = RequestFactory().post("/")
        request.user = User.objects.create_superuser(
            username="admin@example.com",
            email="admin@example.com",
            password="AdminPass123!",
        )

        BookingAdmin(Booking, AdminSite()).save_model(request, booking, form=None, change=True)

        booking.refresh_from_db()
        self.hotel.refresh_from_db()
        self.assertEqual(booking.status, Booking.STATUS_CANCELLED)
        self.assertEqual(self.hotel.rooms_left, 5)


class DashboardFunctionTests(TestCase):
    def setUp(self):
        Hotel.objects.all().delete()
        self.hotel = Hotel.objects.create(
            code="dash-hotel",
            name="Dashboard Bay Hotel",
            city="Antalya",
            country="Turkey",
            location="Antalya Marina, Turkey",
            category="beach",
            property_type="hotel",
            amenities="WiFi, Spa, Pool",
            image_url="https://example.com/dashboard.jpg",
            rating="4.6",
            review_count=320,
            original_price=260,
            current_price=190,
            max_guests=4,
            rooms_left=6,
        )
        self.user = User.objects.create_user(
            username="dashboard@example.com",
            email="dashboard@example.com",
            password="StrongPass123!",
            first_name="Dash",
            last_name="User",
        )
        self.booking = Booking.objects.create(
            user=self.user,
            hotel=self.hotel,
            guest_first_name="Dash",
            guest_last_name="User",
            guest_email="dashboard@example.com",
            check_in=date(2026, 7, 1),
            check_out=date(2026, 7, 4),
            guests=2,
            total_amount="684.00",
        )
        self.client.login(username="dashboard@example.com", password="StrongPass123!")

    def test_dashboard_pages_render_for_logged_in_user(self):
        names = [
            "dashboard",
            "dashboard-bookings",
            "dashboard-saved",
            "dashboard-profile",
            "dashboard-notifications",
            "dashboard-payment-methods",
            "dashboard-reviews",
            "dashboard-rewards",
        ]

        for name in names:
            with self.subTest(name=name):
                response = self.client.get(reverse(name))
                self.assertEqual(response.status_code, 200)

    def test_bookings_page_shows_current_user_booking_count(self):
        response = self.client.get(reverse("dashboard-bookings"))

        self.assertContains(response, "Showing 1 reservation")
        self.assertContains(response, self.user.email)
        self.assertContains(response, self.booking.display_reference)
        self.assertIn("no-store", response.headers["Cache-Control"])

    def test_dashboard_overview_shows_my_bookings_section(self):
        response = self.client.get(reverse("dashboard"))

        self.assertContains(response, "My Bookings")
        self.assertContains(response, "Recent Payments")
        self.assertContains(response, self.booking.display_reference)
        self.assertContains(response, self.hotel.name)
        self.assertIn("no-store", response.headers["Cache-Control"])

    def test_hotel_detail_renders_selected_hotel_and_save_form(self):
        response = self.client.get(reverse("hotel-detail"), {"id": self.hotel.code})

        self.assertContains(response, self.hotel.name)
        self.assertContains(response, self.hotel.location)
        self.assertContains(response, "Save Hotel")
        self.assertContains(response, f'name="hotel_code" value="{self.hotel.code}"')

    def test_hotel_detail_booking_widget_submits_selected_dates_to_checkout(self):
        response = self.client.get(
            reverse("hotel-detail"),
            {
                "id": self.hotel.code,
                "checkIn": "2026-09-10",
                "checkOut": "2026-09-14",
                "guests": "3",
            },
        )

        self.assertContains(response, 'action="/checkout/guest-details/" method="get"')
        self.assertContains(response, 'name="checkIn" class="widget-date-value" value="2026-09-10"')
        self.assertContains(response, 'name="checkOut" class="widget-date-value" value="2026-09-14"')
        self.assertContains(response, 'name="guests" value="3"')
        self.assertContains(response, 'name="room_name" value="Deluxe Sea View Room"')
        self.assertContains(response, "room_name=Deluxe%20Sea%20View%20Room")
        self.assertContains(response, "room_name=Junior%20Suite")
        self.assertContains(response, "/static/shared/js/date-range.js")
        self.assertContains(response, "data-booking-source")
        self.assertContains(response, "data-booking-link")

    def test_hotel_detail_widget_price_uses_selected_room(self):
        response = self.client.get(
            reverse("hotel-detail"),
            {
                "id": self.hotel.code,
                "room_name": "Junior Suite",
            },
        )

        self.assertContains(response, 'name="room_name" value="Junior Suite"')
        self.assertContains(response, 'data-deluxe-price="190"')
        self.assertContains(response, 'data-junior-price="260"')
        self.assertContains(response, '<span class="widget-price" id="w-price">$260</span>')

    def test_guest_details_summary_uses_requested_guests_and_room(self):
        response = self.client.get(
            reverse("guest-details"),
            {
                "hotel": self.hotel.code,
                "checkIn": "2026-09-10",
                "checkOut": "2026-09-14",
                "guests": "3",
                "room_name": "Junior Suite",
            },
        )

        self.assertContains(response, 'name="guests" value="3"')
        self.assertContains(response, 'name="room_name" value="Junior Suite"')
        self.assertContains(response, '<span id="bs-guests">3 Adults</span>')
        self.assertContains(response, '<span id="bs-room">Junior Suite</span>')
        self.assertContains(response, '<span id="bs-room-total">$1040</span>')
        self.assertContains(response, '<span id="bs-total">$1248</span>')

    def test_guest_details_moves_check_out_after_check_in(self):
        response = self.client.get(
            reverse("guest-details"),
            {
                "hotel": self.hotel.code,
                "checkIn": "2026-09-10",
                "checkOut": "2026-09-09",
            },
        )

        self.assertContains(response, "10 Sep 2026")
        self.assertContains(response, "11 Sep 2026")

    def test_bookings_page_includes_matching_guest_email_booking(self):
        other_user = User.objects.create_user(
            username="other@example.com",
            email="other@example.com",
            password="StrongPass123!",
        )
        email_booking = Booking.objects.create(
            user=other_user,
            hotel=self.hotel,
            guest_first_name="Dash",
            guest_last_name="Email",
            guest_email=self.user.email,
            check_in=date(2026, 8, 1),
            check_out=date(2026, 8, 4),
            guests=2,
            total_amount="570.00",
        )

        response = self.client.get(reverse("dashboard-bookings"))

        self.assertContains(response, self.booking.display_reference)
        self.assertContains(response, email_booking.display_reference)

    def test_saved_hotel_toggle_writes_to_database(self):
        response = self.client.post(
            reverse("toggle-saved-hotel"),
            {"hotel_code": self.hotel.code, "next": reverse("dashboard-saved")},
        )

        self.assertRedirects(response, reverse("dashboard-saved"))
        self.assertTrue(SavedHotel.objects.filter(user=self.user, hotel=self.hotel).exists())

        dashboard_response = self.client.get(reverse("dashboard"))
        saved_response = self.client.get(reverse("dashboard-saved"))
        self.assertContains(dashboard_response, self.hotel.name)
        self.assertContains(saved_response, "Showing 1 saved hotel")
        self.assertContains(saved_response, self.user.email)
        self.assertContains(saved_response, self.hotel.name)
        self.assertIn("no-store", saved_response.headers["Cache-Control"])

        self.client.post(
            reverse("toggle-saved-hotel"),
            {"hotel_code": self.hotel.code, "next": reverse("dashboard-saved")},
        )
        self.assertFalse(SavedHotel.objects.filter(user=self.user, hotel=self.hotel).exists())

    def test_save_action_keeps_existing_saved_hotel(self):
        SavedHotel.objects.create(user=self.user, hotel=self.hotel)

        response = self.client.post(
            reverse("toggle-saved-hotel"),
            {
                "action": "save",
                "hotel_code": self.hotel.code,
                "next": reverse("hotels"),
            },
        )

        self.assertRedirects(response, reverse("hotels"))
        self.assertTrue(SavedHotel.objects.filter(user=self.user, hotel=self.hotel).exists())

    def test_profile_update_writes_user_profile(self):
        response = self.client.post(
            reverse("dashboard-profile"),
            {
                "action": "profile",
                "first_name": "Updated",
                "last_name": "Traveler",
                "email": "updated@example.com",
                "phone": "+90 555 111 22 33",
                "nationality": "Turkey",
                "marketing_emails": "on",
                "reward_updates": "on",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        profile = UserProfile.objects.get(user=self.user)
        self.assertEqual(self.user.email, "updated@example.com")
        self.assertEqual(profile.phone, "+90 555 111 22 33")
        self.assertFalse(profile.booking_notifications)

    def test_payment_method_stores_only_brand_and_last4(self):
        response = self.client.post(
            reverse("dashboard-payment-methods"),
            {
                "cardholder_name": "Dash User",
                "card_number": "4111 1111 1111 1111",
                "expiry": "12/30",
                "cvv": "123",
            },
        )

        self.assertRedirects(response, reverse("dashboard-payment-methods"))
        method = PaymentMethod.objects.get(user=self.user)
        self.assertEqual(method.brand, PaymentMethod.CARD_VISA)
        self.assertEqual(method.last4, "1111")
        self.assertTrue(method.is_default)

    def test_review_form_creates_review_for_booking(self):
        response = self.client.post(
            reverse("dashboard-reviews"),
            {
                "booking_id": self.booking.id,
                "rating": "4",
                "comment": "Very comfortable stay.",
            },
        )

        self.assertRedirects(response, reverse("dashboard-reviews"))
        review = Review.objects.get(user=self.user, booking=self.booking)
        self.assertEqual(review.hotel, self.hotel)
        self.assertEqual(review.rating, 4)
