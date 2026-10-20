from django.urls import path

from . import actions, diff_views, export_views, stage_views, views

app_name = "scans"

urlpatterns = [
    path("", views.list_scans, name="list"),
    path("new/<slug:slug>/", views.new_scan, name="new"),
    path("<int:pk>/", views.detail_scan, name="detail"),
    path("<int:pk>/status/", views.status_partial, name="status"),
    path("<int:pk>/cancel/", views.cancel, name="cancel"),
    path("<int:pk>/review/", actions.toggle_review, name="review"),
    path("<int:pk>/delete/", actions.delete_scan, name="delete"),
    path("<int:pk>/stage/<str:name>/", stage_views.stage_detail,
         name="stage"),
    path("<int:pk>/export.md", export_views.export_markdown,
         name="export_md"),
    path("<int:pk>/export.csv", export_views.export_csv,
         name="export_csv"),
    path("<int:pk>/export.json", export_views.export_json,
         name="export_json"),
    path("<int:pk>/diff/", diff_views.diff_view, name="diff"),
]
