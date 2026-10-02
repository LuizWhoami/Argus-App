import shutil
import subprocess
from abc import ABC, abstractmethod
from typing import Optional


class ToolAdapter(ABC):
    name: str = ""
    timeout: int = 600

    def check_installation(self) -> bool:
        return shutil.which(self.name) is not None

    @abstractmethod
    def build_command(self, target: Optional[str] = None,
                      config: Optional[dict] = None,
                      **kwargs) -> list[str]:
        ...

    @abstractmethod
    def parse_output(self, stdout: str):
        ...

    def execute(self, target: Optional[str] = None,
                input_data: Optional[str] = None,
                config: Optional[dict] = None,
                **kwargs):
        if not self.check_installation():
            raise RuntimeError(f"Ferramenta '{self.name}' nao encontrada no PATH")
        cmd = self.build_command(target, config, **kwargs)
        try:
            proc = subprocess.run(
                cmd, input=input_data, text=True, capture_output=True,
                check=False, timeout=self.timeout,
            )
        except subprocess.TimeoutExpired as e:
            raise RuntimeError(f"{self.name} excedeu timeout de {self.timeout}s") from e
        if proc.returncode != 0:
            raise RuntimeError(f"{self.name} falhou: {proc.stderr.strip()}")
        return self.parse_output(proc.stdout)
