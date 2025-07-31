from django import forms
from .models import Property, PropertyUnit, Review
from django.utils.translation import gettext_lazy as _

class PropertyForm(forms.ModelForm):
    """
    Form for a user to submit a new property.
    Includes all the structured address fields that will eventually
    be populated by the Google Places API.
    """
    class Meta:
        model = Property
        fields = [
            'name',
            'address',
            # --- All structured address fields are included ---
            'country',
            'state',
            'city',
            'postal_code',
            # --- These will be made hidden with JavaScript on Day 5 ---
            'latitude',
            'longitude',
            'google_place_id',
        ]
        labels = {
            'name': _("Property Name"),
            'address': _("Full Address"),
            'country': _("Country"),
            'state': _("State / Province / Region"),
            'city': _("City / Town"),
            'postal_code': _("Postal Code / ZIP Code"),
        }
        help_texts = {
            'name': _("The main name of the Estate or Apartment Building."),
            'address': _("Start typing, and select the property from the search results."),
        }
        # We will use JavaScript in Day 5 to make these fields hidden,
        # but for now, they are visible for testing purposes.
        # widgets = {
        #     'latitude': forms.HiddenInput(),
        #     'longitude': forms.HiddenInput(),
        #     'google_place_id': forms.HiddenInput(),
        # }


class PropertyUnitForm(forms.ModelForm):
    """
    Form for adding a specific unit to a property.
    """
    class Meta:
        model = PropertyUnit
        # The 'property' will be linked in the view, not set by the user here.
        fields = ['unit_identifier']
        labels = {
            'unit_identifier': _("Your Unit Identifier"),
        }
        help_texts = {
            'unit_identifier': _("e.g., 'Apartment A521' or 'House 7, Block 10'"),
        }


class ReviewForm(forms.ModelForm):
    """
    Form for the main review content.
    """
    class Meta:
        model = Review
        # The 'unit', 'author', and 'status' will be set in the view.
        fields = [
            'security_rating',
            'electricity_rating',
            'water_rating',
            'road_network_rating',
            'mobile_network_rating',
            'management_rating',
            'pros',
            'cons'
        ]
        # Use widgets to customize the appearance of form fields.
        widgets = {
            'pros': forms.Textarea(attrs={'rows': 5, 'placeholder': _('e.g., Great security, constant power, quiet environment...')}),
            'cons': forms.Textarea(attrs={'rows': 5, 'placeholder': _('e.g., Excessive bills, incompetent management, flooding during raining season, frequent water shortages...')}),
        }
        labels = {
            'security_rating': _("How would you rate the security?"),
            'electricity_rating': _("How would you rate the electricity supply?"),
            'water_rating': _("How would you rate the water supply & quality?"),
            'road_network_rating': _("How would you rate the road network, congestion, drainage?"),
            'mobile_network_rating': _("How would you rate the mobile network for calls and browsing?"),
            'management_rating': _("How would you rate the property management?"),
            
            'pros': _("Pros"),
            'cons': _("Cons"),
        }