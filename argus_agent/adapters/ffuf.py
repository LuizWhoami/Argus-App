import json
from typing import Optional
from .base import ToolAdapter


class FfufAdapter(ToolAdapter):
    name = "ffuf"
    timeout = 1200

    def build_command(self, target=None, config=None,
                      rate_limit=None, extensions=None, **kwargs):
        if not target:
            raise ValueError("ffuf requer target (URL)")
        cmd = [
            self.name,
            "-u", target.rstrip("/") + "/FUZZ",
            "-w", "/dev/stdin",
            "-json", "-s",
            "-mc", "200,301,302,401,403",
            "-ac", "-timeout", "10", "-t", "20",
        ]
        if extensions:
            cmd += ["-e", extensions]
        if rate_limit:
            cmd += ["-rate", str(rate_limit)]
        return cmd

    def parse_output(self, stdout):
        out = []
        for line in stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return out
