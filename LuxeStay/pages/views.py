from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash
from django.db.models import Q
from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.cache import never_cache

from .forms import LoginForm, SignupForm
from .models import Booking, Hotel, PaymentMethod, Review, SavedHotel, UserProfile


@never_cache
def service_worker_view(request):
    script = """
self.addEventListener('install', function(event) {
  self.skipWaiting();
});
self.addEventListener('activate', function(event) {
  event.waitUntil(
    caches.keys()
      .then(function(keys) { return Promise.all(keys.map(function(key) { return caches.delete(key); })); })
      .then(function() { return self.registration.unregister(); })
      .then(function() { return self.clients.matchAll(); })
      .then(function(clients) { clients.forEach(function(client) { client.navigate(client.url); }); })
  );
});
self.addEventListener('fetch', function(event) {
  event.respondWith(fetch(event.request));
});
"""
    response = HttpResponse(script, content_type="application/javascript")
    response["Service-Worker-Allowed"] = "/"
    response["Cache-Control"] = "no-store, max-age=0"
    return response


def account_context(request):
    if not request.user.is_authenticated:
        return {}

    full_name = request.user.get_full_name().strip()
    account_name = full_name or request.user.email or request.user.username
    initials_source = full_name or request.user.email or request.user.username
    initials = "".join(part[0] for part in initials_source.split()[:2]).upper()
    if not initials:
        initials = request.user.username[:2].upper()

    return {
        "account_name": account_name,
        "account_first_name": request.user.first_name or account_name.split()[0],
        "account_initials": initials,
    }


def get_profile(user):
    profile, _ = UserProfile.objects.get_or_create(user=user)
    return profile


def reward_points_for(user):
    total = Decimal("0")
    for booking in Booking.objects.filter(user=user).exclude(status=Booking.STATUS_CANCELLED):
        total += booking.total_amount
    return int(total)


def tier_for_points(points):
    if points >= 50000:
        return "Platinum", 50000, 50000, 100
    if points >= 15000:
        return "Gold", 15000, 50000, int((points - 15000) * 100 / 35000)
    if points >= 5000:
        return "Silver", 5000, 15000, int((points - 5000) * 100 / 10000)
    return "Bronze", 0, 5000, int(points * 100 / 5000)


def dashboard_base_context(request):
    context = account_context(request)
    points = reward_points_for(request.user)
    tier, tier_start, tier_end, tier_progress = tier_for_points(points)
    context.update(
        {
            "profile": get_profile(request.user),
            "reward_points": points,
            "reward_value": points // 100,
            "reward_tier": tier,
            "tier_start": tier_start,
            "tier_end": tier_end,
            "tier_progress": tier_progress,
            "bookings_count": Booking.objects.filter(user=request.user).count(),
            "saved_count": SavedHotel.objects.filter(user=request.user).count(),
        }
    )
    return context


def notification_items(user):
    items = []
    for booking in Booking.objects.select_related("hotel").filter(user=user)[:8]:
        if booking.status == Booking.STATUS_CANCELLED:
            title = "Booking cancelled"
            body = f"{booking.display_reference} for {booking.hotel.name} was cancelled."
            css = "status-cancelled"
        else:
            title = "Booking confirmed"
            body = f"{booking.display_reference} for {booking.hotel.name} is confirmed."
            css = "status-upcoming"
        items.append({"title": title, "body": body, "css": css, "created_at": booking.created_at})
    if not items:
        items.append(
            {
                "title": "Welcome to LuxeStay",
                "body": "Your dashboard is ready. Search hotels and create your first booking.",
                "css": "status-upcoming",
                "created_at": None,
            }
        )
    return items


def page(template_name, require_login=False):
    def view(request):
        return render(request, template_name, account_context(request))

    if require_login:
        return login_required(view)
    return view


def filter_hotels(request):
    destination = request.GET.get("destination", "").strip()
    category = request.GET.get("category", "").strip().lower()
    check_in = request.GET.get("checkIn", "").strip()
    check_out = request.GET.get("checkOut", "").strip()
    guests = request.GET.get("guests", "").strip()
    sort = request.GET.get("sort", "recommended").strip()

    hotels = Hotel.objects.all()

    if destination:
        hotels = hotels.filter(
            Q(name__icontains=destination)
            | Q(city__icontains=destination)
            | Q(country__icontains=destination)
            | Q(location__icontains=destination)
            | Q(category__icontains=destination)
            | Q(property_type__icontains=destination)
        )

    if category:
        hotels = hotels.filter(category__iexact=category)

    if guests.isdigit():
        hotels = hotels.filter(max_guests__gte=int(guests))

    if sort == "price-desc":
        hotels = hotels.order_by("-current_price", "name")
    elif sort == "rating":
        hotels = hotels.order_by("-rating", "-review_count")
    else:
        hotels = hotels.order_by("current_price", "name")

    search = {
        "destination": destination,
        "category": category,
        "checkIn": check_in,
        "checkOut": check_out,
        "guests": guests or "2",
        "sort": sort,
    }
    return hotels, search


def hotels_view(request):
    hotels, search = filter_hotels(request)
    print(f"HOTEL_SEARCH params={dict(request.GET)}")
    print(f"HOTEL_SEARCH sql={hotels.query}")
    context = account_context(request)
    context.update(
        {
            "hotels": hotels,
            "result_count": hotels.count(),
            "search": search,
            "has_search": any([search["destination"], search["category"], search["checkIn"], search["checkOut"], request.GET.get("guests", "")]),
            "saved_codes": set(
                SavedHotel.objects.filter(user=request.user).values_list("hotel__code", flat=True)
            )
            if request.user.is_authenticated
            else set(),
        }
    )
    return render(request, "hotels/html/hotels.html", context)


def hotels_api(request):
    hotels, search = filter_hotels(request)
    print(f"API_HOTEL_SEARCH params={dict(request.GET)}")
    print(f"API_HOTEL_SEARCH sql={hotels.query}")
    data = [
        {
            "id": hotel.code,
            "name": hotel.name,
            "city": hotel.city,
            "country": hotel.country,
            "location": hotel.location,
            "category": hotel.category,
            "price": hotel.current_price,
            "rating": float(hotel.rating),
            "rooms_left": hotel.rooms_left,
        }
        for hotel in hotels
    ]
    return JsonResponse({"count": len(data), "search": search, "results": data})


def parse_booking_date(value, fallback):
    if not value:
        return fallback
    try:
        return date.fromisoformat(value)
    except ValueError:
        return fallback


def booking_total(hotel, check_in, check_out):
    nights = max((check_out - check_in).days, 1)
    room_total = Decimal(hotel.current_price) * nights
    service_fee = (room_total * Decimal("0.08")).quantize(Decimal("1"))
    taxes = (room_total * Decimal("0.12")).quantize(Decimal("1"))
    total = room_total + service_fee + taxes
    return {
        "nights": nights,
        "room_total": room_total,
        "service_fee": service_fee,
        "taxes": taxes,
        "total": total,
    }


def checkout_context(request, hotel, check_in, check_out, guests):
    context = account_context(request)
    totals = booking_total(hotel, check_in, check_out)
    context.update(
        {
            "hotel": hotel,
            "check_in": check_in,
            "check_out": check_out,
            "guests": guests,
            "room_name": "Deluxe Sea View Room",
            "totals": totals,
            "saved_payment_methods": PaymentMethod.objects.filter(user=request.user),
        }
    )
    return context


def card_digits(value):
    return "".join(ch for ch in (value or "") if ch.isdigit())


def parse_card_expiry(value):
    digits = card_digits(value)
    if len(digits) == 4:
        month = int(digits[:2])
        year = int("20" + digits[2:])
    elif len(digits) == 6:
        month = int(digits[:2])
        year = int(digits[2:])
    else:
        return None

    today = date.today()
    if month < 1 or month > 12:
        return None
    if year < today.year or (year == today.year and month < today.month):
        return None
    return month, year


def card_error_message(cardholder_name, digits, expiry, cvv):
    if not cardholder_name:
        return "Please enter the name on the card."
    if len(digits) < 13 or len(digits) > 19:
        return "Card number must be 13 to 19 digits."
    if not parse_card_expiry(expiry):
        return "Expiry date must be a valid future date in MM/YY format."
    if len(cvv) < 3 or len(cvv) > 4:
        return "CVV must be 3 or 4 digits."
    return ""


def save_payment_method_for_user(user, cardholder_name, digits, expiry, is_default=False):
    expiry_month, expiry_year = parse_card_expiry(expiry)
    PaymentMethod.objects.create(
        user=user,
        cardholder_name=cardholder_name.strip() or user.get_full_name() or user.email,
        brand=card_brand(digits),
        last4=digits[-4:],
        expiry_month=expiry_month,
        expiry_year=expiry_year,
        is_default=is_default,
    )


@login_required
def guest_details_view(request):
    if request.method == "POST":
        today = date.today()
        check_in = parse_booking_date(request.POST.get("checkIn"), today + timedelta(days=1))
        check_out = parse_booking_date(request.POST.get("checkOut"), check_in + timedelta(days=2))
        if check_out <= check_in:
            check_out = check_in + timedelta(days=1)

        request.session["pending_booking"] = {
            "hotel_code": request.POST.get("hotel_code") or "h1",
            "check_in": check_in.isoformat(),
            "check_out": check_out.isoformat(),
            "guests": request.POST.get("guests") or "2",
            "guest_first_name": request.POST.get("guest_first_name", "").strip(),
            "guest_last_name": request.POST.get("guest_last_name", "").strip(),
            "guest_email": request.POST.get("guest_email", "").strip(),
            "guest_phone": request.POST.get("guest_phone", "").strip(),
            "nationality": request.POST.get("nationality", "").strip(),
            "notes": request.POST.get("notes", "").strip(),
        }
        print(f"CHECKOUT_GUEST_DETAILS session={request.session['pending_booking']}")
        return redirect("payment")

    today = date.today()
    hotel_code = request.GET.get("hotel") or request.GET.get("id") or "h1"
    hotel = get_object_or_404(Hotel, code=hotel_code)
    check_in = parse_booking_date(request.GET.get("checkIn"), today + timedelta(days=1))
    check_out = parse_booking_date(request.GET.get("checkOut"), check_in + timedelta(days=2))
    if check_out <= check_in:
        check_out = check_in + timedelta(days=1)
    guests = request.GET.get("guests") or "2"
    context = checkout_context(request, hotel, check_in, check_out, guests)
    return render(request, "checkout/html/guest-details.html", context)


@login_required
def payment_view(request):
    pending = request.session.get("pending_booking")
    if not pending:
        return redirect("hotels")

    hotel = get_object_or_404(Hotel, code=pending["hotel_code"])
    check_in = parse_booking_date(pending.get("check_in"), date.today() + timedelta(days=1))
    check_out = parse_booking_date(pending.get("check_out"), check_in + timedelta(days=2))
    guests = int(pending.get("guests") or 2)
    totals = booking_total(hotel, check_in, check_out)

    if request.method == "POST":
        if not request.POST.get("agree_terms") or not request.POST.get("agree_cancel"):
            context = checkout_context(request, hotel, check_in, check_out, guests)
            context["payment_error"] = "Please accept the Terms & Policies to continue."
            return render(request, "checkout/html/payment.html", context)

        payment_method = request.POST.get("payment_method") or Booking.PAYMENT_CARD
        if payment_method == Booking.PAYMENT_CARD:
            cardholder_name = request.POST.get("cardholder_name", "").strip()
            digits = card_digits(request.POST.get("card_number", ""))
            expiry = request.POST.get("expiry", "")
            cvv = card_digits(request.POST.get("cvv", ""))
            card_error = card_error_message(cardholder_name, digits, expiry, cvv)
            if card_error:
                context = checkout_context(request, hotel, check_in, check_out, guests)
                context["payment_error"] = card_error
                return render(request, "checkout/html/payment.html", context)

        with transaction.atomic():
            locked_hotel = Hotel.objects.select_for_update().get(pk=hotel.pk)
            print(f"BOOKING_CREATE before_stock hotel={locked_hotel.code} rooms_left={locked_hotel.rooms_left}")
            if locked_hotel.rooms_left < 1:
                context = checkout_context(request, locked_hotel, check_in, check_out, guests)
                context["payment_error"] = "This hotel is no longer available."
                return render(request, "checkout/html/payment.html", context)

            booking = Booking.objects.create(
                user=request.user,
                hotel=locked_hotel,
                guest_first_name=pending.get("guest_first_name") or request.user.first_name or "Guest",
                guest_last_name=pending.get("guest_last_name") or request.user.last_name or "Traveler",
                guest_email=pending.get("guest_email") or request.user.email,
                guest_phone=pending.get("guest_phone", ""),
                nationality=pending.get("nationality", ""),
                check_in=check_in,
                check_out=check_out,
                guests=guests,
                payment_method=payment_method,
                total_amount=totals["total"],
            )
            locked_hotel.rooms_left -= 1
            locked_hotel.save(update_fields=["rooms_left"])
            if payment_method == Booking.PAYMENT_CARD and request.POST.get("save_card"):
                is_first = not PaymentMethod.objects.filter(user=request.user).exists()
                save_payment_method_for_user(request.user, cardholder_name, digits, expiry, is_default=is_first)
            print(
                "BOOKING_CREATE saved "
                f"booking_id={booking.booking_reference} user_id={request.user.id} "
                f"hotel={locked_hotel.code} after_stock={locked_hotel.rooms_left}"
            )

        request.session["latest_booking_id"] = booking.id
        request.session.pop("pending_booking", None)
        return redirect("booking-confirmed")

    context = checkout_context(request, hotel, check_in, check_out, guests)
    return render(request, "checkout/html/payment.html", context)


@login_required
@never_cache
def booking_confirmed_view(request):
    booking = get_object_or_404(
        Booking.objects.select_related("hotel"),
        pk=request.session.get("latest_booking_id"),
        user=request.user,
    )
    context = account_context(request)
    context["booking"] = booking
    return render(request, "checkout/html/booking-confirmed.html", context)


@login_required
@never_cache
def dashboard_bookings_view(request):
    context = dashboard_base_context(request)
    bookings = (
        Booking.objects.select_related("hotel")
        .filter(Q(user=request.user) | Q(guest_email__iexact=request.user.email))
        .distinct()
    )
    booking_count = bookings.count()
    print(f"DASHBOARD_BOOKINGS user_id={request.user.id} email={request.user.email} count={booking_count}")
    print(f"DASHBOARD_BOOKINGS sql={bookings.query}")
    context["bookings"] = bookings
    context["dashboard_bookings_count"] = booking_count
    response = render(request, "dashboard/html/bookings.html", context)
    response["Cache-Control"] = "no-store, max-age=0, must-revalidate"
    response["Pragma"] = "no-cache"
    response["Expires"] = "0"
    return response


@login_required
@never_cache
def dashboard_overview_view(request):
    context = dashboard_base_context(request)
    context.update(
        {
            "upcoming_bookings": Booking.objects.select_related("hotel")
            .filter(user=request.user, status=Booking.STATUS_CONFIRMED)[:3],
            "saved_hotels": SavedHotel.objects.select_related("hotel").filter(user=request.user)[:3],
            "notifications": notification_items(request.user)[:3],
        }
    )
    return render(request, "dashboard/html/index.html", context)


@login_required
@never_cache
def dashboard_saved_view(request):
    if request.method == "POST":
        hotel = get_object_or_404(Hotel, code=request.POST.get("hotel_code"))
        action = request.POST.get("action")
        if action == "remove":
            SavedHotel.objects.filter(user=request.user, hotel=hotel).delete()
        else:
            SavedHotel.objects.get_or_create(user=request.user, hotel=hotel)
        return redirect("dashboard-saved")

    context = dashboard_base_context(request)
    context["saved_hotels"] = SavedHotel.objects.select_related("hotel").filter(user=request.user)
    return render(request, "dashboard/html/saved.html", context)


@login_required
def toggle_saved_hotel_view(request):
    if request.method != "POST":
        return redirect("hotels")

    hotel = get_object_or_404(Hotel, code=request.POST.get("hotel_code"))
    saved, created = SavedHotel.objects.get_or_create(user=request.user, hotel=hotel)
    if not created:
        saved.delete()
    return redirect(request.POST.get("next") or "hotels")


@login_required
@never_cache
def dashboard_profile_view(request):
    profile = get_profile(request.user)
    context = dashboard_base_context(request)

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "profile":
            request.user.first_name = request.POST.get("first_name", "").strip()
            request.user.last_name = request.POST.get("last_name", "").strip()
            email = request.POST.get("email", "").strip().lower()
            email_exists = (
                request.user.__class__.objects.exclude(pk=request.user.pk)
                .filter(Q(email=email) | Q(username=email))
                .exists()
                if email
                else False
            )
            if email_exists:
                context["dashboard_error"] = "This email is already in use."
            else:
                if email:
                    request.user.email = email
                    request.user.username = email
                request.user.save()
                profile.phone = request.POST.get("phone", "").strip()
                profile.nationality = request.POST.get("nationality", "").strip()
                profile.marketing_emails = bool(request.POST.get("marketing_emails"))
                profile.booking_notifications = bool(request.POST.get("booking_notifications"))
                profile.reward_updates = bool(request.POST.get("reward_updates"))
                profile.save()
                context["dashboard_message"] = "Profile updated."
        elif action == "password":
            current_password = request.POST.get("current_password", "")
            new_password = request.POST.get("new_password", "")
            confirm_password = request.POST.get("confirm_password", "")
            if not request.user.check_password(current_password):
                context["dashboard_error"] = "Current password is incorrect."
            elif new_password != confirm_password:
                context["dashboard_error"] = "New passwords do not match."
            elif len(new_password) < 8:
                context["dashboard_error"] = "New password must be at least 8 characters."
            else:
                request.user.set_password(new_password)
                request.user.save()
                update_session_auth_hash(request, request.user)
                context["dashboard_message"] = "Password updated."

        context.update(account_context(request))
        context["profile"] = get_profile(request.user)

    return render(request, "dashboard/html/profile.html", context)


@login_required
@never_cache
def dashboard_notifications_view(request):
    context = dashboard_base_context(request)
    context["notifications"] = notification_items(request.user)
    return render(request, "dashboard/html/notifications.html", context)


def card_brand(number):
    if number.startswith("4"):
        return PaymentMethod.CARD_VISA
    if number.startswith(("51", "52", "53", "54", "55")):
        return PaymentMethod.CARD_MASTERCARD
    if number.startswith(("34", "37")):
        return PaymentMethod.CARD_AMEX
    return PaymentMethod.CARD_OTHER


@login_required
@never_cache
def dashboard_payment_methods_view(request):
    if request.method == "POST":
        action = request.POST.get("action")
        method_id = request.POST.get("method_id")
        if action == "delete" and method_id:
            PaymentMethod.objects.filter(user=request.user, id=method_id).delete()
            return redirect("dashboard-payment-methods")
        if action == "default" and method_id:
            PaymentMethod.objects.filter(user=request.user).update(is_default=False)
            PaymentMethod.objects.filter(user=request.user, id=method_id).update(is_default=True)
            return redirect("dashboard-payment-methods")

        cardholder_name = request.POST.get("cardholder_name", "").strip()
        digits = card_digits(request.POST.get("card_number", ""))
        expiry = request.POST.get("expiry", "")
        cvv = card_digits(request.POST.get("cvv", ""))
        card_error = card_error_message(cardholder_name, digits, expiry, cvv)
        if card_error:
            context = dashboard_base_context(request)
            context["payment_error"] = card_error
            context["payment_methods"] = PaymentMethod.objects.filter(user=request.user)
            context["billing_bookings"] = Booking.objects.select_related("hotel").filter(user=request.user)[:10]
            return render(request, "dashboard/html/payment-methods.html", context)

        if digits:
            is_first = not PaymentMethod.objects.filter(user=request.user).exists()
            save_payment_method_for_user(request.user, cardholder_name, digits, expiry, is_default=is_first)
        return redirect("dashboard-payment-methods")

    context = dashboard_base_context(request)
    context["payment_methods"] = PaymentMethod.objects.filter(user=request.user)
    context["billing_bookings"] = Booking.objects.select_related("hotel").filter(user=request.user)[:10]
    return render(request, "dashboard/html/payment-methods.html", context)


@login_required
@never_cache
def dashboard_reviews_view(request):
    if request.method == "POST":
        booking = get_object_or_404(
            Booking.objects.select_related("hotel"),
            id=request.POST.get("booking_id"),
            user=request.user,
        )
        try:
            rating = int(request.POST.get("rating") or 5)
        except ValueError:
            rating = 5
        rating = max(1, min(5, rating))
        Review.objects.update_or_create(
            booking=booking,
            defaults={
                "user": request.user,
                "hotel": booking.hotel,
                "rating": rating,
                "comment": request.POST.get("comment", "").strip(),
            },
        )
        return redirect("dashboard-reviews")

    reviewed_booking_ids = Review.objects.filter(user=request.user).values_list("booking_id", flat=True)
    context = dashboard_base_context(request)
    context["reviews"] = Review.objects.select_related("hotel", "booking").filter(user=request.user)
    context["reviewable_bookings"] = (
        Booking.objects.select_related("hotel")
        .filter(user=request.user)
        .exclude(status=Booking.STATUS_CANCELLED)
        .exclude(id__in=reviewed_booking_ids)
    )
    return render(request, "dashboard/html/reviews.html", context)


@login_required
@never_cache
def dashboard_rewards_view(request):
    context = dashboard_base_context(request)
    context["points_history"] = Booking.objects.select_related("hotel").filter(user=request.user).exclude(status=Booking.STATUS_CANCELLED)[:10]
    return render(request, "dashboard/html/rewards.html", context)


def signup_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    form = SignupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        print(
            "SIGNUP_POST received "
            f"first_name={form.cleaned_data['firstName']} "
            f"last_name={form.cleaned_data['lastName']} "
            f"email={form.cleaned_data['email']}"
        )
        user = form.save()
        login(request, user)
        return redirect("dashboard")

    return render(request, "auth/html/signup.html", {"form": form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    form = LoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        login(request, form.user)
        if not form.cleaned_data.get("remember"):
            request.session.set_expiry(0)
        next_url = request.GET.get("next")
        if next_url and url_has_allowed_host_and_scheme(
            next_url,
            allowed_hosts={request.get_host()},
        ):
            return redirect(next_url)
        return redirect(reverse("dashboard"))

    return render(request, "auth/html/login.html", {"form": form})


def logout_view(request):
    logout(request)
    return redirect("home")
