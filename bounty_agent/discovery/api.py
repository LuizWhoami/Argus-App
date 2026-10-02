from typing import Optional


def _lc(s: Optional[str]) -> str:
    return (s or "").lower()


# Status aceitaveis por tipo. Tudo que nao estiver aqui eh descartado.
_ACCEPT_STATUS = {
    "swagger":  {200, 301, 302, 401, 403},
    "openapi":  {200, 301, 302, 401, 403},
    "graphql":  {200, 400, 401, 403, 405},   # /graphql sem query -> 400
    "rest":     {200, 201, 202, 204, 301, 302, 401, 403, 405},
}


def classify_api_endpoint(url: str, response: dict) -> Optional[str]:
    """
    Retorna 'swagger' | 'openapi' | 'graphql' | 'rest' | None.
    Rejeita 404, 5xx e status fora da whitelist de cada tipo.
    """
    u = _lc(url)
    ct = _lc(response.get("content_type"))
    status = response.get("status_code") or 0

    if status == 0 or status >= 500 or status == 404:
        return None

    def _ok(kind: str) -> bool:
        return status in _ACCEPT_STATUS[kind]

    # 1) Swagger
    if any(k in u for k in ("swagger-ui", "swagger.json", "swagger.yaml", "/swagger")):
        if _ok("swagger"):
            return "swagger"
        return None

    # 2) OpenAPI
    if any(k in u for k in ("openapi.json", "openapi.yaml", "api-docs", "/.well-known/openapi")):
        if _ok("openapi"):
            return "openapi"
        return None

    # 3) GraphQL
    if "graphql" in u or "graphiql" in u:
        if _ok("graphql"):
            return "graphql"
        return None

    # 4) REST generico: exige path suspeito E content-type compativel
    if any(k in u for k in ("/api", "/rest", "/v1", "/v2", "/v3")):
        if _ok("rest") and ("json" in ct or "xml" in ct):
            return "rest"

    return None
