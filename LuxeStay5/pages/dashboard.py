from decimal import Decimal

from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.cache import never_cache

from .models import Booking, Hotel, PaymentMethod, Review, SavedHotel
from .views import (
    account_context,
    card_digits,
    card_error_message,
    get_profile,
    save_payment_method_for_user,
)


SECTIONS = {
    "overview": {"label": "Overview", "url_name": "dashboard"},
    "bookings": {"label": "Bookings", "url_name": "dashboard-bookings"},
    "saved": {"label": "Saved Hotels", "url_name": "dashboard-saved"},
    "payments": {"label": "Payments", "url_name": "dashboard-payment-methods"},
    "reviews": {"label": "Reviews", "url_name": "dashboard-reviews"},
    "rewards": {"label": "Rewards", "url_name": "dashboard-rewards"},
    "profile": {"label": "Profile", "url_name": "dashboard-profile"},
    "notifications": {"label": "Updates", "url_name": "dashboard-notifications"},
}


def user_bookings(user):
    return (
        Booking.objects.select_related("hotel")
        .filter(Q(user=user) | Q(guest_email__iexact=user.email))
        .distinct()
    )


def rewards_for(bookings):
    total = Decimal("0")
    for booking in bookings.exclude(status=Booking.STATUS_CANCELLED):
        total += booking.total_amount
    points = int(total)
    if points >= 50000:
        return points, "Platinum", 50000, 50000, 100
    if points >= 15000:
        return points, "Gold", 15000, 50000, int((points - 15000) * 100 / 35000)
    if points >= 5000:
        return points, "Silver", 5000, 15000, int((points - 5000) * 100 / 10000)
    return points, "Bronze", 0, 5000, int(points * 100 / 5000)


def account_updates(bookings):
    updates = []
    for booking in bookings[:6]:
        if booking.status == Booking.STATUS_CANCELLED:
            updates.append(
                {
                    "title": "Booking cancelled",
                    "body": f"{booking.display_reference} for {booking.hotel.name} was cancelled.",
                    "tone": "cancelled",
                    "created_at": booking.created_at,
                }
            )
        else:
            updates.append(
                {
                    "title": "Booking ready",
                    "body": f"{booking.display_reference} is linked to {booking.hotel.name}.",
                    "tone": "confirmed",
                    "created_at": booking.created_at,
                }
            )
    if not updates:
        updates.append(
            {
                "title": "Account ready",
                "body": "Saved hotels and reservations will land here as soon as you create them.",
                "tone": "neutral",
                "created_at": None,
            }
        )
    return updates


def render_dashboard(request, section, extra=None):
    bookings = user_bookings(request.user)
    saved_hotels = SavedHotel.objects.select_related("hotel").filter(user=request.user)
    points, tier, tier_start, tier_end, tier_progress = rewards_for(bookings)
    reviewed_booking_ids = Review.objects.filter(user=request.user).values_list("booking_id", flat=True)

    context = account_context(request)
    context.update(
        {
            "active_section": section,
            "dashboard_sections": SECTIONS,
            "bookings": bookings,
            "bookings_count": bookings.count(),
            "dashboard_bookings_count": bookings.count(),
            "recent_bookings": bookings[:4],
            "upcoming_bookings": bookings.filter(status=Booking.STATUS_CONFIRMED)[:4],
            "saved_hotels": saved_hotels,
            "saved_count": saved_hotels.count(),
            "dashboard_saved_count": saved_hotels.count(),
            "payment_methods": PaymentMethod.objects.filter(user=request.user),
            "billing_bookings": bookings[:8],
            "notifications": account_updates(bookings),
            "profile": get_profile(request.user),
            "reviews": Review.objects.select_related("hotel", "booking").filter(user=request.user),
            "reviewable_bookings": bookings.exclude(status=Booking.STATUS_CANCELLED).exclude(
                id__in=reviewed_booking_ids
            ),
            "reward_points": points,
            "reward_value": points // 100,
            "reward_tier": tier,
            "tier_start": tier_start,
            "tier_end": tier_end,
            "tier_progress": tier_progress,
            "points_history": bookings.exclude(status=Booking.STATUS_CANCELLED)[:8],
        }
    )
    if extra:
        context.update(extra)

    response = render(request, "dashboard/html/app.html", context)
    response["Cache-Control"] = "no-store, max-age=0, must-revalidate"
    response["Pragma"] = "no-cache"
    response["Expires"] = "0"
    return response


@login_required
@never_cache
def overview_view(request):
    return render_dashboard(request, "overview")


@login_required
@never_cache
def bookings_view(request):
    return render_dashboard(request, "bookings")


@login_required
@never_cache
def saved_view(request):
    if request.method == "POST":
        hotel = get_object_or_404(Hotel, code=request.POST.get("hotel_code"))
        if request.POST.get("action") == "remove":
            SavedHotel.objects.filter(user=request.user, hotel=hotel).delete()
        else:
            SavedHotel.objects.get_or_create(user=request.user, hotel=hotel)
        return redirect("dashboard-saved")
    return render_dashboard(request, "saved")


@login_required
def save_hotel_view(request):
    if request.method != "POST":
        return redirect("hotels")

    hotel = get_object_or_404(Hotel, code=request.POST.get("hotel_code"))
    saved, created = SavedHotel.objects.get_or_create(user=request.user, hotel=hotel)
    action = request.POST.get("action")
    if action != "save" and not created:
        saved.delete()

    next_url = request.POST.get("next", "")
    if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        return redirect(next_url)
    return redirect("dashboard-saved")


@login_required
@never_cache
def profile_view(request):
    extra = {}
    profile = get_profile(request.user)
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "profile":
            email = request.POST.get("email", "").strip().lower()
            email_taken = (
                request.user.__class__.objects.exclude(pk=request.user.pk)
                .filter(Q(email=email) | Q(username=email))
                .exists()
                if email
                else False
            )
            if email_taken:
                extra["dashboard_error"] = "This email is already in use."
            else:
                request.user.first_name = request.POST.get("first_name", "").strip()
                request.user.last_name = request.POST.get("last_name", "").strip()
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
                extra["dashboard_message"] = "Profile updated."
        elif action == "password":
            current_password = request.POST.get("current_password", "")
            new_password = request.POST.get("new_password", "")
            if not request.user.check_password(current_password):
                extra["dashboard_error"] = "Current password is incorrect."
            elif new_password != request.POST.get("confirm_password", ""):
                extra["dashboard_error"] = "New passwords do not match."
            elif len(new_password) < 8:
                extra["dashboard_error"] = "New password must be at least 8 characters."
            else:
                request.user.set_password(new_password)
                request.user.save()
                update_session_auth_hash(request, request.user)
                extra["dashboard_message"] = "Password updated."
    return render_dashboard(request, "profile", extra)


@login_required
@never_cache
def payment_methods_view(request):
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

        digits = card_digits(request.POST.get("card_number", ""))
        error = card_error_message(
            request.POST.get("cardholder_name", "").strip(),
            digits,
            request.POST.get("expiry", ""),
            card_digits(request.POST.get("cvv", "")),
        )
        if error:
            return render_dashboard(request, "payments", {"payment_error": error})

        is_first = not PaymentMethod.objects.filter(user=request.user).exists()
        save_payment_method_for_user(
            request.user,
            request.POST.get("cardholder_name", ""),
            digits,
            request.POST.get("expiry", ""),
            is_default=is_first,
        )
        return redirect("dashboard-payment-methods")
    return render_dashboard(request, "payments")


@login_required
@never_cache
def reviews_view(request):
    if request.method == "POST":
        booking = get_object_or_404(
            user_bookings(request.user).exclude(status=Booking.STATUS_CANCELLED),
            id=request.POST.get("booking_id"),
        )
        try:
            rating = int(request.POST.get("rating") or 5)
        except ValueError:
            rating = 5
        Review.objects.update_or_create(
            booking=booking,
            defaults={
                "user": request.user,
                "hotel": booking.hotel,
                "rating": max(1, min(5, rating)),
                "comment": request.POST.get("comment", "").strip(),
            },
        )
        return redirect("dashboard-reviews")
    return render_dashboard(request, "reviews")


@login_required
@never_cache
def notifications_view(request):
    return render_dashboard(request, "notifications")


@login_required
@never_cache
def rewards_view(request):
    return render_dashboard(request, "rewards")
