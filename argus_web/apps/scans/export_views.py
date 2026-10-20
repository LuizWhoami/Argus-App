"""Endpoints de export de um scan."""
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404

from .exporters import to_csv, to_json, to_markdown
from .models import Scan


def _get(request, pk):
    return get_object_or_404(Scan, pk=pk, program__owner=request.user)


def _filename(scan, ext):
    safe = scan.target.replace("/", "_").replace(":", "_")
    return f"argus-scan-{scan.pk}-{safe}.{ext}"


@login_required
def export_markdown(request, pk):
    scan = _get(request, pk)
    body = to_markdown(scan)
    r = HttpResponse(body, content_type="text/markdown; charset=utf-8")
    r["Content-Disposition"] = f'attachment; filename="{_filename(scan, "md")}"'
    return r


@login_required
def export_csv(request, pk):
    scan = _get(request, pk)
    body = to_csv(scan)
    r = HttpResponse(body, content_type="text/csv; charset=utf-8")
    r["Content-Disposition"] = f'attachment; filename="{_filename(scan, "csv")}"'
    return r


@login_required
def export_json(request, pk):
    scan = _get(request, pk)
    body = to_json(scan)
    r = HttpResponse(body, content_type="application/json; charset=utf-8")
    r["Content-Disposition"] = f'attachment; filename="{_filename(scan, "json")}"'
    return r
