from django.contrib import admin

from .models import Scan, ScanEvent, ScanStage


class ScanStageInline(admin.TabularInline):
    model = ScanStage
    extra = 0
    readonly_fields = ("started_at", "finished_at")


class ScanEventInline(admin.TabularInline):
    model = ScanEvent
    extra = 0
    readonly_fields = ("ts",)


@admin.register(Scan)
class ScanAdmin(admin.ModelAdmin):
    list_display = ("id", "target", "program", "status",
                    "assets_found", "endpoints_found", "created_at")
    list_filter = ("status", "program")
    search_fields = ("target",)
    readonly_fields = ("created_at", "started_at", "finished_at")
    inlines = [ScanStageInline, ScanEventInline]
