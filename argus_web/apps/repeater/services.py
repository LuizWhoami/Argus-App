"""Logica de envio HTTP do Repeater."""
import time

import requests
from requests.exceptions import RequestException

from .validators import validate_url, SSRFBlocked


DEFAULT_TIMEOUT = 15
MAX_TIMEOUT = 60
MAX_BODY_BYTES = 2 * 1024 * 1024  # 2MB
MAX_RESPONSE_TIME_MS = 60_000


class RepeaterError(Exception):
    pass


def send_request(method: str, url: str, headers: dict,
                 body: str = "", timeout: int = DEFAULT_TIMEOUT,
                 allow_private: bool = False) -> dict:
    """Executa um request e retorna dict com a resposta."""
    method = (method or "GET").upper()
    if method not in ("GET", "POST", "PUT", "PATCH", "DELETE",
                      "OPTIONS", "HEAD"):
        raise RepeaterError(f"Metodo nao permitido: {method}")

    try:
        validate_url(url, allow_private=allow_private)
    except SSRFBlocked as e:
        raise RepeaterError(str(e))

    timeout = max(1, min(MAX_TIMEOUT, int(timeout or DEFAULT_TIMEOUT)))

    # Headers: sanitize (remover valores vazios/None)
    clean_headers = {}
    for k, v in (headers or {}).items():
        if not k or not isinstance(k, str):
            continue
        if v is None:
            continue
        clean_headers[k.strip()] = str(v).strip()

    # Body
    body_data = None
    if body and method not in ("GET", "HEAD"):
        body_data = body.encode("utf-8")
        if len(body_data) > MAX_BODY_BYTES:
            raise RepeaterError(f"Body muito grande ({len(body_data)} bytes)")

    t0 = time.time()
    try:
        r = requests.request(
            method=method,
            url=url,
            headers=clean_headers,
            data=body_data,
            timeout=timeout,
            allow_redirects=False,
            verify=False,
        )
    except requests.exceptions.Timeout:
        elapsed = int((time.time() - t0) * 1000)
        raise RepeaterError(f"Timeout ({timeout}s)")
    except RequestException as e:
        elapsed = int((time.time() - t0) * 1000)
        raise RepeaterError(f"Erro de conexao: {str(e)[:200]}")

    elapsed_ms = int((time.time() - t0) * 1000)

    # Body limitado
    content = r.content or b""
    truncated = False
    if len(content) > MAX_BODY_BYTES:
        content = content[:MAX_BODY_BYTES]
        truncated = True

    # Decodifica
    try:
        text = content.decode(r.encoding or "utf-8", errors="replace")
    except Exception:
        text = content.decode("latin-1", errors="replace")

    return {
        "status": r.status_code,
        "headers": dict(r.headers),
        "body": text,
        "size": len(r.content or b""),
        "time_ms": elapsed_ms,
        "truncated": truncated,
    }
