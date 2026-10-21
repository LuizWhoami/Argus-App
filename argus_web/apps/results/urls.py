from django.urls import path

from . import views

app_name = "results"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("assets/", views.list_assets, name="assets"),
    path("endpoints/", views.list_endpoints, name="endpoints"),
    path("apis/", views.list_apis, name="apis"),
    path("api-recon/", views.api_recon, name="api_recon"),
    path("params/", views.list_params, name="params"),
    path("mark/<str:kind>/<int:pk>/", views.mark_verification,
         name="mark"),
    path("export/", views.export_json, name="export"),
]
