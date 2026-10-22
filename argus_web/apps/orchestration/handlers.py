"""Consome eventos do pipeline e grava nos models do Django."""
import logging
from urllib.parse import urlparse

from django.db import transaction
from django.utils import timezone

from apps.assets.models import (
    Asset, DNSRecord, Endpoint, HTTPProbe, Parameter,
)
from apps.findings.models import Finding
from apps.scans.models import (
    Scan, ScanAsset, ScanEndpoint, ScanParameter,
    ScanEvent, ScanStage,
)

log = logging.getLogger(__name__)

STAGE_ORDER = {
    "scope": 1, "subdomains": 2, "dns": 3, "http": 4,
    "directories": 5, "crawl": 6, "api": 7, "vulns": 8, "params": 9,
}


def _host_of(url: str) -> str:
    try:
        return urlparse(url).hostname or ""
    except Exception:
        return ""


def _link_asset(scan, asset, is_new=False):
    ScanAsset.objects.get_or_create(
        scan=scan, asset=asset, defaults={"is_new": is_new},
    )


def _link_endpoint(scan, endpoint, is_new=False):
    ScanEndpoint.objects.get_or_create(
        scan=scan, endpoint=endpoint, defaults={"is_new": is_new},
    )


def _link_parameter(scan, parameter, is_new=False):
    ScanParameter.objects.get_or_create(
        scan=scan, parameter=parameter, defaults={"is_new": is_new},
    )


@transaction.atomic
def handle_event(scan: Scan, event: dict) -> None:
    kind = event.get("event")

    if kind == "scan.started":
        ScanEvent.objects.create(scan=scan, level="info",
                                 message=f"scan iniciado em {event['target']}")

    elif kind == "stage.started":
        ScanStage.objects.update_or_create(
            scan=scan, name=event["stage"],
            defaults={
                "order": event.get("order",
                                   STAGE_ORDER.get(event["stage"], 99)),
                "status": ScanStage.STATUS_RUNNING,
                "started_at": timezone.now(),
            },
        )

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
        asset, created = Asset.objects.get_or_create(
            program=scan.program,
            hostname=event["hostname"],
            defaults={"ip": event.get("ip")},
        )
        if event.get("ip") and not asset.ip:
            asset.ip = event["ip"]
            asset.save(update_fields=["ip"])
        _link_asset(scan, asset, is_new=created)

    elif kind == "dns.record":
        asset, created = Asset.objects.get_or_create(
            program=scan.program, hostname=event["hostname"],
        )
        _link_asset(scan, asset, is_new=created)
        DNSRecord.objects.get_or_create(
            asset=asset,
            record_type=event["record_type"],
            value=event["value"],
        )

    elif kind == "http.probe":
        asset, a_created = Asset.objects.get_or_create(
            program=scan.program, hostname=event["hostname"],
        )
        _link_asset(scan, asset, is_new=a_created)
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


    elif kind == "directory.found":
        asset, a_created = Asset.objects.get_or_create(
            program=scan.program, hostname=event["hostname"],
        )
        _link_asset(scan, asset, is_new=a_created)
        source = event.get("source") or Endpoint.SOURCE_DIRSEARCH
        endpoint, e_created = Endpoint.objects.update_or_create(
            asset=asset, url=event["url"], method="GET",
            defaults={
                "status_code": event.get("status_code"),
                "source": source,
                "content_type": (event.get("content_type") or "")[:255],
                "is_directory": True,
                "response_size": event.get("content_length"),
            },
        )
        _link_endpoint(scan, endpoint, is_new=e_created)

    elif kind == "endpoint.found":
        asset, a_created = Asset.objects.get_or_create(
            program=scan.program, hostname=event["hostname"],
        )
        _link_asset(scan, asset, is_new=a_created)
        endpoint, e_created = Endpoint.objects.get_or_create(
            asset=asset, url=event["url"],
            method=event.get("method", "GET"),
            defaults={
                "status_code": event.get("status_code"),
                "content_type": (event.get("content_type") or "")[:255],
                "source": event.get("source", Endpoint.SOURCE_KATANA),
            },
        )
        _link_endpoint(scan, endpoint, is_new=e_created)

    elif kind == "api.found":
        asset, a_created = Asset.objects.get_or_create(
            program=scan.program, hostname=event["hostname"],
        )
        _link_asset(scan, asset, is_new=a_created)
        endpoint, e_created = Endpoint.objects.update_or_create(
            asset=asset, url=event["url"], method="GET",
            defaults={
                "kind": event["kind"],
                "source": event.get("source", Endpoint.SOURCE_WORDLIST),
            },
        )
        _link_endpoint(scan, endpoint, is_new=e_created)

    elif kind == "param.found":
        ep = Endpoint.objects.filter(
            asset__program=scan.program,
            url=event["endpoint_url"],
        ).first()
        if ep:
            param, p_created = Parameter.objects.get_or_create(
                endpoint=ep, name=event["name"],
                location=event["location"],
            )
            _link_parameter(scan, param, is_new=p_created)


    elif kind == "finding.found":
        asset = Asset.objects.filter(
            program=scan.program, hostname=event["hostname"],
        ).first()
        if not asset:
            return  # asset desconhecido — ignora

        endpoint = None
        if event.get("url"):
            endpoint = Endpoint.objects.filter(
                asset=asset, url=event["url"],
            ).first()

        Finding.objects.update_or_create(
            program=scan.program,
            asset=asset,
            template_id=event["template_id"],
            url=event.get("url", ""),
            defaults={
                "endpoint": endpoint,
                "title": (event.get("title") or "")[:255],
                "severity": (event.get("severity") or "info").lower(),
                "description": (event.get("description") or "")[:5000],
                "tags": (event.get("tags") or "")[:500],
                "cve": (event.get("cve") or "")[:500],
                "cwe": (event.get("cwe") or "")[:500],
                "reference": (event.get("reference") or "")[:1000],
                "curl_command": (event.get("curl_command") or "")[:5000],
                "matcher": (event.get("matcher") or "")[:200],
                "extracted": (event.get("extracted") or "")[:500],
            },
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
