"""
Ponte unica entre o Django e o core do Argus (argus_agent).

Regra: nenhum outro app Django importa argus_agent diretamente.
"""
from argus_agent.scope import Scope


def scope_check(host: str, allowed: list[str], excluded: list[str]) -> bool:
    """Retorna True se `host` estiver dentro do escopo permitido."""
    return Scope(allowed=allowed, excluded=excluded).is_allowed(host)
