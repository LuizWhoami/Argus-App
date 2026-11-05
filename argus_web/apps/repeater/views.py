import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST

from .models import RepeaterRequest
from .services import send_request, RepeaterError


@login_required
@csrf_protect
@require_POST
def api_send(request):
    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "JSON invalido"}, status=400)

    method = (data.get("method") or "GET").upper()
    url = (data.get("url") or "").strip()
    headers = data.get("headers") or {}
    body = data.get("body") or ""
    timeout = data.get("timeout") or 15

    if not url:
        return JsonResponse({"error": "URL obrigatoria"}, status=400)

    # Cria registro (mesmo se falhar)
    rec = RepeaterRequest.objects.create(
        owner=request.user,
        method=method,
        url=url[:2048],
        request_headers=headers,
        request_body=body[:100_000],
    )

    try:
        result = send_request(
            method=method, url=url, headers=headers,
            body=body, timeout=timeout,
        )
    except RepeaterError as e:
        rec.error = str(e)[:500]
        rec.save(update_fields=["error"])
        return JsonResponse({"error": str(e)}, status=400)

    # Salva resposta
    rec.response_status = result["status"]
    rec.response_headers = result["headers"]
    rec.response_body = result["body"][:100_000]
    rec.response_size = result["size"]
    rec.response_time_ms = result["time_ms"]
    rec.save()

    return JsonResponse({
        "id": rec.pk,
        "status": result["status"],
        "headers": result["headers"],
        "body": result["body"],
        "size": result["size"],
        "time_ms": result["time_ms"],
        "truncated": result["truncated"],
    })


@login_required
def api_history(request):
    rows = (RepeaterRequest.objects
            .filter(owner=request.user)
            .values("id", "method", "url", "response_status",
                    "response_time_ms", "created_at")[:50])
    return JsonResponse({"results": list(rows)})


@login_required
def index(request):
    from django.shortcuts import render
    return render(request, "repeater/index.html")
