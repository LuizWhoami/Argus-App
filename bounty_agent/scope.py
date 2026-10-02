import fnmatch
from typing import List


class Scope:
    def __init__(self, allowed: List[str], excluded: List[str]):
        self.allowed = [a.lower().strip() for a in allowed]
        self.excluded = [e.lower().strip() for e in excluded]

    def is_allowed(self, host: str) -> bool:
        host = host.lower().strip()
        for pat in self.excluded:
            if self._match(host, pat):
                return False
        for pat in self.allowed:
            if self._match(host, pat):
                return True
        return False

    def _match(self, host: str, pattern: str) -> bool:
        if pattern.startswith("*."):
            base = pattern[2:]
            return host == base or host.endswith("." + base)
        return fnmatch.fnmatch(host, pattern)
