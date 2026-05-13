from django.apps import AppConfig


class AssistantConfig(AppConfig):
    name = 'assistant'

    def ready(self):
        # Automatically fix the Site object for local development
        from django.conf import settings
        if settings.DEBUG:
            try:
                from django.contrib.sites.models import Site
                site = Site.objects.get(id=settings.SITE_ID)
                if site.domain == 'example.com':
                    site.domain = 'localhost:8000'
                    site.name = 'CelestAI Local'
                    site.save()
                    print(f"Updated Site {settings.SITE_ID} to localhost:8000")
            except Exception as e:
                # Silently fail if DB is not ready
                pass
