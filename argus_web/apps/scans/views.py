from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

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

        scan = Scan.objects.create(
            program=program,
            target=target,
            requested_by=request.user,
            api_scan=("api_scan" in request.POST),
            crawl=("crawl" in request.POST),
            crawl_depth=int(request.POST.get("crawl_depth") or 3),
        )
        enqueue_scan(scan)
        return redirect("scans:detail", pk=scan.pk)

    return render(request, "scans/new.html", {"program": program})


@login_required
def detail_scan(request, pk):
    scan = get_object_or_404(
        Scan, pk=pk, program__owner=request.user)
    stages = scan.stages.all()
    events = scan.events.all()[:200]
    return render(request, "scans/detail.html", {
        "scan": scan, "stages": stages, "events": events,
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
