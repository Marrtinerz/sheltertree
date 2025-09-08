import os
from django import template
from django.conf import settings
from django.templatetags.static import static

register = template.Library()

@register.simple_tag
def get_avatar_sprites():
    """
    Scans the static directory for available avatar sprites and returns a list
    of their filenames without the extension.
    This is a robust way to manage avatars without hardcoding them.
    """
    try:
        # Define the path relative to your STATICFILES_DIRS
        # Assumes your sprites are in 'static/img/avatars/sprites/'
        sprite_dir_path = os.path.join(settings.BASE_DIR, 'static', 'img', 'avatars', 'sprites')
        
        # Get all files in the directory
        files = os.listdir(sprite_dir_path)
        
        # Filter for SVG files and strip the '.svg' extension
        sprite_names = [f.split('.')[0] for f in files if f.endswith('.svg')]
        
        return sprite_names # Return a sorted list for consistent order
    
    except (FileNotFoundError, IndexError):
        # If the directory doesn't exist or something goes wrong, return an empty list
        return []