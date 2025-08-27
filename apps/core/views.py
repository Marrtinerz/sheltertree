from django.views.generic import TemplateView

class TermsOfServiceView(TemplateView):
    template_name = 'core/terms_of_service.html'

class PrivacyPolicyView(TemplateView):
    template_name = 'core/privacy_policy.html'

class HelpCenterView(TemplateView):
    template_name = 'core/help_center.html'