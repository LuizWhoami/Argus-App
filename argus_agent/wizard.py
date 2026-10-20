from typing import List, Optional
from pathlib import Path
from rich.console import Console
from rich.prompt import Prompt, Confirm, IntPrompt

from .config import Config, ProgramConfig
from .scope import Scope

console = Console()


def _ask_list(label: str, initial: Optional[List[str]] = None,
              required: bool = False) -> List[str]:
    items: List[str] = list(initial or [])
    console.print(f"\n[bold cyan]{label}[/bold cyan]")
    if items:
        console.print(f"  atuais: [dim]{items}[/dim]")
    console.print("  [dim](Enter vazio termina | '!' limpa tudo | 'del X' remove X)[/dim]")

    while True:
        v = Prompt.ask("  >", default="", show_default=False).strip()
        if v == "":
            break
        if v == "!":
            items = []
            console.print("  [yellow]lista limpa[/yellow]")
            continue
        if v.startswith("del "):
            target = v[4:].strip()
            if target in items:
                items.remove(target)
                console.print(f"  [red]- {target}[/red]")
            else:
                console.print(f"  [yellow]nao existe: {target}[/yellow]")
            continue
        if v in items:
            console.print(f"  [yellow]ja existe: {v}[/yellow]")
            continue
        items.append(v)
        console.print(f"  [green]+ {v}[/green]")

    if required and not items:
        console.print("[red]A lista 'allowed' nao pode ficar vazia.[/red]")
        return _ask_list(label, items, required=True)
    return items


def run_wizard(path: str = "program.yaml") -> Config:
    p = Path(path)
    if p.exists():
        console.print(f"[yellow]Arquivo {path} ja existe.[/yellow]")
        if not Confirm.ask("Sobrescrever?", default=False):
            console.print("[dim]Cancelado.[/dim]")
            raise SystemExit(0)
        default = Config.load(path).program
    else:
        default = ProgramConfig(name="new-program", allowed=["example.com"])

    console.print("\n[bold]Assistente de escopo — Bounty Agent[/bold]\n")

    name = Prompt.ask("Nome do programa", default=default.name)
    allowed = _ask_list("Dominios PERMITIDOS (ex: *.example.com)",
                        initial=default.allowed, required=True)
    excluded = _ask_list("Dominios EXCLUIDOS (opcional)",
                         initial=default.excluded, required=False)
    max_rps = IntPrompt.ask("Max RPS", default=default.max_rps)
    aggressive = Confirm.ask("Scan agressivo?",
                             default=default.aggressive_scanning)
    destructive = Confirm.ask("Testes destrutivos?",
                              default=default.destructive_testing)

    cfg = Config(program=ProgramConfig(
        name=name, allowed=allowed, excluded=excluded,
        max_rps=max_rps, aggressive_scanning=aggressive,
        destructive_testing=destructive,
    ))
    cfg.save(path)
    console.print(f"\n[green]OK[/green] escopo gravado em {path}")
    preview(cfg)
    return cfg


def preview(cfg: Config) -> None:
    console.print("\n[bold]Escopo efetivo[/bold]")
    console.print(f"  nome ........: {cfg.program.name}")
    console.print(f"  allowed .....: {cfg.program.allowed}")
    console.print(f"  excluded ....: {cfg.program.excluded}")
    console.print(f"  max_rps .....: {cfg.program.max_rps}")
    console.print(f"  aggressive ..: {cfg.program.aggressive_scanning}")
    console.print(f"  destructive .: {cfg.program.destructive_testing}")
    console.print("\n[dim]Dica: 'bounty scope check <host>' valida um host.[/dim]")
