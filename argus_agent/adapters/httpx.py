import json
from typing import Optional
from .base import ToolAdapter


class HttpxAdapter(ToolAdapter):
    name = "httpx"

    def build_command(self, target: Optional[str] = None,
                      config: Optional[dict] = None,
                      paths: Optional[list] = None,
                      rate_limit: Optional[int] = None,
                      **kwargs) -> list[str]:
        cmd = [
            self.name,
            "-silent",
            "-json",
            "-no-color",
            "-status-code",
            "-title",
            "-tech-detect",
            "-web-server",
            "-content-type",
            "-location",
            "-follow-redirects",
        ]
        if rate_limit:
            cmd.extend(["-rl", str(rate_limit)])
        if paths:
            for p in paths:
                cmd.extend(["-path", p])
        return cmd

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
