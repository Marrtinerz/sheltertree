from django.contrib import admin
from .models import IntelligenceReport, ReportOrder

@admin.register(IntelligenceReport)
class IntelligenceReportAdmin(admin.ModelAdmin):
    # This admin is unchanged.
    list_display = ('property', 'client', 'status', 'created_at', 'updated_at')
    list_filter = ('status',)
    search_fields = ('property__name', 'client__email')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(ReportOrder)
class ReportOrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'report', 'user', 'status', 'amount_paid', 'created_at')
    list_filter = ('status',)
    
    # --- REVISED FIELD ---
    readonly_fields = (
        'id', 'report', 'user', 'paystack_transaction_ref',
        'amount_paid', 'created_at', 'updated_at'
    )