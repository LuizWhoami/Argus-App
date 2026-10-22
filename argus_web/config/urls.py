from django.contrib import admin
from django.http import JsonResponse
from django.shortcuts import redirect
from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path


def healthz(request):
    return JsonResponse({"status": "ok"})


def root(request):
    if request.user.is_authenticated:
        return redirect("results:dashboard")
    return redirect("accounts:login")


urlpatterns = [
    path("", root, name="root"),
    path("healthz", healthz),
    path("admin/", admin.site.urls),
    path("accounts/", include("apps.accounts.urls")),
    path("programs/", include("apps.programs.urls")),
    path("scans/", include("apps.scans.urls")),
    path("results/", include("apps.results.urls")),
    path("wordlists/", include("apps.wordlists.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL,
                          document_root=settings.MEDIA_ROOT)
