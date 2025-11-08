# In apps/core/models.py
from django.db import models
from django.conf import settings

# ... (your existing core models, if any) ...

class PlatformFeedback(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    source_url = models.CharField(max_length=512)
    feedback_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Platform Feedback"
        verbose_name_plural = "Platform Feedback"

    def __str__(self):
        return f"Feedback from {self.user.email if self.user else 'Anonymous'} on {self.created_at.date()}"