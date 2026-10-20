from typing import List
import yaml
from pydantic import BaseModel, field_validator


class ProgramConfig(BaseModel):
    name: str
    allowed: List[str]
    excluded: List[str] = []
    max_rps: int = 5
    aggressive_scanning: bool = False
    destructive_testing: bool = False

    @field_validator("allowed")
    @classmethod
    def _allowed_not_empty(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError("program.allowed nao pode estar vazio")
        return v


class Config(BaseModel):
    program: ProgramConfig

    @classmethod
    def load(cls, path: str) -> "Config":
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return cls(**data)

    def save(self, path: str) -> None:
        # revalida antes de gravar
        fresh = Config(program=ProgramConfig(**self.program.model_dump()))
        with open(path, "w", encoding="utf-8") as f:
            yaml.safe_dump(fresh.model_dump(), f,
                           sort_keys=False, allow_unicode=True)
