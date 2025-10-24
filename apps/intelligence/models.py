from django.db import models

# Create your models here.
import uuid
from django.db import models
from django.conf import settings

# ... ReportStatus and OrderStatus enums remain the same ...
class ReportStatus(models.TextChoices):
    AWAITING_SCOUT_DISPATCH = 'AWAITING_SCOUT_DISPATCH', 'Awaiting Scout Dispatch'
    SCOUT_DISPATCHED = 'SCOUT_DISPATCHED', 'Scout Dispatched'
    COMPILING_DATA = 'COMPILING_DATA', 'Compiling Data'
    IN_REVIEW = 'IN_REVIEW', 'In Review'
    COMPLETE = 'COMPLETE', 'Complete'

class OrderStatus(models.TextChoices):
    SUCCEEDED = 'SUCCEEDED', 'Succeeded'
    FAILED = 'FAILED', 'Failed'


class IntelligenceReport(models.Model):
    # This model is unchanged. Its logic is internal to our business.
    property = models.ForeignKey('reviews.Property', on_delete=models.PROTECT, related_name='intelligence_reports')
    client = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='commissioned_reports')
    status = models.CharField(max_length=50, choices=ReportStatus.choices, default=ReportStatus.AWAITING_SCOUT_DISPATCH, db_index=True)
    report_file = models.FileField(upload_to='intelligence_reports/%Y/%m/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Verified Report for {self.property.name} ({self.status})"

    class Meta:
        ordering = ['-created_at']


class ReportOrder(models.Model):
    """ A record of the financial transaction for a single IntelligenceReport. """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    report = models.OneToOneField(IntelligenceReport, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    
    # --- REVISED FIELD ---
    # We now store Paystack's transaction reference. It's the key to their system.
    paystack_transaction_ref = models.CharField(max_length=255, unique=True, db_index=True)
    
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=50, choices=OrderStatus.choices)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Order {self.id} for {self.report.property.name}"

    class Meta:
        ordering = ['-created_at']