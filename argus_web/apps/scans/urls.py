from django.urls import path

from . import views

app_name = "scans"

urlpatterns = [
    path("", views.list_scans, name="list"),
    path("new/<slug:slug>/", views.new_scan, name="new"),
    path("<int:pk>/", views.detail_scan, name="detail"),
    path("<int:pk>/status/", views.status_partial, name="status"),
    path("<int:pk>/cancel/", views.cancel, name="cancel"),
]
