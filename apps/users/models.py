from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _
from apps.locations.models import Country

class CustomUser(AbstractUser):
    class UserType(models.TextChoices):
        RENTER = 'RENTER', _('Renter')
        HOMEOWNER = 'HOMEOWNER', _('Homeowner')

    # --- Fields for Staged Onboarding (Stage 2) ---
    # These fields will be collected after the initial signup.
    user_type = models.CharField(
        max_length=10, 
        choices=UserType.choices, 
        blank=True,
        verbose_name=_("User Type")
    )
    country = models.ForeignKey(
        Country, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name=_("Country")
    )
    onboarding_complete = models.BooleanField(
        default=False,
        help_text=_("Indicates if the user has completed the second stage of onboarding.")
    )

    # --- Fields for Phone Number & Verification (Stage 3) ---
    # These fields support the future phone number verification flow.
    phone_number = models.CharField(
        max_length=30, 
        blank=True,
        verbose_name=_("Phone Number (E.164 format)")
    )
    is_phone_verified = models.BooleanField(
        default=False,
        verbose_name=_("Phone Verified")
    )
    # --- The two fields below are for the verification process itself ---
    phone_verification_code = models.CharField(
        max_length=6, 
        blank=True, 
        null=True,
        verbose_name=_("Phone Verification Code")
    )
    phone_verification_timestamp = models.DateTimeField(
        blank=True, 
        null=True,
        verbose_name=_("Verification Code Timestamp")
    )

    def __str__(self):
        return self.username