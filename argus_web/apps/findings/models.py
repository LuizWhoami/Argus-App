from django.db import models


class Finding(models.Model):
    """Achado de vulnerabilidade (nuclei). NUNCA auto-verified."""
    SEV_INFO = "info"
    SEV_LOW = "low"
    SEV_MEDIUM = "medium"
    SEV_HIGH = "high"
    SEV_CRITICAL = "critical"
    SEV_CHOICES = [
        (SEV_INFO, "Info"),
        (SEV_LOW, "Low"),
        (SEV_MEDIUM, "Medium"),
        (SEV_HIGH, "High"),
        (SEV_CRITICAL, "Critical"),
    ]

    VERIF_SUSPICIOUS = "suspicious"
    VERIF_VERIFIED = "verified"
    VERIF_FALSE_POSITIVE = "false_positive"
    VERIF_ACCEPTED_RISK = "accepted_risk"
    VERIF_CHOICES = [
        (VERIF_SUSPICIOUS, "Suspeito"),
        (VERIF_VERIFIED, "Verificado"),
        (VERIF_FALSE_POSITIVE, "Falso positivo"),
        (VERIF_ACCEPTED_RISK, "Risco aceito"),
    ]

    program = models.ForeignKey(
        "programs.Program",
        on_delete=models.CASCADE,
        related_name="findings",
    )
    asset = models.ForeignKey(
        "assets.Asset",
        on_delete=models.CASCADE,
        related_name="findings",
    )
    endpoint = models.ForeignKey(
        "assets.Endpoint",
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="findings",
    )

    template_id = models.CharField(max_length=255, db_index=True)
    title = models.CharField(max_length=255)
    severity = models.CharField(max_length=20, choices=SEV_CHOICES,
                                default=SEV_INFO, db_index=True)
    url = models.CharField(max_length=2048, blank=True)

    description = models.TextField(blank=True)
    tags = models.CharField(max_length=500, blank=True)
    cve = models.CharField(max_length=500, blank=True)
    cwe = models.CharField(max_length=500, blank=True)
    reference = models.CharField(max_length=1000, blank=True)
    curl_command = models.TextField(blank=True)
    matcher = models.CharField(max_length=200, blank=True)
    extracted = models.CharField(max_length=500, blank=True)

    verification = models.CharField(max_length=20, choices=VERIF_CHOICES,
                                    default=VERIF_SUSPICIOUS, db_index=True)
    verification_note = models.TextField(blank=True)
    verified_by = models.ForeignKey(
        "auth.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="+",
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    confidence = models.FloatField(default=0.5)

    first_seen = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-last_seen",)
        constraints = [
            models.UniqueConstraint(
                fields=["program", "asset", "template_id", "url"],
                name="uniq_finding_dedup",
            )
        ]
        indexes = [
            models.Index(fields=["program", "-last_seen"]),
            models.Index(fields=["severity", "verification"]),
        ]

    def __str__(self):
        return f"[{self.severity}] {self.title} @ {self.url}"
