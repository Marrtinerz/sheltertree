import logging
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.contrib.sites.models import Site

# Get a logger instance for professional error handling
logger = logging.getLogger(__name__)

class NotificationService:
    """
    The single source of truth for sending all transactional and moderation
    emails. This service sends multipart emails (HTML with a plain text fallback)
    and delegates all content rendering to the template layer.
    """

    def _get_base_context(self):
        """Returns the base context for all emails, like the site domain."""
        current_site = Site.objects.get_current()
        return {
            'site_name': current_site.name,
            'domain': current_site.domain,
        }

    def _send_email(self, template_base_name, context, recipient_list):
        """
        A private, central method for rendering and sending multipart emails.
        This is the definitive, professional pattern.
        """
        if not recipient_list or not recipient_list[0]:
            logger.warning(f"Attempted to send email '{template_base_name}' but recipient list was empty.")
            return

        full_context = {**self._get_base_context(), **context}
        
        try:
            # 1. Render the subject from its dedicated .txt file.
            subject = render_to_string(f'notifications/{template_base_name}_subject.txt', full_context).strip()
            
            # 2. Render the HTML body.
            html_body = render_to_string(f'notifications/{template_base_name}.html', full_context)

            # 3. Render the PLAIN TEXT body from its own dedicated .txt file.
            text_body = render_to_string(f'notifications/{template_base_name}.txt', full_context)
            
            # 4. Use EmailMultiAlternatives, which is designed for this.
            msg = EmailMultiAlternatives(
                subject=subject,
                body=text_body, # The plain text version is the 'body'
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=recipient_list
            )
            # Attach the HTML version as an alternative.
            msg.attach_alternative(html_body, "text/html")
            
            # 5. Send the email.
            msg.send(fail_silently=False)
            logger.info(f"Successfully sent multipart email '{template_base_name}' to {recipient_list[0]}")

        except Exception as e:
            logger.error(f"CRITICAL: Could not send email for template '{template_base_name}'. Reason: {e}")


    # --- PROPERTY MODERATION NOTIFICATIONS ---
    # These public methods remain beautifully simple. They are unchanged.

    def send_property_approved_email(self, property_obj):
        if settings.SKIP_APPROVAL_EMAIL_SEND:
            return
        
        user = property_obj.added_by
        
        # --- THE CRITICAL FIX IS HERE ---
        # 1. Prepare the special, truncated display name in the service.
        email_subject_name = property_obj.get_email_subject_name()
        property_display_name = property_obj.get_display_name(truncate_address=True) # Use the frontend logic
        
        # 2. Add the prepared name to the context.
        context = {
            'user': user, 
            'property': property_obj,
            'email_subject_name': email_subject_name,
            'property_display_name': property_display_name,
        }
        
        self._send_email(
            template_base_name='property_approved',
            context=context,
            recipient_list=[user.email] if user else None
        )

    def send_property_rejected_email(self, property_obj, reason=""):
        user = property_obj.added_by
        email_subject_name = property_obj.get_email_subject_name()
        property_display_name = property_obj.get_display_name(truncate_address=True)
        context = {
            'user': user, 
            'property': property_obj, 
            'submission_type': 'property',
            'email_subject_name': email_subject_name,
            'property_display_name': property_display_name,
            'reason': reason
        }
        self._send_email(
            template_base_name='submission_rejected',
            context=context,
            recipient_list=[user.email] if user else None
        )

    # --- REVIEW MODERATION NOTIFICATIONS ---

    def send_review_approved_email(self, review_obj):
        if settings.SKIP_REVIEW_EMAIL_SEND:
            return
        
        user = review_obj.author
        email_subject_name = review_obj.unit.property.get_email_subject_name()
        property_display_name = review_obj.unit.property.get_display_name(truncate_address=True)
        unit_identifier = review_obj.unit.unit_identifier # Get the simple string here
        context = {
            'user': user, 
            'review': review_obj,
            'email_subject_name': email_subject_name,
            'property_display_name': property_display_name,
            'unit_identifier': unit_identifier,
        }
        self._send_email(
            template_base_name='review_approved',
            context=context,
            recipient_list=[user.email] if user else None
        )

    def send_review_rejected_email(self, review_obj, reason=""):
        user = review_obj.author
        email_subject_name = review_obj.unit.property.get_email_subject_name()
        property_display_name = review_obj.unit.property.get_display_name(truncate_address=True)
        context = {
            'user': user, 
            'submission_type': 'review', 
            'submission_obj': review_obj, 
            'email_subject_name': email_subject_name,
            'property_display_name': property_display_name,
            'reason': reason
        }
        self._send_email(
            template_base_name='submission_rejected',
            context=context,
            recipient_list=[user.email] if user else None
        )
        
    
    # --- NEW: ONBOARDING & ENGAGEMENT NOTIFICATIONS ---

    def send_welcome_email(self, user):
        """
        Sends a personal welcome email to a new user after they verify.
        """
        context = {'user': user}
        self._send_email(
            template_base_name='welcome',
            context=context,
            recipient_list=[user.email]
        )

# Create a single, reusable instance of the service
notification_service = NotificationService()