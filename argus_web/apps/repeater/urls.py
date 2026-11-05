from django.urls import path

from . import views

app_name = "repeater"

urlpatterns = [
    path("", views.index, name="index"),
    path("api/send/", views.api_send, name="api_send"),
    path("api/history/", views.api_history, name="api_history"),
]
