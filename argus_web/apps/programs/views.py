from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.text import slugify

from argus_agent.scope import Scope

from .models import Program, ScopeEntry


def _unique_slug(name: str, owner) -> str:
    base = slugify(name)[:120] or "program"
    slug = base
    i = 1
    while Program.objects.filter(slug=slug).exists():
        i += 1
        slug = f"{base}-{i}"
    return slug


@login_required
def list_programs(request):
    programs = request.user.programs.all()
    return render(request, "programs/list.html", {"programs": programs})


@login_required
def create_program(request):
    if request.method == "POST":
        name = (request.POST.get("name") or "").strip()
        description = (request.POST.get("description") or "").strip()
        max_rps = int(request.POST.get("max_rps") or 5)

        if not name:
            return HttpResponseBadRequest("Nome obrigatorio")

        try:
            with transaction.atomic():
                program = Program.objects.create(
                    owner=request.user,
                    name=name,
                    slug=_unique_slug(name, request.user),
                    description=description,
                    max_rps=max(1, min(100, max_rps)),
                )
        except IntegrityError:
            messages.error(request, "Ja existe um programa com esse nome.")
            return redirect("programs:list")

        messages.success(request, f"Programa '{program.name}' criado.")
        return redirect("programs:detail", slug=program.slug)

    return render(request, "programs/form.html", {"program": None})


@login_required
def detail_program(request, slug):
    program = get_object_or_404(Program, slug=slug, owner=request.user)
    entries = program.scope_entries.all()

    # Preview da decisao do scope engine
    scope = Scope(
        allowed=program.allowed_patterns(),
        excluded=program.excluded_patterns(),
    )
    preview_host = request.GET.get("check", "").strip()
    preview_allowed = None
    if preview_host:
        preview_allowed = scope.is_allowed(preview_host)

    return render(request, "programs/detail.html", {
        "program": program,
        "entries": entries,
        "preview_host": preview_host,
        "preview_allowed": preview_allowed,
    })


@login_required
def edit_program(request, slug):
    program = get_object_or_404(Program, slug=slug, owner=request.user)

    if request.method == "POST":
        program.name = (request.POST.get("name") or program.name).strip()
        program.description = (request.POST.get("description")
                               or program.description).strip()
        try:
            program.max_rps = max(1, min(100, int(request.POST.get("max_rps")
                                                   or program.max_rps)))
        except ValueError:
            pass
        program.aggressive_scanning = "aggressive_scanning" in request.POST
        program.destructive_testing = "destructive_testing" in request.POST
        program.is_active = "is_active" in request.POST
        program.save()
        messages.success(request, "Programa atualizado.")
        return redirect("programs:detail", slug=program.slug)

    return render(request, "programs/form.html", {"program": program})


@login_required
def add_scope_entry(request, slug):
    program = get_object_or_404(Program, slug=slug, owner=request.user)
    if request.method != "POST":
        return HttpResponseBadRequest("POST obrigatorio")

    kind = request.POST.get("kind")
    pattern = (request.POST.get("pattern") or "").strip().lower()
    note = (request.POST.get("note") or "").strip()

    if kind not in (ScopeEntry.KIND_ALLOW, ScopeEntry.KIND_EXCLUDE):
        return HttpResponseBadRequest("kind invalido")
    if not pattern:
        return HttpResponseBadRequest("pattern obrigatorio")

    try:
        with transaction.atomic():
            ScopeEntry.objects.create(program=program, kind=kind,
                                      pattern=pattern, note=note)
    except IntegrityError:
        messages.warning(request, "Entrada duplicada, ignorada.")
        return redirect("programs:detail", slug=program.slug)

    messages.success(request, f"Entrada '{pattern}' adicionada.")
    return redirect("programs:detail", slug=program.slug)


@login_required
def delete_scope_entry(request, slug, pk):
    program = get_object_or_404(Program, slug=slug, owner=request.user)
    entry = get_object_or_404(ScopeEntry, pk=pk, program=program)
    if request.method != "POST":
        return HttpResponseBadRequest("POST obrigatorio")
    entry.delete()
    messages.success(request, "Entrada removida.")
    return redirect("programs:detail", slug=program.slug)
