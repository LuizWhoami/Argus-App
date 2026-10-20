"""Geradores de relatorio por scan. Sem dependencia de Django templates."""
import csv
import io
import json
from typing import Iterable

from apps.assets.models import Asset, Endpoint, HTTPProbe, Parameter


def _collect(scan):
    """Pega tudo o que pertence a este scan."""
    linked_assets = list(
        Asset.objects.filter(scan_links__scan=scan,
                             program=scan.program).order_by("hostname")
    )
    if not linked_assets:
        linked_assets = list(
            Asset.objects.filter(program=scan.program).order_by("hostname")
        )

    endpoints = list(
        Endpoint.objects.filter(asset__in=linked_assets)
        .select_related("asset").order_by("url")
    )
    params = list(
        Parameter.objects.filter(endpoint__in=endpoints)
        .select_related("endpoint").order_by("location", "name")
    )
    probes = list(
        HTTPProbe.objects.filter(asset__in=linked_assets)
        .select_related("asset").order_by("-status_code", "url")
    )
    return linked_assets, endpoints, params, probes


def to_json(scan) -> str:
    assets, endpoints, params, probes = _collect(scan)
    data = {
        "scan": {
            "id": scan.pk,
            "target": scan.target,
            "program": scan.program.name,
            "status": scan.status,
            "created_at": scan.created_at.isoformat() if scan.created_at else None,
            "started_at": scan.started_at.isoformat() if scan.started_at else None,
            "finished_at": scan.finished_at.isoformat() if scan.finished_at else None,
            "error": scan.error_message or None,
        },
        "summary": {
            "assets": len(assets),
            "endpoints": len(endpoints),
            "apis": len([e for e in endpoints if e.kind]),
            "params": len(params),
            "probes": len(probes),
        },
        "assets": [
            {
                "hostname": a.hostname, "ip": a.ip, "is_alive": a.is_alive,
                "verification": a.verification, "note": a.verification_note,
            } for a in assets
        ],
        "endpoints": [
            {
                "url": e.url, "method": e.method, "status_code": e.status_code,
                "kind": e.kind or None, "source": e.source,
                "hostname": e.asset.hostname,
                "verification": e.verification, "note": e.verification_note,
            } for e in endpoints
        ],
        "parameters": [
            {
                "name": p.name, "location": p.location,
                "endpoint_url": p.endpoint.url,
                "verification": p.verification, "note": p.verification_note,
            } for p in params
        ],
    }
    return json.dumps(data, indent=2, ensure_ascii=False)


def to_csv(scan) -> str:
    assets, endpoints, params, probes = _collect(scan)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["type", "hostname", "url", "method", "status_code",
                "kind", "source", "param_name", "param_location",
                "verification", "note"])

    for a in assets:
        w.writerow(["asset", a.hostname, "", "", "", "", "", "", "",
                    a.verification, a.verification_note])

    for e in endpoints:
        w.writerow(["endpoint", e.asset.hostname, e.url, e.method,
                    e.status_code or "", e.kind or "", e.source, "", "",
                    e.verification, e.verification_note])

    for p in params:
        w.writerow(["parameter", p.endpoint.asset.hostname,
                    p.endpoint.url, p.endpoint.method, "",
                    "", "", p.name, p.location,
                    p.verification, p.verification_note])

    for pr in probes:
        w.writerow(["http_probe", pr.asset.hostname, pr.url, "",
                    pr.status_code or "", "", "", "", "",
                    pr.verification, pr.verification_note])

    return buf.getvalue()


def to_markdown(scan) -> str:
    assets, endpoints, params, probes = _collect(scan)
    apis = [e for e in endpoints if e.kind]
    verified_assets = [a for a in assets if a.verification == "verified"]
    interesting = [x for x in list(assets) + list(endpoints) + list(params)
                   if x.verification == "interesting"]

    lines = []
    lines.append(f"# Scan #{scan.pk} — `{scan.target}`")
    lines.append("")
    lines.append(f"- **Programa:** {scan.program.name}")
    lines.append(f"- **Status:** {scan.status}")
    lines.append(f"- **Criado em:** "
                 f"{scan.created_at.strftime('%Y-%m-%d %H:%M:%S')}"
                 if scan.created_at else "")
    if scan.started_at:
        lines.append(f"- **Iniciado em:** "
                     f"{scan.started_at.strftime('%Y-%m-%d %H:%M:%S')}")
    if scan.finished_at:
        lines.append(f"- **Finalizado em:** "
                     f"{scan.finished_at.strftime('%Y-%m-%d %H:%M:%S')}")
    if scan.error_message:
        lines.append(f"- **Erro:** {scan.error_message}")
    lines.append("")

    lines.append("## Sumario")
    lines.append("")
    lines.append(f"| Metrica | Valor |")
    lines.append(f"|---|---|")
    lines.append(f"| Assets | {len(assets)} |")
    lines.append(f"| Endpoints | {len(endpoints)} |")
    lines.append(f"| API endpoints | {len(apis)} |")
    lines.append(f"| Parametros | {len(params)} |")
    lines.append(f"| HTTP probes | {len(probes)} |")
    lines.append(f"| Verificados | {len(verified_assets)} |")
    lines.append(f"| Interessantes | {len(interesting)} |")
    lines.append("")

    if assets:
        lines.append("## Assets")
        lines.append("")
        lines.append("| Hostname | IP | Alive | Verificacao | Nota |")
        lines.append("|---|---|---|---|---|")
        for a in assets:
            lines.append(f"| `{a.hostname}` | {a.ip or '—'} | "
                         f"{'sim' if a.is_alive else '—'} | "
                         f"{a.verification} | {a.verification_note or '—'} |")
        lines.append("")

    if apis:
        lines.append("## API endpoints")
        lines.append("")
        lines.append("| URL | Tipo | Status | Source | Verificacao |")
        lines.append("|---|---|---|---|---|")
        for e in apis:
            lines.append(f"| `{e.url}` | {e.kind} | {e.status_code or '—'} | "
                         f"{e.source} | {e.verification} |")
        lines.append("")

    other_eps = [e for e in endpoints if not e.kind]
    if other_eps:
        lines.append("## Outros endpoints")
        lines.append("")
        lines.append("| URL | Method | Status | Source | Verificacao |")
        lines.append("|---|---|---|---|---|")
        for e in other_eps[:200]:
            lines.append(f"| `{e.url}` | {e.method} | {e.status_code or '—'} | "
                         f"{e.source} | {e.verification} |")
        if len(other_eps) > 200:
            lines.append(f"")
            lines.append(f"*(+{len(other_eps) - 200} endpoints omitidos)*")
        lines.append("")

    if params:
        lines.append("## Parametros")
        lines.append("")
        lines.append("| Nome | Local | Endpoint | Verificacao |")
        lines.append("|---|---|---|---|")
        for p in params[:300]:
            lines.append(f"| `{p.name}` | {p.location} | "
                         f"`{p.endpoint.url}` | {p.verification} |")
        if len(params) > 300:
            lines.append("")
            lines.append(f"*(+{len(params) - 300} parametros omitidos)*")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("*Gerado por Argus — Autonomous Security Research Platform*")
    lines.append("")
    lines.append("*Uso exclusivo em programas de Bug Bounty e ativos "
                 "com autorizacao escrita.*")

    return "\n".join(lines)
