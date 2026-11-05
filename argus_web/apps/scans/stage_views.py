"""Visualizacao de resultados por etapa do scan."""
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from apps.assets.models import Asset, Endpoint, HTTPProbe, Parameter

from .models import Scan

STAGE_LABELS = {
    "scope": "Validacao de escopo",
    "subdomains": "Subdominios",
    "dns": "Resolucao DNS",
    "http": "HTTP probing",
    "directories": "Diretorios",
    "crawl": "Crawling",
    "api": "API discovery",
    "vulns": "Vulnerabilidades",
    "params": "Parametros",
}


@login_required
def stage_detail(request, pk, name):
    if name not in STAGE_LABELS:
        raise Http404("etapa desconhecida")

    scan = get_object_or_404(Scan, pk=pk, program__owner=request.user)
    program = scan.program

    # Bases: prioriza links explicitos, cai para tudo do programa
    linked_assets = list(
        Asset.objects.filter(scan_links__scan=scan, program=program)
        .values_list("pk", flat=True)
    )
    linked_endpoints = list(
        Endpoint.objects.filter(
            scan_links__scan=scan, asset__program=program
        ).values_list("pk", flat=True)
    )
    linked_params = list(
        Parameter.objects.filter(
            scan_links__scan=scan, endpoint__asset__program=program
        ).values_list("pk", flat=True)
    )

    has_links = bool(linked_assets or linked_endpoints or linked_params)

    if has_links:
        assets_base = Asset.objects.filter(pk__in=linked_assets)
        endpoints_base = Endpoint.objects.filter(pk__in=linked_endpoints)
        params_base = Parameter.objects.filter(pk__in=linked_params)
        probes_base = HTTPProbe.objects.filter(asset__pk__in=linked_assets)
        source_label = "vinculado a este scan"
    else:
        assets_base = Asset.objects.filter(program=program)
        endpoints_base = Endpoint.objects.filter(asset__program=program)
        params_base = Parameter.objects.filter(
            endpoint__asset__program=program)
        probes_base = HTTPProbe.objects.filter(asset__program=program)
        source_label = "todos os achados do programa"

    rows = []
    kind_of_rows = "assets"

    if name == "scope":
        kind_of_rows = "events"
        rows = list(scan.events.filter(stage="scope")[:200])

    elif name == "subdomains":
        kind_of_rows = "assets"
        rows = list(assets_base.order_by("hostname"))

    elif name == "dns":
        kind_of_rows = "assets"
        rows = list(assets_base.exclude(ip__isnull=True)
                    .exclude(ip="")
                    .order_by("hostname"))

    elif name == "http":
        kind_of_rows = "probes"
        rows = list(probes_base.select_related("asset")
                    .order_by("-status_code", "url"))

    elif name == "directories":
        kind_of_rows = "directories"
        rows = list(endpoints_base
                    .filter(is_directory=True)
                    .select_related("asset")
                    .order_by("url"))

    elif name == "crawl":
        kind_of_rows = "endpoints"
        rows = list(endpoints_base
                    .filter(source=Endpoint.SOURCE_KATANA,
                            is_directory=False)
                    .select_related("asset")
                    .order_by("url"))

    elif name == "api":
        kind_of_rows = "endpoints"
        rows = list(endpoints_base.exclude(kind="")
                    .select_related("asset")
                    .order_by("kind", "url"))

    elif name == "vulns":
        try:
            from apps.findings.models import Finding
            kind_of_rows = "findings"
            rows = list(Finding.objects.filter(program=program)
                        .select_related("asset")
                        .order_by("-severity", "title"))
        except Exception:
            kind_of_rows = "empty"
            rows = []

    elif name == "params":
        kind_of_rows = "params"
        rows = list(params_base
                    .select_related("endpoint", "endpoint__asset")
                    .order_by("location", "name"))

    stage_obj = scan.stages.filter(name=name).first()

    return render(request, "scans/stage_detail.html", {
        "scan": scan,
        "stage_name": name,
        "stage_label": STAGE_LABELS[name],
        "stage_obj": stage_obj,
        "kind_of_rows": kind_of_rows,
        "rows": rows,
        "total_count": len(rows),
        "source_label": source_label,
        "has_links": has_links,
    })
