from django.contrib import admin

from .models import Wordlist


@admin.register(Wordlist)
class WordlistAdmin(admin.ModelAdmin):
    list_display = ("name", "kind", "owner", "is_builtin",
                    "line_count", "updated_at")
    list_filter = ("kind", "is_builtin")
    search_fields = ("name", "description")
    readonly_fields = ("created_at", "updated_at")

    @admin.display(description="linhas")
    def line_count(self, obj):
        return len(obj.load_lines())
