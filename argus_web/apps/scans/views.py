from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.assets.models import Asset, Endpoint, Parameter
from apps.programs.models import Program
from apps.orchestration.services import cancel_scan, enqueue_scan

from .models import Scan


@login_required
def list_scans(request):
    scans = (Scan.objects
             .filter(program__owner=request.user)
             .select_related("program")
             .order_by("-created_at"))
    return render(request, "scans/list.html", {"scans": scans})


@login_required
def new_scan(request, slug):
    program = get_object_or_404(Program, slug=slug, owner=request.user)
    if request.method == "POST":
        target = (request.POST.get("target") or "").strip().lower()
        if not target:
            return HttpResponseBadRequest("target obrigatorio")

        # valida escopo na criacao
        from argus_agent.scope import Scope
        scope = Scope(program.allowed_patterns(), program.excluded_patterns())
        if not scope.is_allowed(target):
            messages.error(request, f"'{target}' fora do escopo do programa.")
            return redirect("scans:new", slug=program.slug)

        from apps.wordlists.models import Wordlist
        wl = None
        wl_id = request.POST.get("wordlist") or ""
        if wl_id:
            wl = Wordlist.objects.filter(
                pk=wl_id,
            ).filter(
                models.Q(is_builtin=True) | models.Q(owner=request.user)
            ).first()

        scan = Scan.objects.create(
            program=program,
            target=target,
            requested_by=request.user,
            api_scan=("api_scan" in request.POST),
            crawl=("crawl" in request.POST),
            crawl_depth=int(request.POST.get("crawl_depth") or 3),
            wordlist=wl,
        )
        enqueue_scan(scan)
        return redirect("scans:detail", pk=scan.pk)

    from django.db.models import Q
    from apps.wordlists.models import Wordlist
    wordlists = Wordlist.objects.filter(
        Q(is_builtin=True) | Q(owner=request.user),
        kind=Wordlist.KIND_API,
    ).order_by("-is_builtin", "name")

    return render(request, "scans/new.html", {
        "program": program, "wordlists": wordlists,
    })


@login_required
def detail_scan(request, pk):
    scan = get_object_or_404(
        Scan, pk=pk, program__owner=request.user)
    stages = scan.stages.all()
    events = scan.events.all()[:200]
    review = getattr(scan, "review", None)

    from django.utils import timezone as _tz

    has_links = (
        scan.scan_assets.exists()
        or scan.scan_endpoints.exists()
        or scan.scan_parameters.exists()
    )

    if has_links:
        assets = (Asset.objects
                  .filter(scan_links__scan=scan, program=scan.program)
                  .select_related("program")
                  .order_by("hostname"))
        endpoints = (Endpoint.objects
                     .filter(scan_links__scan=scan,
                             asset__program=scan.program)
                     .select_related("asset")
                     .order_by("url"))
        apis = (Endpoint.objects
                .filter(scan_links__scan=scan,
                        asset__program=scan.program)
                .exclude(kind="")
                .select_related("asset")
                .order_by("kind", "url"))
        params = (Parameter.objects
                  .filter(scan_links__scan=scan,
                          endpoint__asset__program=scan.program)
                  .select_related("endpoint")
                  .order_by("location", "name"))
    else:
        t0 = scan.started_at or scan.created_at
        t1 = scan.finished_at or _tz.now()
        assets = (Asset.objects
                  .filter(program=scan.program,
                          first_seen__gte=t0, first_seen__lte=t1)
                  .order_by("hostname"))
        endpoints = (Endpoint.objects
                     .filter(asset__program=scan.program,
                             discovered_at__gte=t0,
                             discovered_at__lte=t1)
                     .select_related("asset")
                     .order_by("url"))
        apis = (endpoints.exclude(kind="").order_by("kind", "url"))
        params = (Parameter.objects
                  .filter(endpoint__asset__program=scan.program,
                          endpoint__discovered_at__gte=t0,
                          endpoint__discovered_at__lte=t1)
                  .select_related("endpoint")
                  .order_by("location", "name"))

    return render(request, "scans/detail.html", {
        "scan": scan, "stages": stages, "events": events,
        "review": review,
        "assets": assets, "endpoints": endpoints,
        "apis": apis, "params": params,
    })


@login_required
def status_partial(request, pk):
    """Fragmento HTMX: atualiza status + stages + events."""
    try:
        scan = Scan.objects.get(pk=pk, program__owner=request.user)
    except Scan.DoesNotExist:
        raise Http404
    return render(request, "scans/_status.html", {
        "scan": scan,
        "stages": scan.stages.all(),
        "events": scan.events.all()[:50],
    })


@login_required
@require_POST
def cancel(request, pk):
    scan = get_object_or_404(Scan, pk=pk, program__owner=request.user)
    if cancel_scan(scan):
        messages.warning(request, "Scan cancelado.")
    else:
        messages.info(request, "Nada a cancelar.")
    return redirect("scans:detail", pk=scan.pk)
