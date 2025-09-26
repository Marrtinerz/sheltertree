from django.contrib import admin
from .models import CustomUser, FeatureInterest, Feedback

# Register your models here.

@admin.register(CustomUser)
class UserAdmin(admin.ModelAdmin):
        list_display = ('username', 'email', 'first_name', 'last_name')
        
        

@admin.register(FeatureInterest)
class FeatureInterestAdmin(admin.ModelAdmin):
    list_display = ('feature_name', 'email', 'phone_number', 'created_at')
    list_filter = ('feature_name',)
    search_fields = ('email', 'phone_number')
    

@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ('category', 'email', 'is_resolved', 'created_at')
    list_filter = ('category', 'is_resolved')
    search_fields = ('email', 'message')
