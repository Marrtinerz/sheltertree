from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from apps.locations.models import Country, State
from django.contrib.postgres.search import SearchVectorField
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVector
from django.conf import settings
from django.db.models import Q, Count, Avg, F, OuterRef, Subquery
from django.db.models.functions import Coalesce

# --- Status Enums ---

class PropertyStatus(models.TextChoices):
    PENDING_APPROVAL = 'PENDING', _('Pending Approval')
    APPROVED = 'APPROVED', _('Approved')
    REJECTED = 'REJECTED', _('Rejected')
    NEEDS_CORRECTION = 'NEEDS_CORRECTION', _('Needs Correction')
    ADMIN_REMOVED = 'ADMIN_REMOVED', _('Removed by Admin')

class ReviewStatus(models.TextChoices):
    PENDING_PROPERTY_APPROVAL = 'PROP_PENDING', _('Pending Property Approval')
    PENDING_CONTENT_REVIEW = 'CONT_PENDING', _('Pending Content Review')
    APPROVED = 'APPROVED', _('Approved')
    REJECTED = 'REJECTED', _('Rejected')
    PROPERTY_REJECTED = 'PROP_REJECTED', _('Property Rejected')
    USER_DELETED = 'USER_DELETED', _('Deleted by User')
    ADMIN_REMOVED = 'ADMIN_REMOVED', _('Removed by Admin')
    PROPERTY_REMOVED = 'PROPERTY_REMOVED', _('Associated Property Removed')
    UNDER_REVIEW = 'UNDER_REVIEW', _('Under Review / Quarantined')

# --- Other Enums ---

class PropertyType(models.TextChoices):
    """
    Defines the types of properties users can review.
    """
    APARTMENT_BUILDING = 'APARTMENT', _('Stand-alone Apartment Building')
    GATED_ESTATE = 'ESTATE', _('Gated Estate / Community')
    STANDALONE_HOUSE = 'HOUSE', _('Stand-alone House')
    OTHER = 'OTHER', _('Other')

class OverallRating(models.IntegerChoices):
    VERY_BAD = 1, _('Very Bad')
    BAD = 2, _('Bad')
    AVERAGE = 3, _('Average')
    GOOD = 4, _('Good')
    EXCELLENT = 5, _('Excellent')

class ResidenceLength(models.IntegerChoices):
    LESS_THAN_6_MONTHS = 6, _("less than 6 months")
    SIX_MONTHS_TO_1_YEAR = 12, _("6 months to 1 year")
    ONE_TO_2_YEARS = 24, _("1 - 2 years")
    TWO_TO_4_YEARS = 48, _("2 - 4 years")
    OVER_4_YEARS = 60, _("more than 4 years")
    
class FloodingSeverity(models.TextChoices):
    NONE = 'NONE', _('No Flooding: The property and access roads remain dry.')
    EXTERNAL = 'EXTERNAL', _('External Only: Access roads flood, but the compound is fine.')
    COMPOUND = 'COMPOUND', _('Compound Flooding: Water pools in parking/common areas, but does not enter buildings.')
    CATASTROPHIC = 'CATASTROPHIC', _('Internal Flooding: Water enters the home/building.')


class PropertyQuerySet(models.QuerySet):
    """
    A custom QuerySet for the Property model to hold reusable
    filtering and annotation logic.
    """
    def with_reputation_data(self):
        """
        Annotates the QuerySet with approved review counts and a true overall
        average rating using robust, Coalesce-wrapped subqueries.
        """
        # Define the base for our subqueries: only approved reviews for the parent property.
        approved_reviews = Review.objects.filter(
            unit__property_id=OuterRef('pk'),
            status=ReviewStatus.APPROVED
        ).values('unit__property_id') # Must group by the property to aggregate

        # Subquery for the count of approved reviews.
        review_count_subquery = approved_reviews.annotate(
            count=Count('pk')
        ).values('count')

        # --- THE CRITICAL FIX IS HERE ---
        # Subquery for the overall average rating.
        # Each Avg() is now wrapped in Coalesce to gracefully handle properties with zero reviews.
        overall_avg_subquery = approved_reviews.annotate(
            overall_avg=(
                Coalesce(Avg('security_rating'), 0.0) +
                Coalesce(Avg('electricity_rating'), 0.0) +
                Coalesce(Avg('water_rating'), 0.0) +
                Coalesce(Avg('management_rating'), 0.0) +
                Coalesce(Avg('road_network_rating'), 0.0) +
                Coalesce(Avg('mobile_network_rating'), 0.0)
            ) / 6.0
        ).values('overall_avg')
        
        # Annotate the main queryset with the results of our safe subqueries.
        return self.annotate(
            review_count=Coalesce(Subquery(review_count_subquery), 0),
            overall_average_rating=Coalesce(
                Subquery(overall_avg_subquery), 
                0.0, 
                output_field=models.FloatField()
            )
        )

# --- The World-Class Manager ---
class PropertyManager(models.Manager):
    def get_queryset(self):
        return PropertyQuerySet(self.model, using=self._db)

    def with_reputation_data(self):
        """
        A clean proxy method to call the QuerySet's method.
        Allows for the elegant Property.objects.with_reputation_data() syntax.
        """
        return self.get_queryset().with_reputation_data()

class Property(models.Model):
    name = models.CharField(max_length=255, verbose_name=_("Property Name"), blank=True)
    address = models.CharField(max_length=255, help_text=_("Full address of the property"), null=False, blank=False)
    google_place_id = models.CharField(max_length=255, unique=True, null=True, blank=True, help_text=_("Google Places API unique ID."))
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    city = models.CharField(max_length=100, blank=True, null=True, verbose_name=_("City"))
    postal_code = models.CharField(max_length=20, blank=True, verbose_name=_("Postal Code / ZIP Code"))
    
    country = models.ForeignKey(
        Country,
        on_delete=models.PROTECT,
        null=False,
        blank=False,
        verbose_name=_("Country")
    )
    
    state = models.ForeignKey(
        State,
        on_delete=models.PROTECT,
        null=False,
        blank=False,
        verbose_name=_("State / Province / Region")
    )
    property_type = models.CharField(
        max_length=20,
        choices=PropertyType.choices,
        verbose_name=_("Type of Property")
    )

    status = models.CharField(
        max_length=20,
        choices=PropertyStatus.choices,
        default=PropertyStatus.PENDING_APPROVAL,
        verbose_name=_("Status")
    )
    search_vector = SearchVectorField(null=True, editable=False) # editable=False is a best practice

    added_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="added_properties")
    created_at = models.DateTimeField(auto_now_add=True)

    # Use our new, intelligent manager for all queries.
    objects = PropertyManager()

    class Meta:
        verbose_name = _("Property")
        verbose_name_plural = _("Properties")
        indexes = [
            GinIndex(fields=['search_vector'])
        ]

    
    def get_admin_display_name(self, max_length=50):
        """
        The definitive method for generating a clean display name FOR THE ADMIN.
        If the name is missing, it provides a clean, truncated version of the address.
        """
        if self.name and self.name.strip():
            return self.name
        
        if self.address and len(self.address) > max_length:
            return f"{self.address[:max_length].strip()}..."
        elif self.address:
            return self.address
        
        return f"Property #{self.pk}"

    def get_email_subject_name(self, max_length=20):
        """
        A new, dedicated, and high-precision method for generating a
        very short name specifically for email subject lines,
        perfectly enforcing the character limit.
        """
        # --- THE DEFINITIVE, CORRECT LOGIC ---
        
        # First, determine the source string: the name if it exists, otherwise the address.
        source_string = self.name.strip() if self.name and self.name.strip() else self.address
        
        # If there is no source string at all, fall back to the PK.
        if not source_string:
            return f"Prop #{self.pk}"
            
        # Now, apply the truncation logic to the chosen source string.
        if len(source_string) > max_length:
            return f"{source_string[:max_length].strip()}..."
        
        return source_string

    # --- THIS IS THE CORRECTED __str__ METHOD ---
    def __str__(self):
        """
        The string representation used throughout the Django Admin.
        It now correctly uses our new helper method for a clean and
        always-informative display.
        """
        # Get the clean, reliable display name from our helper method.
        display_name = self.get_admin_display_name()
        
        # Return the final, formatted string.
        return f"{display_name} [{self.get_status_display()}]"
    
    
    def get_display_name(self, truncate_address=False, max_length=35):
        """
        The definitive, site-wide method for displaying the property's name.
        It is now context-aware.

        :param truncate_address: If True, fall back to a truncated address.
        :param max_length: The max length for the truncated address.
        """
        if self.name:
            return self.name
        
        if truncate_address:
            # This path is for list/card views
            if len(self.address) > max_length:
                return f"{self.address[:max_length].strip()}..."
            return self.address
        
        # This path is for page headings (<h1>) and other full-page contexts
        return _("Unnamed Property")


    def get_title_name(self):
        """
        The definitive method for generating a browser title.
        If the name is missing, it returns a truncated version of the address
        to ensure the title is always informative and clean.
        """
        if self.name:
            return self.name
        
        # Truncate the address to a reasonable length for a title tag
        if len(self.address) > 45:
            return f"{self.address[:45]}..."
        return self.address


class PropertyUnit(models.Model):
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='units', verbose_name=_("Parent Property"))
    unit_identifier = models.CharField(max_length=50, help_text=_("e.g., 'Apartment A521' or 'House 7, Block 10'"), verbose_name=_("Unit Identifier"))
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('property', 'unit_identifier')
        verbose_name = _("Property Unit")
        verbose_name_plural = _("Property Units")

    def __str__(self):
        """
        Provides a context-rich string representation for the admin.
        """
        # --- THE PREMIUM UPGRADE ---
        # It now includes the parent property's admin display name.
        return f"{self.unit_identifier} ({self.property.get_admin_display_name()})"


class Review(models.Model):
    unit = models.ForeignKey(PropertyUnit, on_delete=models.CASCADE, related_name='reviews', verbose_name=_("Property Unit"))
    
    # --- CRITICAL IMPROVEMENT ---
    # Change on_delete to SET_NULL to preserve reviews if a user deletes their account.
    # The author field must also be allowed to be NULL.
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, # Allow the author field to be empty
        verbose_name=_("Author")
    )
    
    residence_length = models.IntegerField(choices=ResidenceLength.choices, verbose_name=_("How long did you live here?"))
    security_rating = models.IntegerField(choices=OverallRating.choices, verbose_name=_("Security Rating"))
    electricity_rating = models.IntegerField(choices=OverallRating.choices, verbose_name=_("Electricity Rating"))
    water_rating = models.IntegerField(choices=OverallRating.choices, verbose_name=_("Water Rating"))
    mobile_network_rating = models.IntegerField(choices=OverallRating.choices, verbose_name=_("Mobile Network Rating"))
    road_network_rating = models.IntegerField(choices=OverallRating.choices, verbose_name=_("Road Network Rating"))
    management_rating = models.IntegerField(choices=OverallRating.choices, verbose_name=_("Management Rating"))
    
    flooding_severity = models.CharField(
        max_length=20,
        choices=FloodingSeverity.choices,
        verbose_name=_("Flooding During Heavy Rains"),
        # The new, shorter, more effective help text
        help_text=_("How bad is the flooding during heavy rains?")
    )

    pros = models.TextField(help_text=_("What are the best things about living here?"), verbose_name=_("Pros"))
    
    # --- MINOR FIX ---
    # Corrected the help_text for the 'cons' field.
    cons = models.TextField(help_text=_("What are the unique challenges or worst things about living here?"), verbose_name=_("Cons"))

    status = models.CharField(
        max_length=20,
        choices=ReviewStatus.choices,
        default=ReviewStatus.PENDING_PROPERTY_APPROVAL,
        verbose_name=_("Status")
    )
    
    # These new fields are perfectly implemented.
    is_author_phone_verified = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Review")
        verbose_name_plural = _("Reviews")

    # The save method is perfectly implemented.
    def save(self, *args, **kwargs):
        if self._state.adding and self.author:
            self.is_author_phone_verified = self.author.is_phone_verified
        super().save(*args, **kwargs)
        
    def __str__(self):
        # Handle the case where the author has been deleted
        author_name = self.author.username if self.author else "Anonymous"
        return f"Review by {author_name} for {self.unit} [{self.get_status_display()}]"
    
    def get_overall_rating(self):
        """
        Calculates the average rating for this specific review instance.
        Returns the average as a float, or 0.0 if no ratings are present.
        """
        ratings = [
            self.security_rating, self.electricity_rating, self.water_rating,
            self.management_rating, self.road_network_rating, self.mobile_network_rating
        ]
        
        # Filter out None values in case some ratings are optional
        valid_ratings = [r for r in ratings if r is not None]
        
        if not valid_ratings:
            return 0.0
            
        return sum(valid_ratings) / len(valid_ratings)
    

class Vote(models.Model):
    class VoteChoice(models.IntegerChoices):
        UPVOTE = 1, 'Upvote'
        DOWNVOTE = -1, 'Downvote'
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    review = models.ForeignKey('Review', on_delete=models.CASCADE, related_name='votes')
    value = models.IntegerField(choices=VoteChoice.choices)

    class Meta:
        # --- THE CRITICAL CONSTRAINT ---
        # This ensures a user can only have one vote record per review.
        unique_together = ('user', 'review')
    

# ==============================================================================
# PROXY MODELS FOR ADMIN MODERATION QUEUES
# These models allow us to create separate, dedicated admin interfaces for
# filtering and managing specific subsets of our core data.
# ==============================================================================

class PendingProperty(Property):
    class Meta:
        proxy = True
        verbose_name = 'Pending Property'
        verbose_name_plural = '  Property Approval Queue' # Indent for admin sorting

class PendingReview(Review):
    class Meta:
        proxy = True
        verbose_name = 'Pending Review'
        verbose_name_plural = ' Review Content Queue' # Indent for admin sorting

class FlaggedReview(Review):
    class Meta:
        proxy = True
        verbose_name = 'Flagged Review'
        verbose_name_plural = ' Flagged Review Queue' # Indent for admin sorting