import json
import os
import subprocess
import tempfile
from typing import Optional

from .base import ToolAdapter


class DirsearchAdapter(ToolAdapter):
    """Adapter do dirsearch 0.5.x com recursao.

    Flags corretas para 0.5.x:
      -O FORMAT  (json, simple, xml, html, csv)
      -o PATH    (output file)

    Wordlist vem SEMPRE do input_data (form do scan).
    Se vazia, usa a default embutida do dirsearch.
    """
    name = "dirsearch"
    timeout = 2400

    def build_command(self, target: Optional[str] = None,
                      config: Optional[dict] = None,
                      wordlist_file: Optional[str] = None,
                      output_file: Optional[str] = None,
                      recursion_depth: int = 2,
                      extensions: Optional[str] = None,
                      threads: int = 10,
                      exclude_status: str = "404,400",
                      **kwargs) -> list[str]:
        if not target:
            raise ValueError("dirsearch requer target (URL)")

        cmd = [
            self.name,
            "-u", target,
            "-O", "json",
            "-q",
            "-r",
            "-R", str(recursion_depth),
            "-t", str(threads),
            "--exclude-status", exclude_status,
        ]
        if output_file:
            cmd.extend(["-o", output_file])
        if wordlist_file:
            cmd.extend(["-w", wordlist_file])
        if extensions:
            cmd.extend(["-e", extensions])
        return cmd

    def parse_output(self, content: str):
        if not content.strip():
            return []
        try:
            data = json.loads(content)
            if isinstance(data, dict):
                return data.get("results", [])
            if isinstance(data, list):
                return data
        except json.JSONDecodeError:
            pass

        out = []
        for line in content.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                if isinstance(obj, dict):
                    out.append(obj)
            except json.JSONDecodeError:
                continue
        return out

    def execute(self, target=None, input_data=None, config=None, **kwargs):
        binary = self._resolve()
        if not binary:
            raise RuntimeError(
                f"Ferramenta '{self.name}' nao encontrada. "
                f"Instale: pip install dirsearch"
            )

        wordlist_file = None
        if input_data and input_data.strip():
            fd_wl, wordlist_file = tempfile.mkstemp(
                suffix=".txt", prefix="dirsearch_wl_")
            with os.fdopen(fd_wl, "w") as f:
                f.write(input_data)

        fd_out, output_file = tempfile.mkstemp(
            suffix=".json", prefix="dirsearch_out_")
        os.close(fd_out)

        try:
            cmd = self.build_command(
                target, config,
                wordlist_file=wordlist_file,
                output_file=output_file,
                **kwargs,
            )
            if cmd and cmd[0] == self.name:
                cmd = [binary] + cmd[1:]

            try:
                proc = subprocess.run(
                    cmd, text=True, capture_output=True,
                    check=False, timeout=self.timeout,
                )
            except subprocess.TimeoutExpired as e:
                raise RuntimeError(
                    f"{self.name} excedeu timeout de {self.timeout}s"
                ) from e

            with open(output_file, "r") as f:
                content = f.read()

            if not content.strip():
                stderr = (proc.stderr or "").strip()[:300]
                stdout = (proc.stdout or "").strip()[:300]
                raise RuntimeError(
                    f"dirsearch nao gerou output "
                    f"(exit={proc.returncode}).\n"
                    f"stderr: {stderr or '(vazio)'}\n"
                    f"stdout: {stdout or '(vazio)'}"
                )

            return self.parse_output(content)

        finally:
            try:
                if wordlist_file:
                    os.unlink(wordlist_file)
            except Exception:
                pass
            try:
                os.unlink(output_file)
            except Exception:
                pass
