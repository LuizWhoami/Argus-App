from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import Wordlist


def _visible(user):
    """Wordlists embutidas + do proprio usuario."""
    return Wordlist.objects.filter(Q(is_builtin=True) | Q(owner=user))


@login_required
def list_wordlists(request):
    qs = _visible(request.user)
    kind = request.GET.get("kind", "").strip()
    if kind:
        qs = qs.filter(kind=kind)

    rows = list(qs)
    # Contagem de linhas carregada 1x para a UI
    for w in rows:
        w.line_count = len(w.load_lines())

    return render(request, "wordlists/list.html", {
        "rows": rows,
        "kinds": Wordlist.KIND_CHOICES,
        "current_kind": kind,
    })


@login_required
def new_wordlist(request):
    if request.method == "POST":
        name = (request.POST.get("name") or "").strip()
        kind = request.POST.get("kind") or ""
        description = (request.POST.get("description") or "").strip()
        content = (request.POST.get("content") or "").strip()
        upload = request.FILES.get("file")

        if not name:
            messages.error(request, "Nome obrigatorio.")
            return redirect("wordlists:new")
        if kind not in dict(Wordlist.KIND_CHOICES):
            messages.error(request, "Tipo invalido.")
            return redirect("wordlists:new")
        if not content and not upload:
            messages.error(request, "Forneca conteudo ou arquivo.")
            return redirect("wordlists:new")

        w = Wordlist(
            owner=request.user, name=name, kind=kind,
            description=description, content=content, file=upload,
        )
        w.save()
        messages.success(request, f"Wordlist '{w.name}' criada "
                                  f"({len(w.load_lines())} linhas).")
        return redirect("wordlists:list")

    return render(request, "wordlists/form.html", {
        "obj": None, "kinds": Wordlist.KIND_CHOICES,
    })


@login_required
def edit_wordlist(request, pk):
    w = get_object_or_404(Wordlist, pk=pk, owner=request.user)

    if request.method == "POST":
        w.name = (request.POST.get("name") or w.name).strip()
        w.description = (request.POST.get("description")
                         or "").strip()
        new_content = request.POST.get("content")
        if new_content is not None:
            w.content = new_content.strip()
        if request.FILES.get("file"):
            w.file = request.FILES["file"]
        w.save()
        messages.success(request, "Wordlist atualizada.")
        return redirect("wordlists:list")

    return render(request, "wordlists/form.html", {
        "obj": w, "kinds": Wordlist.KIND_CHOICES,
    })


@login_required
@require_POST
def delete_wordlist(request, pk):
    w = get_object_or_404(Wordlist, pk=pk, owner=request.user)
    if w.is_builtin:
        raise Http404
    name = w.name
    w.delete()
    messages.success(request, f"Wordlist '{name}' excluida.")
    return redirect("wordlists:list")


@login_required
def download_wordlist(request, pk):
    w = get_object_or_404(Wordlist, pk=pk)
    if not (w.is_builtin or w.owner_id == request.user.id):
        raise Http404
    body = "\n".join(w.load_lines())
    r = HttpResponse(body, content_type="text/plain; charset=utf-8")
    r["Content-Disposition"] = f'attachment; filename="{w.name}.txt"'
    return r


@login_required
def preview_wordlist(request, pk):
    w = get_object_or_404(Wordlist, pk=pk)
    if not (w.is_builtin or w.owner_id == request.user.id):
        raise Http404
    lines = w.load_lines()
    return render(request, "wordlists/preview.html", {
        "w": w, "lines": lines[:500], "total": len(lines),
    })
