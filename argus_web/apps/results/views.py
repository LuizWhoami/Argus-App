from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.assets.models import Asset, Endpoint, HTTPProbe, Parameter
from apps.programs.models import Program
from apps.scans.models import Scan


def _programs_of(user):
    return Program.objects.filter(owner=user)


def _filter_by_program(qs, request, field="program"):
    slug = request.GET.get("program", "").strip()
    if not slug:
        return qs, None
    prog = get_object_or_404(Program, slug=slug, owner=request.user)
    return qs.filter(**{field: prog}), prog


def _filter_by_verification(qs, request):
    v = request.GET.get("verification", "").strip()
    if v:
        qs = qs.filter(verification=v)
    return qs


def _search(qs, request, fields):
    q = request.GET.get("q", "").strip()
    if not q:
        return qs
    cond = Q()
    for f in fields:
        cond |= Q(**{f"{f}__icontains": q})
    return qs.filter(cond)


@login_required
def dashboard(request):
    progs = _programs_of(request.user)
    stats = {
        "programs": progs.count(),
        "scans": Scan.objects.filter(program__owner=request.user).count(),
        "assets": Asset.objects.filter(program__owner=request.user).count(),
        "endpoints": Endpoint.objects.filter(
            asset__program__owner=request.user).count(),
        "api_endpoints": Endpoint.objects.filter(
            asset__program__owner=request.user).exclude(kind="").count(),
        "params": Parameter.objects.filter(
            endpoint__asset__program__owner=request.user).count(),
    }
    verified_assets = Asset.objects.filter(
        program__owner=request.user,
        verification=Asset.VERIF_VERIFIED,
    ).count()

    recent_scans = (Scan.objects
                    .filter(program__owner=request.user)
                    .select_related("program")
                    .order_by("-created_at")[:8])

    recent_assets = (Asset.objects
                     .filter(program__owner=request.user)
                     .select_related("program")
                     .order_by("-last_seen")[:10])

    return render(request, "results/dashboard.html", {
        "stats": stats,
        "verified_assets": verified_assets,
        "recent_scans": recent_scans,
        "recent_assets": recent_assets,
        "programs": progs,
    })


@login_required
def list_assets(request):
    qs = (Asset.objects
          .filter(program__owner=request.user)
          .select_related("program")
          .order_by("-last_seen"))
    qs, prog = _filter_by_program(qs, request)
    qs = _filter_by_verification(qs, request)
    qs = _search(qs, request, ["hostname", "ip"])
    return render(request, "results/list.html", {
        "kind": "assets", "title": "Assets",
        "rows": qs[:500], "total": qs.count(),
        "programs": _programs_of(request.user), "current_program": prog,
        "verification_choices": Asset.VERIF_CHOICES,
    })


@login_required
def list_endpoints(request):
    qs = (Endpoint.objects
          .filter(asset__program__owner=request.user)
          .select_related("asset", "asset__program")
          .order_by("-discovered_at"))
    qs, prog = _filter_by_program(qs, request, field="asset__program")
    qs = _filter_by_verification(qs, request)
    qs = _search(qs, request, ["url", "asset__hostname"])
    return render(request, "results/list.html", {
        "kind": "endpoints", "title": "Endpoints",
        "rows": qs[:500], "total": qs.count(),
        "programs": _programs_of(request.user), "current_program": prog,
        "verification_choices": Endpoint.VERIF_CHOICES,
    })


@login_required
def list_apis(request):
    qs = (Endpoint.objects
          .filter(asset__program__owner=request.user)
          .exclude(kind="")
          .select_related("asset", "asset__program")
          .order_by("-discovered_at"))
    qs, prog = _filter_by_program(qs, request, field="asset__program")
    qs = _filter_by_verification(qs, request)
    kind_filter = request.GET.get("kind", "").strip()
    if kind_filter:
        qs = qs.filter(kind=kind_filter)
    qs = _search(qs, request, ["url", "asset__hostname"])
    return render(request, "results/list.html", {
        "kind": "apis", "title": "API endpoints",
        "rows": qs[:500], "total": qs.count(),
        "programs": _programs_of(request.user), "current_program": prog,
        "verification_choices": Endpoint.VERIF_CHOICES,
    })


@login_required
def list_params(request):
    qs = (Parameter.objects
          .filter(endpoint__asset__program__owner=request.user)
          .select_related("endpoint", "endpoint__asset")
          .order_by("-id"))
    qs, prog = _filter_by_program(qs, request, field="endpoint__asset__program")
    qs = _filter_by_verification(qs, request)
    loc = request.GET.get("loc", "").strip()
    if loc:
        qs = qs.filter(location=loc)
    qs = _search(qs, request, ["name", "endpoint__url"])
    return render(request, "results/list.html", {
        "kind": "params", "title": "Parametros",
        "rows": qs[:500], "total": qs.count(),
        "programs": _programs_of(request.user), "current_program": prog,
        "verification_choices": Parameter.VERIF_CHOICES,
    })


MODEL_MAP = {
    "assets": Asset,
    "endpoints": Endpoint,
    "apis": Endpoint,
    "params": Parameter,
}


def _program_of(obj):
    if isinstance(obj, Asset):
        return obj.program
    if isinstance(obj, Endpoint):
        return obj.asset.program
    if isinstance(obj, Parameter):
        return obj.endpoint.asset.program
    if isinstance(obj, HTTPProbe):
        return obj.asset.program
    return None


@login_required
@require_POST
def mark_verification(request, kind: str, pk: int):
    model = MODEL_MAP.get(kind)
    if not model:
        raise Http404

    obj = get_object_or_404(model, pk=pk)
    program = _program_of(obj)
    if program is None or program.owner_id != request.user.id:
        raise Http404

    new_status = request.POST.get("verification", "").strip()
    if new_status not in dict(model.VERIF_CHOICES):
        messages.error(request, "status invalido")
        return redirect(request.META.get("HTTP_REFERER", "results:dashboard"))

    obj.verification = new_status
    obj.verification_note = request.POST.get("note", "").strip()[:2000]
    obj.verified_by = request.user
    obj.verified_at = timezone.now()
    obj.save(update_fields=[
        "verification", "verification_note", "verified_by", "verified_at",
    ])

    messages.success(request, f"Marcado como '{new_status}'.")
    return redirect(request.META.get("HTTP_REFERER", "results:dashboard"))


@login_required
def export_json(request):
    kind = request.GET.get("kind", "assets")
    model = MODEL_MAP.get(kind)
    if not model:
        raise Http404

    if kind == "assets":
        qs = model.objects.filter(program__owner=request.user)
        qs, _ = _filter_by_program(qs, request)
    elif kind in ("endpoints", "apis"):
        qs = model.objects.filter(asset__program__owner=request.user)
        if kind == "apis":
            qs = qs.exclude(kind="")
        qs, _ = _filter_by_program(qs, request, field="asset__program")
    else:
        qs = model.objects.filter(
            endpoint__asset__program__owner=request.user)
        qs, _ = _filter_by_program(qs, request,
                                   field="endpoint__asset__program")

    qs = _filter_by_verification(qs, request)

    data = []
    for o in qs[:5000]:
        d = {
            "id": o.pk,
            "verification": o.verification,
            "verification_note": o.verification_note,
        }
        if isinstance(o, Asset):
            d.update(hostname=o.hostname, ip=o.ip, is_alive=o.is_alive)
        elif isinstance(o, Endpoint):
            d.update(url=o.url, method=o.method, kind=o.kind,
                     status_code=o.status_code, source=o.source,
                     hostname=o.asset.hostname)
        elif isinstance(o, Parameter):
            d.update(name=o.name, location=o.location,
                     endpoint_url=o.endpoint.url)
        data.append(d)

    return JsonResponse({"kind": kind, "count": len(data), "results": data})
