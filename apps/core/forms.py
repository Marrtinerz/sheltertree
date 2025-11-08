# In apps/core/forms.py
from django import forms
from .models import PlatformFeedback

class PlatformFeedbackForm(forms.ModelForm):
    class Meta:
        model = PlatformFeedback
        fields = ['feedback_text']
        widgets = {
            'feedback_text': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Have feedback or suggestions to improve ShelterTree?'
            })
        }