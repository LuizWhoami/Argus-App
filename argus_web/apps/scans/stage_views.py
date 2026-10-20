"""Visualizacao de resultados por etapa do scan.

Estrategia de resolucao (em ordem):
  1. Se ha links explicitos (ScanAsset/ScanEndpoint/ScanParameter), usa.
  2. Se nao ha links, mostra TODOS os achados do programa do scan.
     (pode incluir achados de outros scans do mesmo programa)
"""
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, render

from apps.assets.models import Asset, Endpoint, HTTPProbe, Parameter

from .models import Scan

STAGE_LABELS = {
    "scope": "Validacao de escopo",
    "subdomains": "Subdominios",
    "dns": "Resolucao DNS",
    "http": "HTTP probing",
    "crawl": "Crawling",
    "api": "API discovery",
    "params": "Parametros",
}


@login_required
def stage_detail(request, pk, name):
    if name not in STAGE_LABELS:
        raise Http404("etapa desconhecida")

    scan = get_object_or_404(Scan, pk=pk, program__owner=request.user)
    program = scan.program

    # --- Tenta usar links explicitos do scan ---
    linked_assets = list(
        Asset.objects.filter(scan_links__scan=scan,
                             program=program).values_list("pk", flat=True)
    )
    linked_endpoints = list(
        Endpoint.objects.filter(scan_links__scan=scan,
                                asset__program=program)
        .values_list("pk", flat=True)
    )
    linked_params = list(
        Parameter.objects.filter(scan_links__scan=scan,
                                 endpoint__asset__program=program)
        .values_list("pk", flat=True)
    )

    has_links = bool(linked_assets or linked_endpoints or linked_params)

    if has_links:
        # Escopo: só o que este scan trouxe
        assets_base = Asset.objects.filter(pk__in=linked_assets)
        endpoints_base = Endpoint.objects.filter(pk__in=linked_endpoints)
        params_base = Parameter.objects.filter(pk__in=linked_params)
        probes_base = HTTPProbe.objects.filter(asset__pk__in=linked_assets)
        source_label = "vinculado a este scan"
    else:
        # Fallback: tudo do programa
        assets_base = Asset.objects.filter(program=program)
        endpoints_base = Endpoint.objects.filter(asset__program=program)
        params_base = Parameter.objects.filter(
            endpoint__asset__program=program)
        probes_base = HTTPProbe.objects.filter(asset__program=program)
        source_label = "todos os achados do programa"

    # --- Aplica filtro por etapa ---
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

    elif name == "crawl":
        kind_of_rows = "endpoints"
        rows = list(endpoints_base
                    .filter(source=Endpoint.SOURCE_KATANA)
                    .select_related("asset")
                    .order_by("url"))

    elif name == "api":
        kind_of_rows = "endpoints"
        rows = list(endpoints_base.exclude(kind="")
                    .select_related("asset")
                    .order_by("kind", "url"))

    elif name == "params":
        kind_of_rows = "params"
        rows = list(params_base.select_related("endpoint",
                                                "endpoint__asset")
                    .order_by("location", "name"))

    stage_obj = scan.stages.filter(name=name).first()

    # Contagem total (antes do list(); pega do banco)
    total_count = len(rows)

    return render(request, "scans/stage_detail.html", {
        "scan": scan,
        "stage_name": name,
        "stage_label": STAGE_LABELS[name],
        "stage_obj": stage_obj,
        "kind_of_rows": kind_of_rows,
        "rows": rows,
        "total_count": total_count,
        "source_label": source_label,
        "has_links": has_links,
    })
