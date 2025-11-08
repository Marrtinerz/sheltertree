from django.views.generic import TemplateView, CreateView
from django.core.mail import send_mail
from django.template.loader import render_to_string
from apps.users.forms import FeedbackForm
from apps.users.models import Feedback
from django.urls import reverse_lazy
from django.conf import settings
from django.shortcuts import render
from django.views.decorators.http import require_http_methods
from .forms import PlatformFeedbackForm



class TermsOfServiceView(TemplateView):
    template_name = 'core/terms_of_service.html'

class PrivacyPolicyView(TemplateView):
    template_name = 'core/privacy_policy.html'

class HelpCenterView(TemplateView):
    template_name = 'core/help_center.html'
    

class FeedbackCreateView(CreateView):
    model = Feedback
    form_class = FeedbackForm
    template_name = 'core/contact_us.html'
    success_url = reverse_lazy('core:contact_success')

    def get_initial(self):
        # Pre-fill the email if the user is logged in
        if self.request.user.is_authenticated:
            return {'email': self.request.user.email}
        return {}

    def form_valid(self, form):
        # If the user is logged in, associate their account with the feedback
        if self.request.user.is_authenticated:
            form.instance.user = self.request.user
        
        # --- Send Email Notification ---
        feedback = form.save(commit=False) # Don't save to DB just yet
        
        # Prepare email context
        email_context = {
            'category': feedback.get_category_display(),
            'email': feedback.email,
            'phone': feedback.phone_number,
            'message': feedback.message,
        }
        # Render the text and HTML versions of the email
        email_body = render_to_string('account/email/feedback_notification.txt', email_context)
        html_email_body = render_to_string('account/email/feedback_notification.html', email_context)

        # Send the email
        send_mail(
            subject=f"New ShelterTree Feedback: {feedback.get_category_display()}",
            message=email_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=['support@mysheltertree.com'], # IMPORTANT: Change this
            html_message=html_email_body,
            fail_silently=False, # We want to know if email sending fails
        )
        
        # Now, call the parent method which saves the object to the database
        return super().form_valid(form)
    

@require_http_methods(["POST"])
def submit_feedback(request):
    form = PlatformFeedbackForm(request.POST)
    if form.is_valid():
        feedback = form.save(commit=False)
        if request.user.is_authenticated:
            feedback.user = request.user
        feedback.source_url = request.META.get('HTTP_REFERER', 'unknown')
        feedback.save()
    # The success partial can live in the 'core' app's templates
    return render(request, 'core/partials/feedback_success.html')