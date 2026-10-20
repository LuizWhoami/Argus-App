import json
from typing import Optional
from .base import ToolAdapter


class KatanaAdapter(ToolAdapter):
    name = "katana"
    timeout = 1800

    def build_command(self, target=None, config=None,
                      depth=3, rate_limit=None,
                      js_crawl=True, **kwargs):
        cmd = [self.name, "-jsonl", "-silent", "-nc",
               "-d", str(depth), "-kf", "all"]
        if js_crawl:
            cmd += ["-jc", "-jsl"]
        if rate_limit:
            cmd += ["-rl", str(rate_limit)]
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
