import typer
from rich.console import Console
from rich.table import Table

from .config import Config
from .scope import Scope
from .pipeline import run_scan
from .database import DEFAULT_DB, init_db, get_session
from .wizard import run_wizard, preview
from .models import APIEndpoint, Parameter

app = typer.Typer(help="Autonomous Bug Bounty Agent", no_args_is_help=True)
scope_app = typer.Typer(help="Gerencia o escopo (program.yaml)", no_args_is_help=True)
api_app = typer.Typer(help="Consulta endpoints de API", no_args_is_help=True)
app.add_typer(scope_app, name="scope")
app.add_typer(api_app, name="api")

console = Console()
CONFIG_PATH = "program.yaml"


@app.command()
def init(
    config: str = typer.Option(CONFIG_PATH, "--config", "-c"),
    wizard: bool = typer.Option(True, "--wizard/--no-wizard"),
):
    """Cria ou reconfigura o escopo do programa."""
    if wizard:
        run_wizard(config)
    else:
        try:
            cfg = Config.load(config)
            console.print(f"[green]OK[/green] programa '{cfg.program.name}' carregado de {config}")
        except Exception as e:
            console.print(f"[red]Falha: {e}[/red]")
            raise typer.Exit(1)


@scope_app.command("show")
def scope_show(config: str = typer.Option(CONFIG_PATH, "--config", "-c")):
    preview(Config.load(config))


@scope_app.command("check")
def scope_check(host: str, config: str = typer.Option(CONFIG_PATH, "--config", "-c")):
    cfg = Config.load(config)
    s = Scope(cfg.program.allowed, cfg.program.excluded)
    if s.is_allowed(host):
        console.print(f"[green]ALLOW[/green] {host}")
    else:
        console.print(f"[red]DENY[/red]  {host}")
        raise typer.Exit(2)


def _mutate(config_path: str, mutate) -> None:
    cfg = Config.load(config_path)
    mutate(cfg.program)
    cfg.save(config_path)
    preview(cfg)


@scope_app.command("add")
def scope_add(pattern: str, config: str = typer.Option(CONFIG_PATH, "--config", "-c")):
    def m(p):
        if pattern not in p.allowed:
            p.allowed.append(pattern)
    _mutate(config, m)


@scope_app.command("exclude")
def scope_exclude(pattern: str, config: str = typer.Option(CONFIG_PATH, "--config", "-c")):
    def m(p):
        if pattern not in p.excluded:
            p.excluded.append(pattern)
    _mutate(config, m)


@scope_app.command("remove")
def scope_remove(pattern: str, config: str = typer.Option(CONFIG_PATH, "--config", "-c")):
    def m(p):
        if pattern in p.allowed:
            p.allowed.remove(pattern)
        if not p.allowed:
            raise typer.BadParameter("allowed ficaria vazio")
    _mutate(config, m)


@scope_app.command("include")
def scope_include(pattern: str, config: str = typer.Option(CONFIG_PATH, "--config", "-c")):
    def m(p):
        if pattern in p.excluded:
            p.excluded.remove(pattern)
    _mutate(config, m)


@app.command()
def scan(
    target: str,
    config: str = typer.Option(CONFIG_PATH, "--config", "-c"),
    db: str = typer.Option(DEFAULT_DB, "--db"),
    dry_run: bool = typer.Option(False, "--dry-run"),
    api: bool = typer.Option(True, "--api/--no-api",
                             help="Rodar etapa de API discovery"),
    wordlist: str = typer.Option(
        None, "--wordlist", "-w",
        help="Arquivo de paths (1 por linha). Default: wordlists/api_paths.txt",
    ),
):
    """Executa pipeline de recon contra alvo autorizado."""
    run_scan(target=target, config_path=config, db_url=db,
             dry_run=dry_run, api_scan=api, wordlist=wordlist)


@api_app.command("list")
def api_list(
    db: str = typer.Option(DEFAULT_DB, "--db"),
    kind: str = typer.Option(None, "--kind", help="swagger|openapi|graphql|rest"),
):
    """Lista endpoints de API descobertos."""
    init_db(db)
    s = get_session()
    q = s.query(APIEndpoint)
    if kind:
        q = q.filter_by(kind=kind)
    rows = q.order_by(APIEndpoint.id.desc()).all()
    if not rows:
        console.print("[yellow]Nenhum endpoint de API registrado.[/yellow]")
        return
    table = Table(title=f"API endpoints ({len(rows)})")
    table.add_column("id", style="dim")
    table.add_column("kind", style="cyan")
    table.add_column("status")
    table.add_column("url")
    for r in rows:
        table.add_row(str(r.id), r.kind or "", str(r.status_code or ""), r.url or "")
    console.print(table)
    s.close()


@api_app.command("params")
def api_params(
    db: str = typer.Option(DEFAULT_DB, "--db"),
    location: str = typer.Option(None, "--loc", help="query|form"),
):
    """Lista parametros descobertos."""
    init_db(db)
    s = get_session()
    q = s.query(Parameter)
    if location:
        q = q.filter_by(location=location)
    rows = q.order_by(Parameter.id.desc()).all()
    if not rows:
        console.print("[yellow]Nenhum parametro registrado.[/yellow]")
        return
    table = Table(title=f"Parameters ({len(rows)})")
    table.add_column("id", style="dim")
    table.add_column("loc", style="cyan")
    table.add_column("name")
    table.add_column("endpoint")
    for r in rows:
        table.add_row(str(r.id), r.location or "", r.name or "", r.endpoint or "")
    console.print(table)
    s.close()


if __name__ == "__main__":
    app()
