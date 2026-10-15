from django.urls import path

from . import views

app_name = "programs"

urlpatterns = [
    path("", views.list_programs, name="list"),
    path("new/", views.create_program, name="create"),
    path("<slug:slug>/", views.detail_program, name="detail"),
    path("<slug:slug>/edit/", views.edit_program, name="edit"),
    path("<slug:slug>/scope/add/", views.add_scope_entry, name="scope_add"),
    path("<slug:slug>/scope/<int:pk>/delete/",
         views.delete_scope_entry, name="scope_delete"),
]
