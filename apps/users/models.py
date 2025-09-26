from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _
from apps.locations.models import Country
from django.utils import timezone
import random
from django.conf import settings

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
    
    # --- NEW: The Display Name Preference Field ---
    class DisplayNamePreference(models.TextChoices):
        USERNAME = 'USERNAME', _('Username')
        INITIALS = 'INITIALS', _('First Name & Last Initial')


    display_name_preference = models.CharField(
        max_length=20,
        choices=DisplayNamePreference.choices,
        default=DisplayNamePreference.USERNAME,
        verbose_name=_("Public Display Name (Choose an option)")
    )
    
    onboarding_complete = models.BooleanField(
        default=False,
        help_text=_("Indicates if the user has completed the second stage of onboarding.")
    )
    
    # --- NEW, SIMPLER AVATAR FIELD ---
    # We only need to store the path to the chosen static SVG file.
    avatar = models.CharField(
        max_length=255, 
        blank=True, 
        null=True,
        verbose_name=_("Avatar Path")
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


    # --- NEW: A Helper Method for the templates ---
    def get_review_author_name(self):
        """
        Returns the name to be displayed on reviews based on user preference.
        """
        if self.display_name_preference == self.DisplayNameChoice.FIRST_NAME_INITIAL and self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name[0]}."
        return self.username
    
    def get_avatar_url(self):
        """
        The single source of truth for displaying an avatar.
        It's now much simpler: if a user has chosen an avatar, show it.
        Otherwise, show the default.
        """
        from django.templatetags.static import static
        if self.avatar:
            return static(self.avatar)
        return static('img/avatars/default_sprite.svg')
    
    def get_display_name(self):
        """
        Returns the user's public-facing name based on their chosen preference.
        This now handles the "First Name & Last Initial" format.
        """
        # THE FIX: We check for the INITIALS preference first.
        # This requires both a first name and a last name to be present.
        if (self.display_name_preference == CustomUser.DisplayNamePreference.INITIALS 
            and self.first_name and self.last_name):
            # Format: "James T."
            return f"{self.first_name.capitalize()} {self.last_name[0].upper()}."
        
        # The default fallback is always the username for all other cases.
        return self.username
    
    # --- NEW, WORLD-CLASS METHOD ---
    def get_masked_phone_number(self):
        """
        Returns a privacy-protected, masked version of the user's phone number.
        Shows the international prefix and the last 4 digits.
        Example: +2348031234567 -> +234 •••• 4567
        """
        if not self.phone_number:
            return ""

        phone = str(self.phone_number)
        
        # E.164 format includes a '+'. We keep the '+' and the next 3 digits (country code).
        # We also keep the last 4 digits.
        if len(phone) > 8: # A reasonable length to apply masking
            return f"{phone[:7]} xxxx"
        else:
            # If the number is too short for some reason, just return a generic masked version.
            return "xxxx"
    
    
    
# apps/users/models.py
class FeatureInterest(models.Model):
    email = models.EmailField(blank=True, null=True)
    phone_number = models.CharField(max_length=30, blank=True, null=True) # E.164 format
    feature_name = models.CharField(max_length=100) # e.g., "The Taproot"
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.email or self.phone_number} interested in {self.feature_name}"
    

class Feedback(models.Model):
    class FeedbackCategory(models.TextChoices):
        GENERAL = 'GENERAL', _('General Feedback')
        IDEA = 'IDEA', _('I have an idea for a new feature')
        BUG = 'BUG', _('I found a bug or incorrect information')
        PARTNER = 'PARTNER', _('I am a property manager or owner')
        OTHER = 'OTHER', _('Something else')

    # Link to the user if they are logged in, but allow anonymous feedback.
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    
    # User-provided data
    email = models.EmailField()
    phone_number = models.CharField(max_length=30, blank=True, verbose_name=_("WhatsApp Number (Optional)"))
    category = models.CharField(max_length=20, choices=FeedbackCategory.choices, default=FeedbackCategory.GENERAL)
    message = models.TextField()
    
    # Admin tracking fields
    created_at = models.DateTimeField(auto_now_add=True)
    is_resolved = models.BooleanField(default=False)

    def __str__(self):
        return f"Feedback ({self.get_category_display()}) from {self.email}"