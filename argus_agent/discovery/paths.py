from pathlib import Path
from typing import List, Optional

# Fallback minimo se wordlist nao existir.
_FALLBACK = [
    "/api", "/api/v1", "/api/v2", "/v1", "/v2",
    "/graphql", "/swagger.json", "/openapi.json",
]

DEFAULT_WORDLIST = Path("wordlists/api_paths.txt")


def _load_file(path: Path) -> List[str]:
    out: List[str] = []
    seen = set()
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if not line.startswith("/"):
            line = "/" + line
        if line not in seen:
            seen.add(line)
            out.append(line)
    return out


def load_api_paths(wordlist: Optional[str] = None) -> List[str]:
    """
    Carrega paths de API.
    Ordem de resolucao:
      1. wordlist explicito (str) passado por --wordlist
      2. wordlists/api_paths.txt no cwd
      3. lista fallback embutida
    """
    if wordlist:
        p = Path(wordlist)
        if not p.exists():
            raise FileNotFoundError(f"wordlist nao encontrada: {p}")
        return _load_file(p)

    if DEFAULT_WORDLIST.exists():
        return _load_file(DEFAULT_WORDLIST)

    return list(_FALLBACK)


# Compatibilidade: alguns modulos ainda importam COMMON_API_PATHS.
COMMON_API_PATHS = load_api_paths()
