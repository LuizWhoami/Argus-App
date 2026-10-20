"""Acoes de curadoria e ciclo de vida do scan."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST

from .models import Scan, ScanReview


def _own_scan(user, pk):
    return get_object_or_404(Scan, pk=pk, program__owner=user)


@login_required
@require_POST
def toggle_review(request, pk):
    """Marca ou desmarca 'revisado'. So pode em scans terminais."""
    scan = _own_scan(request.user, pk)

    if not scan.is_terminal():
        messages.warning(
            request,
            "So da para revisar scans finalizados (completed/failed/cancelled).",
        )
        return redirect("scans:detail", pk=scan.pk)

    existing = getattr(scan, "review", None)
    if existing:
        existing.delete()
        messages.info(request, "Revisao removida.")
    else:
        ScanReview.objects.create(
            scan=scan,
            reviewed_by=request.user,
            note=(request.POST.get("note") or "").strip()[:2000],
        )
        messages.success(request, "Scan marcado como revisado.")

    return redirect("scans:detail", pk=scan.pk)


@login_required
@require_POST
def delete_scan(request, pk):
    """Exclui um scan. Exige confirmacao textual para evitar acidente."""
    scan = _own_scan(request.user, pk)

    confirm = (request.POST.get("confirm") or "").strip()
    if confirm != f"delete {scan.pk}":
        messages.error(
            request,
            f"Confirmacao invalida. Digite: delete {scan.pk}",
        )
        return redirect("scans:detail", pk=scan.pk)

    target = scan.target
    scan.delete()
    messages.success(request, f"Scan de '{target}' excluido.")
    return redirect("scans:list")
