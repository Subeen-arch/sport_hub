from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse
from django.urls import include, path
from django.views import View

from accounts.views import StaffSessionView
from support.views import ContactView


class HealthView(View):
    def get(self, request):
        return JsonResponse({"status": "ok", "service": "sporthub-api"})


urlpatterns = [
    path("api/health/", HealthView.as_view()),
    path("api/auth/", include("accounts.urls")),
    path("api/admin/session/", StaffSessionView.as_view()),
    path("api/", include("catalog.urls")),
    path("api/", include("commerce.urls")),
    path("api/", include("outlets.urls")),
    path("api/admin/", include("accounts.staff_urls")),
    path("api/messages/", ContactView.as_view()),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
