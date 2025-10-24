# In apps/intelligence/forms.py
from django import forms

TIER_CHOICES = (
    ('COMPREHENSIVE', 'Comprehensive Verification'),
    ('STANDARD', 'Standard Verification'),
    ('ESSENTIAL', 'Essential Verification'),
)

class ReportInquiryForm(forms.Form):
    name = forms.CharField(label="Full Name", max_length=100, widget=forms.TextInput(attrs={'placeholder': ' '}))
    email = forms.EmailField(label="Email Address", widget=forms.EmailInput(attrs={'placeholder': ' '}))
    phone_number = forms.CharField(label="Phone Number", max_length=20, widget=forms.TextInput(attrs={'placeholder': ' '}))
    property_details = forms.CharField(label="Property Address or Details", help_text="Provide the address or link to the property.", widget=forms.Textarea(attrs={'rows': 4, 'placeholder': ' '}))
    
    # Honeypot remains for bot protection
    honeypot = forms.CharField(widget=forms.HiddenInput(), required=False)
    
    # Tier selection remains for our internal context
    selected_tier = forms.ChoiceField(choices=TIER_CHOICES, widget=forms.HiddenInput(), required=False)