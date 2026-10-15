from django.db import models


class Asset(models.Model):
    """Hostname descoberto dentro de um programa."""
    program = models.ForeignKey(
        "programs.Program",
        on_delete=models.CASCADE,
        related_name="assets",
    )
    hostname = models.CharField(max_length=255, db_index=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    is_alive = models.BooleanField(default=False)
    first_seen = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("hostname",)
        constraints = [
            models.UniqueConstraint(
                fields=["program", "hostname"],
                name="uniq_asset_per_program",
            )
        ]
        indexes = [
            models.Index(fields=["program", "hostname"]),
        ]

    def __str__(self):
        return self.hostname


class DNSRecord(models.Model):
    asset = models.ForeignKey(
        Asset, on_delete=models.CASCADE, related_name="dns_records",
    )
    record_type = models.CharField(max_length=10)   # A, AAAA, CNAME, MX...
    value = models.CharField(max_length=512)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["asset", "record_type", "value"],
                name="uniq_dns_record",
            )
        ]

    def __str__(self):
        return f"{self.record_type} {self.value}"


class HTTPProbe(models.Model):
    asset = models.ForeignKey(
        Asset, on_delete=models.CASCADE, related_name="http_probes",
    )
    url = models.CharField(max_length=2048, db_index=True)
    status_code = models.IntegerField(null=True, blank=True)
    title = models.CharField(max_length=512, blank=True)
    content_type = models.CharField(max_length=255, blank=True)
    webserver = models.CharField(max_length=255, blank=True)
    tech = models.TextField(blank=True)     # CSV de tecnologias
    location = models.CharField(max_length=2048, blank=True)
    probed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["asset", "url"],
                name="uniq_http_probe",
            )
        ]
        indexes = [
            models.Index(fields=["asset", "status_code"]),
        ]

    def __str__(self):
        return f"{self.status_code} {self.url}"


class Endpoint(models.Model):
    """URL/rota descoberta via crawling ou path guessing."""
    SOURCE_KATANA = "katana"
    SOURCE_WORDLIST = "wordlist"
    SOURCE_SEED = "seed"
    SOURCE_CHOICES = [
        (SOURCE_KATANA, "katana"),
        (SOURCE_WORDLIST, "wordlist"),
        (SOURCE_SEED, "seed"),
    ]

    KIND_SWAGGER = "swagger"
    KIND_OPENAPI = "openapi"
    KIND_GRAPHQL = "graphql"
    KIND_REST = "rest"
    KIND_CHOICES = [
        (KIND_SWAGGER, "swagger"),
        (KIND_OPENAPI, "openapi"),
        (KIND_GRAPHQL, "graphql"),
        (KIND_REST, "rest"),
    ]

    asset = models.ForeignKey(
        Asset, on_delete=models.CASCADE, related_name="endpoints",
    )
    url = models.CharField(max_length=2048, db_index=True)
    method = models.CharField(max_length=10, default="GET")
    status_code = models.IntegerField(null=True, blank=True)
    content_type = models.CharField(max_length=255, blank=True)
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES,
                              default=SOURCE_SEED)
    kind = models.CharField(max_length=20, choices=KIND_CHOICES,
                            blank=True)
    discovered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("url",)
        constraints = [
            models.UniqueConstraint(
                fields=["asset", "url", "method"],
                name="uniq_endpoint",
            )
        ]
        indexes = [
            models.Index(fields=["asset", "kind"]),
        ]

    def __str__(self):
        return f"{self.method} {self.url}"


class Parameter(models.Model):
    LOC_QUERY = "query"
    LOC_FORM = "form"
    LOC_CHOICES = [
        (LOC_QUERY, "query"),
        (LOC_FORM, "form"),
    ]

    endpoint = models.ForeignKey(
        Endpoint, on_delete=models.CASCADE, related_name="parameters",
    )
    name = models.CharField(max_length=255)
    location = models.CharField(max_length=10, choices=LOC_CHOICES)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["endpoint", "name", "location"],
                name="uniq_parameter",
            )
        ]

    def __str__(self):
        return f"{self.location}:{self.name}"
