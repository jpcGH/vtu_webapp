from .models import SiteSetting


def site_context(request):
    return {'site_settings': SiteSetting.objects.first()}
