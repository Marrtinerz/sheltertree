from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from apps.locations.models import Country, State
from django.contrib.postgres.search import SearchVectorField
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVector
from django.conf import settings

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
    LESS_THAN_6_MONTHS = 6, _("Less than 6 months")
    SIX_MONTHS_TO_1_YEAR = 12, _("6 months to 1 year")
    ONE_TO_2_YEARS = 24, _("1 - 2 years")
    TWO_TO_4_YEARS = 48, _("2 - 4 years")
    OVER_4_YEARS = 60, _("More than 4 years")


# --- Main Models ---

class Property(models.Model):
    name = models.CharField(max_length=255, verbose_name=_("Property Name"), blank=True)
    address = models.CharField(max_length=255, help_text=_("Full address of the property"), null=False, blank=False)
    google_place_id = models.CharField(max_length=255, unique=True, null=True, blank=True, help_text=_("Google Places API unique ID."))
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    city = models.CharField(max_length=100, blank=False, null=False, verbose_name=_("City"))
    postal_code = models.CharField(max_length=20, blank=True, verbose_name=_("Postal Code / ZIP Code"))
    
    
    country = models.ForeignKey(
        Country,
        on_delete=models.PROTECT, # Use PROTECT instead of SET_NULL
        null=False,              # Cannot be NULL in the database
        blank=False,             # Cannot be blank in forms
        verbose_name=_("Country")
    )
    
    state = models.ForeignKey(
        State,
        on_delete=models.PROTECT, # Use PROTECT instead of SET_NULL
        null=False,              # Cannot be NULL in the database
        blank=False,             # Cannot be blank in forms
        verbose_name=_("State / Province / Region")
    )
    property_type = models.CharField(
        max_length=20,
        choices=PropertyType.choices,
        # Remove the default to force the user to make an active choice
        verbose_name=_("Type of Property")
    )

    status = models.CharField(
        max_length=20,
        choices=PropertyStatus.choices,
        default=PropertyStatus.PENDING_APPROVAL,
        verbose_name=_("Status")
    )
    search_vector = SearchVectorField(null=True, blank=True)

    added_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="added_properties")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Property")
        verbose_name_plural = _("Properties")
        indexes = [
            GinIndex(fields=['search_vector'])
        ]

    def save(self, *args, **kwargs):
        """
        Overrides the save method to ensure the search_vector is updated
        whenever a property is saved.
        """
        # First, save the object to the database as normal.
        super().save(*args, **kwargs)

        # Now, perform a *separate* update operation for the search_vector
        # on THIS instance only. This is the correct pattern.
        # This avoids the FieldError because we are not using joins inside the .update() call itself.
        # The joins happen in the filter and annotation parts of a different query.
        vector = SearchVector(
            'name', 'address', 'city', 'state__name', 'country__name'
        )
        
        # Filter for the current instance, annotate it with the new vector,
        # and then update the search_vector field with the annotated value.
        # This looks complex, but it's the right way to tell Django to do this.
        Property.objects.filter(pk=self.pk).update(search_vector=vector)

    def __str__(self):
        return f"{self.name} [{self.get_status_display()}]"


class PropertyUnit(models.Model):
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='units', verbose_name=_("Parent Property"))
    unit_identifier = models.CharField(max_length=50, help_text=_("e.g., 'Apartment A521' or 'House 7, Block 10'"), verbose_name=_("Unit Identifier"))
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('property', 'unit_identifier')
        verbose_name = _("Property Unit")
        verbose_name_plural = _("Property Units")

    def __str__(self):
        return f"{self.unit_identifier}, {self.property.name}"


class Review(models.Model):
    unit = models.ForeignKey(PropertyUnit, on_delete=models.CASCADE, related_name='reviews', verbose_name=_("Property Unit"))
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name=_("Author"))
    residence_length = models.IntegerField(
        choices=ResidenceLength.choices,
        verbose_name=_("How long did you live here?")
    )
    security_rating = models.IntegerField(choices=OverallRating.choices, verbose_name=_("Security Rating"))
    electricity_rating = models.IntegerField(choices=OverallRating.choices, verbose_name=_("Electricity Rating"))
    water_rating = models.IntegerField(choices=OverallRating.choices, verbose_name=_("Water Rating"))
    mobile_network_rating = models.IntegerField(choices=OverallRating.choices, verbose_name=_("Mobile Network Rating"))
    road_network_rating = models.IntegerField(choices=OverallRating.choices, verbose_name=_("Road Network Rating"))
    management_rating = models.IntegerField(choices=OverallRating.choices, verbose_name=_("Management Rating"))

    pros = models.TextField(help_text=_("What are the best things about living here?"), verbose_name=_("Pros"))
    cons = models.TextField(help_text=_("What are the best things about living here?"), verbose_name=_("Cons"))

    status = models.CharField(
        max_length=20,
        choices=ReviewStatus.choices,
        default=ReviewStatus.PENDING_PROPERTY_APPROVAL,
        verbose_name=_("Status")
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Review")
        verbose_name_plural = _("Reviews")

    def __str__(self):
        return f"Review for {self.unit} [{self.get_status_display()}]"