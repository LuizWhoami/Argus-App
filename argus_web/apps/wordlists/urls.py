from django.urls import path

from . import views

app_name = "wordlists"

urlpatterns = [
    path("", views.list_wordlists, name="list"),
    path("new/", views.new_wordlist, name="new"),
    path("<int:pk>/", views.preview_wordlist, name="preview"),
    path("<int:pk>/edit/", views.edit_wordlist, name="edit"),
    path("<int:pk>/delete/", views.delete_wordlist, name="delete"),
    path("<int:pk>/download/", views.download_wordlist, name="download"),
]
