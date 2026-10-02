from typing import Optional
from .base import ToolAdapter


class SubfinderAdapter(ToolAdapter):
    name = "subfinder"

    def build_command(self, target: Optional[str] = None,
                      config: Optional[dict] = None) -> list[str]:
        if not target:
            raise ValueError("subfinder requer um dominio alvo")
        return [self.name, "-d", target, "-silent"]

    def parse_output(self, stdout: str):
        return [line.strip() for line in stdout.splitlines() if line.strip()]
