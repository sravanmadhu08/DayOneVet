from django.conf import settings

from .models import SiteSettings


def site_settings(request):
    settings_obj = SiteSettings.objects.first()
    return {
        "site_settings": settings_obj,
        "has_allauth": settings.HAS_ALLAUTH,
    }
