from django.contrib import admin

from .models import Booking, Hotel, PaymentMethod, Review, SavedHotel, UserProfile


@admin.register(Hotel)
class HotelAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "city", "category", "current_price", "rooms_left")
    list_filter = ("category", "property_type", "city")
    search_fields = ("code", "name", "city", "country", "location")


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = (
        "display_reference",
        "user",
        "hotel",
        "check_in",
        "check_out",
        "guests",
        "status",
        "total_amount",
        "created_at",
    )
    list_filter = ("status", "payment_method", "hotel")
    search_fields = ("booking_reference", "guest_email", "guest_first_name", "guest_last_name", "hotel__name")
    readonly_fields = ("booking_reference", "created_at")

    def save_model(self, request, obj, form, change):
        if change:
            old_booking = Booking.objects.select_related("hotel").get(pk=obj.pk)
            if old_booking.status != obj.status:
                if old_booking.status != Booking.STATUS_CANCELLED and obj.status == Booking.STATUS_CANCELLED:
                    obj.hotel.rooms_left += 1
                    obj.hotel.save(update_fields=["rooms_left"])
                    print(
                        "ADMIN_BOOKING_STATUS_CHANGE "
                        f"booking_id={obj.booking_reference} status={old_booking.status}->{obj.status} "
                        f"hotel={obj.hotel.code} rooms_left={obj.hotel.rooms_left}"
                    )
                elif old_booking.status == Booking.STATUS_CANCELLED and obj.status != Booking.STATUS_CANCELLED:
                    if obj.hotel.rooms_left > 0:
                        obj.hotel.rooms_left -= 1
                        obj.hotel.save(update_fields=["rooms_left"])
                        print(
                            "ADMIN_BOOKING_STATUS_CHANGE "
                            f"booking_id={obj.booking_reference} status={old_booking.status}->{obj.status} "
                            f"hotel={obj.hotel.code} rooms_left={obj.hotel.rooms_left}"
                        )
        super().save_model(request, obj, form, change)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "phone", "nationality", "marketing_emails", "booking_notifications", "reward_updates")
    search_fields = ("user__email", "user__first_name", "user__last_name", "phone", "nationality")


@admin.register(SavedHotel)
class SavedHotelAdmin(admin.ModelAdmin):
    list_display = ("user", "hotel", "created_at")
    search_fields = ("user__email", "hotel__name")


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ("user", "brand", "last4", "expiry_month", "expiry_year", "is_default", "created_at")
    list_filter = ("brand", "is_default")
    search_fields = ("user__email", "cardholder_name", "last4")


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("user", "hotel", "booking", "rating", "created_at")
    list_filter = ("rating", "hotel")
    search_fields = ("user__email", "hotel__name", "comment", "booking__booking_reference")
