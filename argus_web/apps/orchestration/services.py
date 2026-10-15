"""Servicos publicos de orquestracao."""
import logging
import threading

from django.conf import settings

from apps.scans.models import Scan

log = logging.getLogger(__name__)


def enqueue_scan(scan: Scan) -> None:
    """Dispara o scan em background.

    - Se Celery estiver em modo eager (dev sem Redis), roda numa thread
      para nao bloquear a request.
    - Se houver broker (Redis), dispara normalmente via Celery.
    """
    from .tasks import execute_scan

    if getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False):
        t = threading.Thread(
            target=lambda: execute_scan.apply(args=(scan.id,)),
            daemon=True,
            name=f"argus-scan-{scan.id}",
        )
        t.start()
    else:
        execute_scan.delay(scan.id)


def cancel_scan(scan: Scan) -> bool:
    """Marca para cancelamento. O worker checa a flag entre eventos."""
    if scan.is_terminal():
        return False
    try:
        scan.mark_cancelled()
        return True
    except ValueError:
        return False
