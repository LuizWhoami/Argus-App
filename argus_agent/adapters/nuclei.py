import json
from typing import Optional
from .base import ToolAdapter


class NucleiAdapter(ToolAdapter):
    """Adapter do nuclei.

    SEGURANCA: por padrao roda apenas templates PASSIVOS.
    Templates de CVE, injection, xss exigem `tags` explicito.
    """
    name = "nuclei"
    timeout = 1800

    DEFAULT_TAGS = "exposure,misconfig,tech,ssl,dns"

    def build_command(self, target=None, config=None,
                      tags=None, severity="info,low,medium,high,critical",
                      rate_limit=None, templates=None, **kwargs):
        cmd = [
            self.name,
            "-jsonl",
            "-silent",
            "-no-color",
            "-severity", severity,
            "-timeout", "10",
            "-retries", "1",
            "-stats=false",
        ]
        if templates:
            cmd += ["-t", templates]
        else:
            cmd += ["-tags", tags or self.DEFAULT_TAGS]
        if rate_limit:
            cmd += ["-rl", str(rate_limit)]
            cmd += ["-c", str(min(rate_limit, 25))]
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
