# apps/users/forms.py
from django import forms
from allauth.account.forms import SignupForm
from .models import CustomUser, Country, FeatureInterest
from django.utils.translation import gettext_lazy as _
import phonenumbers
from django.core.exceptions import ValidationError
from django.utils.safestring import mark_safe

class MinimalSignupForm(SignupForm):
    # We only need to define the fields that are NOT already handled
    # by the default allauth signup form (email, username, password).
    # In this case, we don't need to add anything. The default form is perfect for Stage 1.
    # This file is a placeholder for now, but is still necessary to tell allauth to use the default.
    # In Day 7(b), we will create a DIFFERENT form for the Stage 2 profile completion.
    pass

class ProfileEditForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        # We only allow editing of these specific, non-sensitive fields.
        fields = ['first_name', 'last_name', 'user_type', 'country']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True


class OnboardingForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'user_type', 'country']

    def __init__(self, *args, **kwargs):
        # Run the standard __init__ to bind the instance
        super().__init__(*args, **kwargs)

        # --- THE DEFINITIVE FIX ---
        # We check if the form is bound to a model instance and if that
        # instance's user_type is currently empty.
        if self.instance and not self.instance.user_type:
            # Instead of setting a field's 'initial' value, we directly
            # modify the attribute on the in-memory instance itself.
            # This becomes the new source data for the form renderer.
            self.instance.user_type = CustomUser.UserType.RENTER

        # Configure the required fields as before
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True
        self.fields['user_type'].required = True
        self.fields['country'].required = True
        self.fields['country'].empty_label = "--- Select Your Country ---"

# class ProfileCompletionForm(forms.ModelForm):
#     class Meta:
#         model = CustomUser
#         # These are the fields we want to collect in Stage 2.
#         fields = ['first_name', 'last_name', 'user_type', 'country']

#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
        
#         # Make fields required for this form submission
#         self.fields['first_name'].required = True
#         self.fields['last_name'].required = True
#         self.fields['user_type'].required = True
#         self.fields['country'].required = True

#         # Set user-friendly labels and queryset for the country field
#         self.fields['country'].queryset = Country.objects.all().order_by('name')
#         self.fields['country'].label = _("Your Home Country")
#         self.fields['user_type'].label = _("How do you plan to use ShelterTree?")


class PhoneNumberForm(forms.Form):
    phone_number = forms.CharField(label="Your Phone Number")
    country_code = forms.CharField(widget=forms.HiddenInput())

    def __init__(self, *args, **kwargs):
        """
        Accept the user object from the view.
        """
        # Pop 'user' from kwargs before calling super(), as the default Form.__init__ doesn't expect it.
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

    def clean(self):
        """
        Perform cross-field validation.
        """
        cleaned_data = super().clean()
        phone_number = cleaned_data.get('phone_number')
        country_code = cleaned_data.get('country_code')

        if not self.user:
            # This should never happen if the view is correct, but it's a good safeguard.
            raise ValidationError("An unexpected error occurred. User not found.")

        if not phone_number or not country_code:
            # This will be caught by the individual field validators, but it's good practice.
            return cleaned_data

        try:
            parsed_number = phonenumbers.parse(phone_number, country_code)
            if not phonenumbers.is_valid_number(parsed_number):
                raise ValidationError("Please enter a valid phone number for the selected country.")
            
            phone_number_e164 = phonenumbers.format_number(parsed_number, phonenumbers.PhoneNumberFormat.E164)
            cleaned_data['phone_number_e164'] = phone_number_e164

            # --- THE VALIDATION THAT USES self.user ---
            # Check if this phone number is already in use by another verified user.
            if CustomUser.objects.filter(phone_number=phone_number_e164, is_phone_verified=True).exclude(pk=self.user.pk).exists():
                raise ValidationError("This phone number is already associated with another verified account.")

        except phonenumbers.NumberParseException:
            raise ValidationError("Could not parse the phone number. Please check the format.")
        
        return cleaned_data

class PhoneVerificationCodeForm(forms.Form):
    code = forms.CharField(
        label="6-Digit Verification Code",
        max_length=6,
        widget=forms.TextInput(attrs={'autocomplete': 'one-time-code'})
    )

    def __init__(self, *args, **kwargs):
        """
        Accept the request object from the view so we can access the user.
        """
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

    def clean_code(self):
        """
        This method is automatically called by Django during form validation.
        This is where we check if the code is correct.
        """
        code = self.cleaned_data.get('code')
        user = self.request.user

        if not user.verify_phone_code(code):
            # If the model method returns False, we raise a validation error.
            # This error will be attached to the 'code' field and displayed on the form.
            raise ValidationError("The code is invalid or has expired. Please try again.")
        
        return code


class FeatureInterestForm(forms.ModelForm):
    """
    A form to capture user interest in a new feature.
    Includes robust validation and a non-persistent consent checkbox.
    """
    
    # This is the consent checkbox. It is part of the form's validation,
    # but it is NOT saved to the database model.
    agree_to_terms = forms.BooleanField(
        required=True,
        label=mark_safe(
            # NOTE: You must create a page at the '/privacy-policy/' URL.
            'I agree to receive a one-time notification and have read the <a href="/privacy-policy/" target="_blank">Privacy Policy</a>.'
        )
    )

    class Meta:
        model = FeatureInterest
        # These are the only fields that will be saved to the database.
        fields = ['email', 'phone_number']
        # We will render the form manually in the template for better UX,
        # so we don't need to define widgets or labels here.

    def clean_phone_number(self):
        """
        Provides lenient but effective validation for the phone number field.
        """
        phone_number = self.cleaned_data.get('phone_number')
        
        # It's an optional field, so an empty value is perfectly valid.
        if not phone_number:
            return phone_number

        try:
            # We attempt to parse the number without a specific region.
            # This requires the user to enter the number with a '+' country code.
            parsed_number = phonenumbers.parse(phone_number, None)
            
            # `is_possible_number` is a good, non-aggressive check.
            if not phonenumbers.is_possible_number(parsed_number):
                raise ValidationError("Please enter a valid phone number, including the country code (e.g., +234...).")
            
            # Return the clean, standard E.164 format for consistent data storage.
            return phonenumbers.format_number(parsed_number, phonenumbers.PhoneNumberFormat.E164)
        
        except phonenumbers.NumberParseException:
            raise ValidationError("The phone number format is not recognized. Please include your country code (e.g., +234...).")

    def clean(self):
        """
        This method performs cross-field validation after each individual
        field's clean method has been called.
        """
        cleaned_data = super().clean()
        email = cleaned_data.get('email')
        phone_number = cleaned_data.get('phone_number')

        # Enforce our business rule: the user MUST provide at least one contact method.
        if not email and not phone_number:
            # This raises a non_field_error, which is displayed at the top of the form.
            raise ValidationError(
                "Please provide either an email address or a WhatsApp number to be notified.",
                code='no_contact_method'
            )
        
        return cleaned_data