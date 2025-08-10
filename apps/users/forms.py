# apps/users/forms.py
from django import forms
from allauth.account.forms import SignupForm
from .models import CustomUser, Country
from django.utils.translation import gettext_lazy as _


class MinimalSignupForm(SignupForm):
    # We only need to define the fields that are NOT already handled
    # by the default allauth signup form (email, username, password).
    # In this case, we don't need to add anything. The default form is perfect for Stage 1.
    # This file is a placeholder for now, but is still necessary to tell allauth to use the default.
    # In Day 7(b), we will create a DIFFERENT form for the Stage 2 profile completion.
    pass

class ProfileCompletionForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        # These are the fields we want to collect in Stage 2.
        fields = ['first_name', 'last_name', 'user_type', 'country']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Make fields required for this form submission
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True
        self.fields['user_type'].required = True
        self.fields['country'].required = True

        # Set user-friendly labels and queryset for the country field
        self.fields['country'].queryset = Country.objects.all().order_by('name')
        self.fields['country'].label = _("Your Home Country")
        self.fields['user_type'].label = _("How do you plan to use ShelterTree?")