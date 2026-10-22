from django.contrib import admin

from .models import Finding


@admin.register(Finding)
class FindingAdmin(admin.ModelAdmin):
    list_display = ("severity", "title", "program", "asset",
                    "template_id", "verification", "last_seen")
    list_filter = ("severity", "verification", "program")
    search_fields = ("title", "template_id", "url", "asset__hostname")
    readonly_fields = ("first_seen", "last_seen")
