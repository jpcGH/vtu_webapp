from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('apps.accounts.urls')),
    path('ledger/', include('apps.ledger.urls')),
    path('payments/', include('apps.payments.urls')),
    path('vtu/', include('apps.vtu.urls')),
    path('referrals/', include('apps.referrals.urls')),
    path('dashboard/', include('apps.dashboard.urls')),
    path('', include('apps.core.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
