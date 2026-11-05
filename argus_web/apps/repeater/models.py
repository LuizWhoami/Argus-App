from django.conf import settings
from django.db import models


class RepeaterRequest(models.Model):
    """Historico de requests enviados pelo Repeater."""
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="repeater_requests",
    )
    method = models.CharField(max_length=10)
    url = models.CharField(max_length=2048, db_index=True)
    request_headers = models.JSONField(default=dict)
    request_body = models.TextField(blank=True)

    response_status = models.IntegerField(null=True, blank=True)
    response_headers = models.JSONField(default=dict, blank=True)
    response_body = models.TextField(blank=True)
    response_size = models.IntegerField(null=True, blank=True)
    response_time_ms = models.IntegerField(null=True, blank=True)

    error = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["owner", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.method} {self.url[:60]} [{self.response_status or 'err'}]"
