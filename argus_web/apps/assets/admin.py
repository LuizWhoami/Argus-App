from django.contrib import admin

from .models import Asset, DNSRecord, Endpoint, HTTPProbe, Parameter


class DNSRecordInline(admin.TabularInline):
    model = DNSRecord
    extra = 0


class HTTPProbeInline(admin.TabularInline):
    model = HTTPProbe
    extra = 0


@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ("hostname", "program", "ip", "is_alive", "last_seen")
    list_filter = ("is_alive", "program")
    search_fields = ("hostname", "ip")
    inlines = [DNSRecordInline, HTTPProbeInline]


@admin.register(Endpoint)
class EndpointAdmin(admin.ModelAdmin):
    list_display = ("url", "asset", "method", "status_code", "kind", "source")
    list_filter = ("kind", "source", "status_code")
    search_fields = ("url", "asset__hostname")


@admin.register(Parameter)
class ParameterAdmin(admin.ModelAdmin):
    list_display = ("name", "location", "endpoint")
    list_filter = ("location",)
    search_fields = ("name", "endpoint__url")
