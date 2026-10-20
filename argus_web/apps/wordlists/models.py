from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.db import models


class Wordlist(models.Model):
    KIND_API = "api"
    KIND_CONTENT = "content"
    KIND_PARAMS = "params"
    KIND_SUBDOMAINS = "subdomains"
    KIND_USERAGENT = "useragent"
    KIND_CHOICES = [
        (KIND_API, "API paths"),
        (KIND_CONTENT, "Content discovery"),
        (KIND_PARAMS, "Parametros"),
        (KIND_SUBDOMAINS, "Subdominios"),
        (KIND_USERAGENT, "User-Agents"),
    ]

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name="wordlists",
        help_text="Vazio = embutida no Argus",
    )
    name = models.CharField(max_length=120)
    kind = models.CharField(max_length=20, choices=KIND_CHOICES,
                            db_index=True)
    description = models.TextField(blank=True)

    content = models.TextField(
        blank=True,
        help_text="1 item por linha. # para comentarios.",
    )
    file = models.FileField(
        upload_to="wordlists/", null=True, blank=True,
        validators=[FileExtensionValidator(allowed_extensions=["txt"])],
    )
    is_builtin = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("kind", "name")
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "name"],
                name="uniq_wordlist_per_owner",
            )
        ]

    def __str__(self):
        return f"{self.kind}:{self.name}"

    # --------------------------------------------------------------
    def load_lines(self) -> list[str]:
        """Retorna a lista efetiva de linhas (content ou file)."""
        raw = ""
        if self.content:
            raw = self.content
        elif self.file:
            try:
                self.file.open("r")
                raw = self.file.read()
                if isinstance(raw, bytes):
                    raw = raw.decode("utf-8", errors="replace")
            finally:
                try:
                    self.file.close()
                except Exception:
                    pass

        out = []
        for line in raw.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            out.append(line)
        return out
