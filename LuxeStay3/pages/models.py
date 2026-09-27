import random

from django.conf import settings
from django.db import models


class Hotel(models.Model):
    code = models.SlugField(unique=True)
    name = models.CharField(max_length=200)
    city = models.CharField(max_length=100)
    country = models.CharField(max_length=100, default="Turkey")
    location = models.CharField(max_length=200)
    category = models.CharField(max_length=50)
    property_type = models.CharField(max_length=50, default="hotel")
    amenities = models.CharField(max_length=255)
    image_url = models.URLField(max_length=500)
    rating = models.DecimalField(max_digits=3, decimal_places=1)
    review_count = models.PositiveIntegerField(default=0)
    original_price = models.PositiveIntegerField()
    current_price = models.PositiveIntegerField()
    max_guests = models.PositiveIntegerField(default=4)
    rooms_left = models.PositiveIntegerField(default=5)

    class Meta:
        ordering = ["current_price", "name"]

    def __str__(self):
        return self.name

    @property
    def amenities_list(self):
        return [item.strip() for item in self.amenities.split(",") if item.strip()]

    @property
    def discount_percent(self):
        if not self.original_price:
            return 0
        return round((self.original_price - self.current_price) * 100 / self.original_price)


class Booking(models.Model):
    STATUS_CONFIRMED = "confirmed"
    STATUS_CANCELLED = "cancelled"
    STATUS_COMPLETED = "completed"
    STATUS_CHOICES = [
        (STATUS_CONFIRMED, "Confirmed"),
        (STATUS_CANCELLED, "Cancelled"),
        (STATUS_COMPLETED, "Completed"),
    ]

    PAYMENT_CARD = "card"
    PAYMENT_BANK = "bank"
    PAYMENT_SAVED = "saved"
    PAYMENT_CHOICES = [
        (PAYMENT_CARD, "Credit / Debit Card"),
        (PAYMENT_BANK, "Bank Transfer"),
        (PAYMENT_SAVED, "Saved Card"),
    ]

    booking_reference = models.CharField(max_length=9, unique=True, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="bookings")
    hotel = models.ForeignKey(Hotel, on_delete=models.PROTECT, related_name="bookings")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_CONFIRMED)
    guest_first_name = models.CharField(max_length=150)
    guest_last_name = models.CharField(max_length=150)
    guest_email = models.EmailField()
    guest_phone = models.CharField(max_length=40, blank=True)
    nationality = models.CharField(max_length=80, blank=True)
    check_in = models.DateField()
    check_out = models.DateField()
    guests = models.PositiveIntegerField(default=2)
    room_name = models.CharField(max_length=120, default="Deluxe Sea View Room")
    payment_method = models.CharField(max_length=20, choices=PAYMENT_CHOICES, default=PAYMENT_CARD)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"LXS-{self.booking_reference} - {self.hotel.name}"

    def save(self, *args, **kwargs):
        if not self.booking_reference:
            self.booking_reference = self.generate_reference()
        super().save(*args, **kwargs)

    @classmethod
    def generate_reference(cls):
        while True:
            reference = f"{random.randint(100000000, 999999999)}"
            if not cls.objects.filter(booking_reference=reference).exists():
                return reference

    @property
    def display_reference(self):
        return f"LXS-{self.booking_reference}"

    @property
    def guest_name(self):
        return f"{self.guest_first_name} {self.guest_last_name}".strip()

    @property
    def nights(self):
        return max((self.check_out - self.check_in).days, 1)

    @property
    def status_css(self):
        if self.status == self.STATUS_CANCELLED:
            return "status-cancelled"
        if self.status == self.STATUS_COMPLETED:
            return "status-completed"
        return "status-upcoming"


class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    phone = models.CharField(max_length=40, blank=True)
    nationality = models.CharField(max_length=80, blank=True)
    marketing_emails = models.BooleanField(default=True)
    booking_notifications = models.BooleanField(default=True)
    reward_updates = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user.email} profile"


class SavedHotel(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="saved_hotels")
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, related_name="saved_by")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "hotel"], name="unique_saved_hotel_per_user"),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.email} saved {self.hotel.name}"


class PaymentMethod(models.Model):
    CARD_VISA = "Visa"
    CARD_MASTERCARD = "Mastercard"
    CARD_AMEX = "American Express"
    CARD_OTHER = "Card"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="payment_methods")
    cardholder_name = models.CharField(max_length=150)
    brand = models.CharField(max_length=40, default=CARD_OTHER)
    last4 = models.CharField(max_length=4)
    expiry_month = models.PositiveSmallIntegerField()
    expiry_year = models.PositiveSmallIntegerField()
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-is_default", "-created_at"]

    def __str__(self):
        return f"{self.brand} ending in {self.last4}"

    @property
    def expiry_display(self):
        return f"{self.expiry_month:02d}/{str(self.expiry_year)[-2:]}"


class Review(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reviews")
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE, related_name="reviews")
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name="review")
    rating = models.PositiveSmallIntegerField(default=5)
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.hotel.name} review by {self.user.email}"
