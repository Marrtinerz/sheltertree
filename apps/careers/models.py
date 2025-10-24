# In apps/careers/models.py
from django.db import models
from django.urls import reverse

class JobPosting(models.Model):
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, help_text="A unique, URL-friendly version of the title.")
    location = models.CharField(max_length=100, default="Remote")
    description = models.TextField(help_text="Full job description. You can use Markdown for formatting.")
    
    is_active = models.BooleanField(default=True, db_index=True, help_text="Uncheck this to hide the job posting from the public site.")
    published_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-published_at']

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('careers:job_detail', kwargs={'slug': self.slug})