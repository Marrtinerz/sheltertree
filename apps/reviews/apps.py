from django.apps import AppConfig


class ReviewsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.reviews'
    
    
    def ready(self):
        """
        This method is called when the app is loaded.
        It's the standard place to import and connect signals.
        """
        import apps.reviews.signals # noqa  
