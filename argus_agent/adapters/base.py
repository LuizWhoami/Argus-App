import os
import shutil
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional


def _common_tool_dirs():
    home = Path.home()
    dirs = [
        home / "go" / "bin",
        Path("/usr/local/go/bin"),
        Path("/usr/local/bin"),
        Path("/usr/bin"),
        Path("/bin"),
    ]
    gopath = os.environ.get("GOPATH")
    if gopath:
        dirs.insert(0, Path(gopath) / "bin")
    return [d for d in dirs if d.exists()]


def find_tool(name: str) -> Optional[str]:
    p = shutil.which(name)
    if p:
        return p
    for d in _common_tool_dirs():
        candidate = d / name
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


class ToolAdapter(ABC):
    name: str = ""
    timeout: int = 600

    def _resolve(self) -> Optional[str]:
        return find_tool(self.name)

    def check_installation(self) -> bool:
        return self._resolve() is not None

    @abstractmethod
    def build_command(self, target=None, config=None, **kwargs):
        ...

    @abstractmethod
    def parse_output(self, stdout: str):
        ...

    def execute(self, target=None, input_data=None, config=None, **kwargs):
        binary = self._resolve()
        if not binary:
            raise RuntimeError(
                f"Ferramenta '{self.name}' nao encontrada. "
                f"Procurei no PATH e em ~/go/bin."
            )
        cmd = self.build_command(target, config, **kwargs)
        if cmd and cmd[0] == self.name:
            cmd = [binary] + cmd[1:]
        try:
            proc = subprocess.run(
                cmd, input=input_data, text=True, capture_output=True,
                check=False, timeout=self.timeout,
            )
        except subprocess.TimeoutExpired as e:
            raise RuntimeError(f"{self.name} excedeu timeout") from e
        if proc.returncode != 0:
            raise RuntimeError(f"{self.name} falhou: {proc.stderr.strip()}")
        return self.parse_output(proc.stdout)
