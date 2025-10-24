# In apps/careers/admin.py
from django.contrib import admin
from .models import JobPosting

@admin.register(JobPosting)
class JobPostingAdmin(admin.ModelAdmin):
    list_display = ('title', 'location', 'is_active', 'published_at')
    list_filter = ('is_active', 'location')
    search_fields = ('title', 'description')
    prepopulated_fields = {'slug': ('title',)}