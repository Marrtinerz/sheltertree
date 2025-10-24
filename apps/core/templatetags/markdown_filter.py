# In apps/core/templatetags/markdown_filter.py
import markdown
from django import template
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter(name='markdownify')
def markdownify(text):
    """
    Processes Markdown text and returns it as safe HTML.
    """
    # Convert markdown to HTML
    html = markdown.markdown(text)
    # Mark the output as safe to prevent auto-escaping
    return mark_safe(html)