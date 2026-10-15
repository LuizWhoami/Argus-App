"""Consome eventos do pipeline_events e grava nos models do Django.

Regra: este modulo NAO fala com ferramentas externas. Ele so escreve
no banco. Toda decisao de escopo ja foi tomada em iter_scan_events.
"""
import logging
from urllib.parse import urlparse

from django.db import transaction
from django.utils import timezone

from apps.assets.models import (
    Asset, DNSRecord, Endpoint, HTTPProbe, Parameter,
)
from apps.scans.models import Scan, ScanEvent, ScanStage

log = logging.getLogger(__name__)

STAGE_ORDER = {
    "scope": 1, "subdomains": 2, "dns": 3, "http": 4,
    "crawl": 5, "api": 6, "params": 7,
}


def _host_of(url: str) -> str:
    try:
        return urlparse(url).hostname or ""
    except Exception:
        return ""


def _get_or_create_asset(scan: Scan, hostname: str, ip=None) -> Asset:
    asset, created = Asset.objects.get_or_create(
        program=scan.program,
        hostname=hostname,
        defaults={"ip": ip},
    )
    if ip and not asset.ip:
        asset.ip = ip
        asset.save(update_fields=["ip"])
    return asset


@transaction.atomic
def handle_event(scan: Scan, event: dict) -> None:
    """Aplica um evento ao banco. Idempotente por constraint."""
    kind = event.get("event")

    if kind == "scan.started":
        ScanEvent.objects.create(scan=scan, level="info",
                                 message=f"scan iniciado em {event['target']}")

    elif kind == "stage.started":
        ScanStage.objects.update_or_create(
            scan=scan, name=event["stage"],
            defaults={
                "order": event.get("order", STAGE_ORDER.get(event["stage"], 99)),
                "status": ScanStage.STATUS_RUNNING,
                "started_at": timezone.now(),
            },
        )
        ScanEvent.objects.create(scan=scan, level="info",
                                 stage=event["stage"],
                                 message=f"etapa {event['stage']} iniciada")

    elif kind == "stage.completed":
        ScanStage.objects.update_or_create(
            scan=scan, name=event["stage"],
            defaults={
                "order": STAGE_ORDER.get(event["stage"], 99),
                "status": ScanStage.STATUS_COMPLETED,
                "result_count": event.get("count", 0),
                "finished_at": timezone.now(),
            },
        )
        ScanEvent.objects.create(scan=scan, level="info",
                                 stage=event["stage"],
                                 message=f"etapa {event['stage']} concluida "
                                         f"({event.get('count', 0)} itens)")

    elif kind == "stage.failed":
        ScanStage.objects.update_or_create(
            scan=scan, name=event["stage"],
            defaults={
                "order": STAGE_ORDER.get(event["stage"], 99),
                "status": ScanStage.STATUS_FAILED,
                "message": str(event.get("error", ""))[:512],
                "finished_at": timezone.now(),
            },
        )
        ScanEvent.objects.create(scan=scan, level="error",
                                 stage=event["stage"],
                                 message=str(event.get("error", ""))[:1000])

    elif kind == "asset.found":
        _get_or_create_asset(scan, event["hostname"], event.get("ip"))

    elif kind == "dns.record":
        asset = _get_or_create_asset(scan, event["hostname"])
        DNSRecord.objects.get_or_create(
            asset=asset,
            record_type=event["record_type"],
            value=event["value"],
        )

    elif kind == "http.probe":
        asset = _get_or_create_asset(scan, event["hostname"])
        HTTPProbe.objects.update_or_create(
            asset=asset, url=event["url"],
            defaults={
                "status_code": event.get("status_code"),
                "content_type": (event.get("content_type") or "")[:255],
                "title": (event.get("title") or "")[:512],
                "webserver": (event.get("webserver") or "")[:255],
                "tech": (event.get("tech") or "")[:2000],
                "location": (event.get("location") or "")[:2048],
            },
        )
        asset.is_alive = True
        asset.save(update_fields=["is_alive"])

    elif kind == "endpoint.found":
        asset = _get_or_create_asset(scan, event["hostname"])
        Endpoint.objects.get_or_create(
            asset=asset, url=event["url"],
            method=event.get("method", "GET"),
            defaults={
                "status_code": event.get("status_code"),
                "content_type": (event.get("content_type") or "")[:255],
                "source": event.get("source", Endpoint.SOURCE_KATANA),
            },
        )

    elif kind == "api.found":
        asset = _get_or_create_asset(scan, event["hostname"])
        Endpoint.objects.update_or_create(
            asset=asset, url=event["url"], method="GET",
            defaults={
                "kind": event["kind"],
                "source": event.get("source", Endpoint.SOURCE_WORDLIST),
            },
        )

    elif kind == "param.found":
        ep = (Endpoint.objects
              .filter(asset__program=scan.program, url=event["endpoint_url"])
              .first())
        if ep:
            Parameter.objects.get_or_create(
                endpoint=ep,
                name=event["name"],
                location=event["location"],
            )

    elif kind == "scan.completed":
        s = event.get("summary", {})
        scan.assets_found = s.get("subdomains", scan.assets_found)
        scan.endpoints_found = s.get("crawled", scan.endpoints_found)
        scan.api_endpoints_found = s.get("api", scan.api_endpoints_found)
        scan.parameters_found = s.get("params", scan.parameters_found)
        scan.save(update_fields=[
            "assets_found", "endpoints_found",
            "api_endpoints_found", "parameters_found",
        ])
        ScanEvent.objects.create(scan=scan, level="info",
                                 message="scan concluido")

    elif kind == "scan.failed":
        ScanEvent.objects.create(scan=scan, level="error",
                                 message=str(event.get("error", ""))[:1000])

    else:
        log.debug("evento desconhecido: %s", kind)
