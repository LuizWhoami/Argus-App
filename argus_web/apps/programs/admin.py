from django.contrib import admin

from .models import Program, ScopeEntry


class ScopeEntryInline(admin.TabularInline):
    model = ScopeEntry
    extra = 1


@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "is_active", "max_rps", "updated_at")
    list_filter = ("is_active", "aggressive_scanning", "destructive_testing")
    search_fields = ("name", "slug", "owner__username")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [ScopeEntryInline]


@admin.register(ScopeEntry)
class ScopeEntryAdmin(admin.ModelAdmin):
    list_display = ("program", "kind", "pattern", "note")
    list_filter = ("kind",)
    search_fields = ("pattern", "program__name")
