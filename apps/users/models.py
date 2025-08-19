from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _
from apps.locations.models import Country
from django.utils import timezone
import random

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
        unique=True,
        null=True,
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
    phone_verification_attempts = models.PositiveIntegerField(default=0)
    phone_lockout_until = models.DateTimeField(
        blank=True, 
        null=True,
        verbose_name=_("Phone Verification Lockout Until")
    )

    def __str__(self):
        return self.username

    def can_request_new_code(self):
        """
        Checks if at least 60 seconds have passed since the last code request.
        """
        if not self.phone_verification_timestamp:
            return True
        return (timezone.now() - self.phone_verification_timestamp).total_seconds() > 60
    
    def verify_phone_code(self, code):
        """
        Checks if a provided code is valid and has not expired.
        Returns True if valid, False otherwise.
        """
        # Check 1: Is the code correct?
        if self.phone_verification_code != code:
            return False
        
        # Check 2: Has the code expired (e.g., after 10 minutes)?
        time_limit = timezone.now() - timezone.timedelta(minutes=10)
        if self.phone_verification_timestamp < time_limit:
            return False
            
        # If both checks pass, the code is valid.
        return True
        
        
    # --- NEW: Fields for Brute-Force Protection ---
    def generate_phone_verification_code(self, phone_number):
        """
        Generates a new code and RESETS the attempt counters and lockout.
        """
        self.phone_number = phone_number
        self.phone_verification_code = str(random.randint(100000, 999999))
        self.phone_verification_timestamp = timezone.now()
        # --- THE CRITICAL RESET ---
        self.phone_verification_attempts = 0
        self.phone_lockout_until = None
        self.save(update_fields=['phone_number', 'phone_verification_code', 'phone_verification_timestamp', 'phone_verification_attempts', 'phone_lockout_until'])

    def mark_phone_as_verified(self):
        """
        Finalizes verification and clears ALL temporary fields.
        """
        self.is_phone_verified = True
        self.phone_verification_code = None
        self.phone_verification_timestamp = None
        self.phone_verification_attempts = 0
        self.phone_lockout_until = None
        self.save(update_fields=['is_phone_verified', 'phone_verification_code', 'phone_verification_timestamp', 'phone_verification_attempts', 'phone_lockout_until'])

