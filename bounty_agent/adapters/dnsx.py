import json
from typing import Optional
from .base import ToolAdapter


class DnsxAdapter(ToolAdapter):
    name = "dnsx"

    def build_command(self, target: Optional[str] = None,
                      config: Optional[dict] = None) -> list[str]:
        return [self.name, "-silent", "-resp", "-json", "-no-color"]

    def parse_output(self, stdout: str):
        results = []
        for line in stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                results.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return results
