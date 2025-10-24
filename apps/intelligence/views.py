# In apps/intelligence/views.py

import uuid
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
# from paystackapi.paystack import Paystack
# from paystackapi.base import PaystackAPIError
from django.views.generic import FormView
from .forms import ReportInquiryForm

from apps.reviews.models import Property

# This will eventually come from settings or a model. For the sprint, it's a constant.
# Paystack requires the amount in the lowest currency unit (kobo for NGN).
VERIFIED_REPORT_PRICE_KOBO = 1000000 * 100  # ₦1,000,000.00

# class InitiatePaymentView(LoginRequiredMixin, View):
#     """
#     Handles the request to start a payment process for a Verified Report.
#     This view is responsible for:
#     1. Validating the request.
#     2. Generating a unique transaction reference.
#     3. Calling the Paystack API to initialize a transaction.
#     4. Redirecting the user to the secure Paystack payment page.
#     """
#     def post(self, request, *args, **kwargs):
#         property_id = request.POST.get('property_id')
#         property = get_object_or_404(Property, pk=property_id)
#         user = request.user

#         paystack = Paystack(secret_key=settings.PAYSTACK_SECRET_KEY)
        
#         # We generate a unique reference for this specific transaction attempt.
#         # This is CRITICAL for idempotency and tracking.
#         transaction_ref = str(uuid.uuid4())

#         try:
#             # The callback_url is where Paystack will redirect the user after payment.
#             # We will build this view on Day 4.
#             callback_url = request.build_absolute_uri(reverse_lazy('intelligence:payment-callback'))

#             response = paystack.transaction.initialize(
#                 reference=transaction_ref,
#                 email=user.email,
#                 amount=VERIFIED_REPORT_PRICE_KOBO,
#                 callback_url=callback_url,
#                 metadata={'property_id': property.id, 'user_id': user.id}
#             )

#             if response['status'] is True:
#                 # Redirect the user to the secure payment page.
#                 auth_url = response['data']['authorization_url']
#                 return redirect(auth_url)
#             else:
#                 messages.error(request, "We couldn't process your request at this time. Please try again.")
#                 return redirect('reviews:property_detail', pk=property.id)

#         except PaystackAPIError as e:
#             # Log the error e.error_response
#             messages.error(request, "There was an issue connecting to the payment gateway. Please try again.")
#             return redirect('reviews:property_detail', pk=property.id)
        


class SheltertreeIntelligenceLandingPageView(FormView):
    """
    Renders the main landing page for the ShelterTree Intelligence platform
    and handles the lead capture form submission.
    """
    template_name = 'intelligence/sheltertree_intelligence_landing_page.html'
    form_class = ReportInquiryForm
    success_url = reverse_lazy('intelligence:inquiry-thank-you')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = "ShelterTree Intelligence"
        return context

    def form_valid(self, form):
        # The business logic for handling the inquiry will be implemented on Day 3.
        print(f"Form is valid. Data: {form.cleaned_data}") # Placeholder for Day 2
        return super().form_valid(form)