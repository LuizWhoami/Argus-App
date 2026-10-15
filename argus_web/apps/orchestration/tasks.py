"""Task Celery que executa um Scan.

Regra: nao importa adapters nem subprocess. So chama iter_scan_events
do core e delega os eventos ao handler.
"""
import logging

from celery import shared_task
from django.db import connection

from argus_agent.pipeline_events import iter_scan_events
from argus_agent.scope import Scope

from apps.scans.models import Scan
from .handlers import handle_event

log = logging.getLogger(__name__)


@shared_task(name="orchestration.execute_scan")
def execute_scan(scan_id: int) -> dict:
    try:
        scan = Scan.objects.get(pk=scan_id)
    except Scan.DoesNotExist:
        return {"error": "scan inexistente"}

    if scan.is_terminal():
        return {"skipped": True, "reason": f"status={scan.status}"}

    try:
        scan.mark_running()
    except ValueError as e:
        return {"skipped": True, "reason": str(e)}

    scope = Scope(
        allowed=scan.program.allowed_patterns(),
        excluded=scan.program.excluded_patterns(),
    )

    try:
        for event in iter_scan_events(
            target=scan.target,
            scope=scope,
            max_rps=scan.program.max_rps,
            api_scan=scan.api_scan,
            crawl=scan.crawl,
            crawl_depth=scan.crawl_depth,
        ):
            # cancelamento cooperativo
            current = Scan.objects.filter(pk=scan_id).values("status").first()
            if not current or current["status"] == Scan.STATUS_CANCELLED:
                scan.refresh_from_db()
                return {"cancelled": True}

            try:
                handle_event(scan, event)
            except Exception as he:
                log.exception("handler falhou em %s", event.get("event"))
                # nao aborta o scan por erro de um evento individual

        scan.refresh_from_db()
        if scan.status == Scan.STATUS_RUNNING:
            scan.mark_completed()
        return {"ok": True, "scan_id": scan_id}

    except Exception as e:
        log.exception("scan %s falhou", scan_id)
        scan.refresh_from_db()
        if not scan.is_terminal():
            scan.mark_failed(str(e))
        return {"error": str(e)}

    finally:
        connection.close()
