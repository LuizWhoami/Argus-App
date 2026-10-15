from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models


class Program(models.Model):
    """Programa de Bug Bounty pertencente a um usuario."""
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="programs",
    )
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True)
    description = models.TextField(blank=True)

    max_rps = models.PositiveIntegerField(
        default=5,
        validators=[MinValueValidator(1), MaxValueValidator(100)],
    )
    aggressive_scanning = models.BooleanField(default=False)
    destructive_testing = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-updated_at",)
        indexes = [models.Index(fields=["owner", "-updated_at"])]
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "name"],
                name="uniq_program_name_per_owner",
            )
        ]

    def __str__(self):
        return self.name

    def allowed_patterns(self):
        return list(self.scope_entries.filter(kind="allow")
                    .values_list("pattern", flat=True))

    def excluded_patterns(self):
        return list(self.scope_entries.filter(kind="exclude")
                    .values_list("pattern", flat=True))


class ScopeEntry(models.Model):
    """Entrada de escopo: allow ou exclude. Exclude tem precedencia."""
    KIND_ALLOW = "allow"
    KIND_EXCLUDE = "exclude"
    KIND_CHOICES = [
        (KIND_ALLOW, "Permitido"),
        (KIND_EXCLUDE, "Excluido"),
    ]

    program = models.ForeignKey(
        Program, on_delete=models.CASCADE, related_name="scope_entries",
    )
    kind = models.CharField(max_length=10, choices=KIND_CHOICES)
    pattern = models.CharField(max_length=255,
                               help_text="Ex: *.example.com ou api.example.com")
    note = models.CharField(max_length=255, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("kind", "pattern")
        constraints = [
            models.UniqueConstraint(
                fields=["program", "kind", "pattern"],
                name="uniq_scope_entry",
            )
        ]

    def __str__(self):
        return f"{self.get_kind_display()}: {self.pattern}"
