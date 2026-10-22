from django.db import models
from django.utils import timezone


class Scan(models.Model):
    STATUS_QUEUED = "queued"
    STATUS_RUNNING = "running"
    STATUS_COMPLETED = "completed"
    STATUS_FAILED = "failed"
    STATUS_CANCELLED = "cancelled"
    STATUS_CHOICES = [
        (STATUS_QUEUED, "Queued"),
        (STATUS_RUNNING, "Running"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_FAILED, "Failed"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    TERMINAL_STATES = {STATUS_COMPLETED, STATUS_FAILED, STATUS_CANCELLED}

    program = models.ForeignKey(
        "programs.Program",
        on_delete=models.CASCADE,
        related_name="scans",
    )
    target = models.CharField(max_length=255, db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES,
                              default=STATUS_QUEUED, db_index=True)
    requested_by = models.ForeignKey(
        "auth.User", on_delete=models.SET_NULL, null=True,
        related_name="scans",
    )

    # Configuracao efetiva
    wordlist = models.ForeignKey(
        "wordlists.Wordlist",
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="scans",
    )
    api_scan = models.BooleanField(default=True)
    dir_scan = models.BooleanField(default=False)  # content discovery opt-in
    dir_depth = models.PositiveSmallIntegerField(default=2)
    dir_wordlist = models.ForeignKey(
        "wordlists.Wordlist",
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="dir_scans",
    )
    vuln_scan = models.BooleanField(default=False)  # opt-in por seguranca
    crawl = models.BooleanField(default=True)
    crawl_depth = models.PositiveSmallIntegerField(default=3)

    # Contadores (denormalizados para a UI)
    assets_found = models.PositiveIntegerField(default=0)
    endpoints_found = models.PositiveIntegerField(default=0)
    api_endpoints_found = models.PositiveIntegerField(default=0)
    parameters_found = models.PositiveIntegerField(default=0)

    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["program", "-created_at"]),
            models.Index(fields=["status", "-created_at"]),
        ]

    def __str__(self):
        return f"scan#{self.pk} {self.target} [{self.status}]"

    # ------------------------------------------------------------------
    # Transicoes controladas
    # ------------------------------------------------------------------
    def mark_running(self):
        if self.status != self.STATUS_QUEUED:
            raise ValueError(f"nao pode ir para running a partir de {self.status}")
        self.status = self.STATUS_RUNNING
        self.started_at = timezone.now()
        self.save(update_fields=["status", "started_at"])

    def mark_completed(self):
        if self.status != self.STATUS_RUNNING:
            raise ValueError(f"nao pode ir para completed a partir de {self.status}")
        self.status = self.STATUS_COMPLETED
        self.finished_at = timezone.now()
        self.save(update_fields=["status", "finished_at"])

    def mark_failed(self, error: str):
        if self.status in self.TERMINAL_STATES:
            raise ValueError(f"scan ja terminal ({self.status})")
        self.status = self.STATUS_FAILED
        self.error_message = error[:5000]
        self.finished_at = timezone.now()
        self.save(update_fields=["status", "error_message", "finished_at"])

    def mark_cancelled(self):
        if self.status in self.TERMINAL_STATES:
            raise ValueError(f"scan ja terminal ({self.status})")
        self.status = self.STATUS_CANCELLED
        self.finished_at = timezone.now()
        self.save(update_fields=["status", "finished_at"])

    @property
    def is_api_recon(self) -> bool:
        """Scan dedicado a API recon: api_scan on, crawl off."""
        return self.api_scan and not self.crawl

    def is_terminal(self) -> bool:
        return self.status in self.TERMINAL_STATES


class ScanStage(models.Model):
    STATUS_PENDING = "pending"
    STATUS_RUNNING = "running"
    STATUS_COMPLETED = "completed"
    STATUS_FAILED = "failed"
    STATUS_SKIPPED = "skipped"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_RUNNING, "Running"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_FAILED, "Failed"),
        (STATUS_SKIPPED, "Skipped"),
    ]

    scan = models.ForeignKey(
        Scan, on_delete=models.CASCADE, related_name="stages",
    )
    order = models.PositiveSmallIntegerField()
    name = models.CharField(max_length=40)      # scope, subdomains, dns, ...
    status = models.CharField(max_length=20, choices=STATUS_CHOICES,
                              default=STATUS_PENDING)
    result_count = models.PositiveIntegerField(default=0)
    message = models.CharField(max_length=512, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("scan", "order")
        constraints = [
            models.UniqueConstraint(
                fields=["scan", "name"],
                name="uniq_stage_per_scan",
            )
        ]

    def __str__(self):
        return f"{self.scan_id}:{self.name}[{self.status}]"


class ScanEvent(models.Model):
    LEVEL_INFO = "info"
    LEVEL_WARN = "warn"
    LEVEL_ERROR = "error"
    LEVEL_CHOICES = [
        (LEVEL_INFO, "info"),
        (LEVEL_WARN, "warn"),
        (LEVEL_ERROR, "error"),
    ]

    scan = models.ForeignKey(
        Scan, on_delete=models.CASCADE, related_name="events",
    )
    ts = models.DateTimeField(auto_now_add=True, db_index=True)
    level = models.CharField(max_length=10, choices=LEVEL_CHOICES,
                             default=LEVEL_INFO)
    stage = models.CharField(max_length=40, blank=True)
    message = models.CharField(max_length=1000)

    class Meta:
        ordering = ("-ts",)

    def __str__(self):
        return f"[{self.level}] {self.message[:60]}"


    # Snapshot no fim do scan
    snap_location = models.CharField(max_length=10, blank=True)

class ScanReview(models.Model):
    """Curadoria humana de um scan: 'eu olhei isso'."""
    scan = models.OneToOneField(
        Scan, on_delete=models.CASCADE, related_name="review",
    )
    reviewed_by = models.ForeignKey(
        "auth.User", on_delete=models.SET_NULL, null=True,
        related_name="scan_reviews",
    )
    note = models.TextField(blank=True)
    reviewed_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"review of scan#{self.scan_id}"


class ScanAsset(models.Model):
    scan = models.ForeignKey(
        Scan, on_delete=models.CASCADE, related_name="scan_assets",
    )
    asset = models.ForeignKey(
        "assets.Asset", on_delete=models.CASCADE, related_name="scan_links",
    )
    is_new = models.BooleanField(default=False)
    seen_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["scan", "asset"], name="uniq_scan_asset",
            )
        ]
        indexes = [
            models.Index(fields=["scan", "is_new"]),
        ]


    # Snapshot no fim do scan (para diff)
    snap_ip = models.GenericIPAddressField(null=True, blank=True)
    snap_is_alive = models.BooleanField(default=False)

class ScanEndpoint(models.Model):
    scan = models.ForeignKey(
        Scan, on_delete=models.CASCADE, related_name="scan_endpoints",
    )
    endpoint = models.ForeignKey(
        "assets.Endpoint", on_delete=models.CASCADE,
        related_name="scan_links",
    )
    is_new = models.BooleanField(default=False)
    seen_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["scan", "endpoint"], name="uniq_scan_endpoint",
            )
        ]
        indexes = [
            models.Index(fields=["scan", "is_new"]),
        ]


    # Snapshot no fim do scan
    snap_status_code = models.IntegerField(null=True, blank=True)
    snap_content_type = models.CharField(max_length=255, blank=True)
    snap_kind = models.CharField(max_length=20, blank=True)

class ScanParameter(models.Model):
    scan = models.ForeignKey(
        Scan, on_delete=models.CASCADE, related_name="scan_parameters",
    )
    parameter = models.ForeignKey(
        "assets.Parameter", on_delete=models.CASCADE,
        related_name="scan_links",
    )
    is_new = models.BooleanField(default=False)
    seen_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["scan", "parameter"], name="uniq_scan_parameter",
            )
        ]
        indexes = [
            models.Index(fields=["scan", "is_new"]),
        ]
