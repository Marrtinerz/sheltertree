# apps/users/forms.py
from django import forms
from allauth.account.forms import SignupForm

class MinimalSignupForm(SignupForm):
    # We only need to define the fields that are NOT already handled
    # by the default allauth signup form (email, username, password).
    # In this case, we don't need to add anything. The default form is perfect for Stage 1.
    # This file is a placeholder for now, but is still necessary to tell allauth to use the default.
    # In Day 7(b), we will create a DIFFERENT form for the Stage 2 profile completion.
    pass