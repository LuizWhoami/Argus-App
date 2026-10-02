from typing import Optional
from urllib.parse import urlparse

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from .config import Config
from .scope import Scope
from .database import init_db, get_session, DEFAULT_DB
from .models import Scan, Asset, DNSRecord, HTTPProbe, APIEndpoint, Parameter
from .adapters import SubfinderAdapter, DnsxAdapter, HttpxAdapter
from .discovery.paths import load_api_paths
from .discovery import (
    classify_api_endpoint,
    extract_query_params,
    extract_form_params,
)
from .discovery.params import fetch_html

console = Console()

MAX_FORM_FETCH = 40  # limite de páginas HTML baixadas para extração de forms


def _ensure_tools():
    missing = [a.name for a in (SubfinderAdapter(), DnsxAdapter(), HttpxAdapter())
               if not a.check_installation()]
    if missing:
        raise RuntimeError(
            "Ferramentas ausentes no PATH: " + ", ".join(missing) +
            "\nInstale com: go install github.com/projectdiscovery/...@latest"
        )


def _host_of(url: str) -> str:
    try:
        return urlparse(url).hostname or ""
    except Exception:
        return ""


def run_scan(target: str, config_path: str = "program.yaml",
             db_url: str = DEFAULT_DB,
             dry_run: bool = False,
             api_scan: bool = True,
             wordlist: Optional[str] = None) -> Optional[dict]:
    config = Config.load(config_path)
    scope = Scope(config.program.allowed, config.program.excluded)

    if not scope.is_allowed(target):
        console.print(f"[red]Alvo '{target}' fora do escopo declarado em {config_path}[/red]")
        return None

    console.print(f"[bold]Bounty Agent v0.2[/bold]\nTarget: {target}\n")
    console.print(f"Escopo permitido: {config.program.allowed}")
    console.print(f"Escopo excluido: {config.program.excluded}")
    console.print(f"Max RPS: {config.program.max_rps}")
    console.print(f"API scan: {'on' if api_scan else 'off'}\n")

    if dry_run:
        console.print("[yellow]--dry-run: nenhuma ferramenta sera executada.[/yellow]")
        return {"target": target, "dry_run": True}

    _ensure_tools()
    init_db(db_url)
    session = get_session()

    scan = Scan(target=target)
    session.add(scan)
    session.commit()

    total_steps = 6 if api_scan else 4
    summary = {"subdomains": 0, "resolved": 0, "alive": 0, "api": 0, "params": 0}

    try:
        with Progress(SpinnerColumn(),
                      TextColumn("[progress.description]{task.description}"),
                      console=console) as progress:

            # 1) Scope
            t = progress.add_task("[1/%d] Scope validation ..." % total_steps, total=None)
            progress.update(t, description=f"[1/{total_steps}] Scope validation ...... OK")
            progress.stop_task(t)

            # 2) Subdomain enumeration
            t = progress.add_task(f"[2/{total_steps}] Subdomain enumeration ...", total=None)
            subdomains = SubfinderAdapter().execute(target)
            subdomains.append(target)  # inclui o proprio alvo
            subdomains = sorted({s for s in subdomains if scope.is_allowed(s)})
            summary["subdomains"] = len(subdomains)
            progress.update(t, description=f"[2/{total_steps}] Subdomain enumeration ... {len(subdomains)} found")
            progress.stop_task(t)

            if not subdomains:
                console.print("[yellow]Nenhum subdominio dentro do escopo.[/yellow]")
                scan.status = "completed-no-assets"
                return summary

            asset_map = {}
            for host in subdomains:
                a = session.query(Asset).filter_by(hostname=host).first()
                if not a:
                    a = Asset(hostname=host, scan_id=scan.id)
                    session.add(a)
                    session.flush()
                asset_map[host] = a
            session.commit()

            # 3) DNS
            t = progress.add_task(f"[3/{total_steps}] DNS resolution ...", total=None)
            dns_results = DnsxAdapter().execute(input_data="\n".join(subdomains))
            resolved = set()
            for res in dns_results:
                host = res.get("host")
                if not host or host not in asset_map:
                    continue
                resolved.add(host)
                for a in res.get("a", []) or []:
                    session.add(DNSRecord(asset_id=asset_map[host].id,
                                          record_type="A", value=a))
            session.commit()
            summary["resolved"] = len(resolved)
            progress.update(t, description=f"[3/{total_steps}] DNS resolution ......... {len(resolved)} resolved")
            progress.stop_task(t)

            # 4) HTTP probing
            t = progress.add_task(f"[4/{total_steps}] HTTP probing ...", total=None)
            http_results = []
            if resolved:
                http_results = HttpxAdapter().execute(
                    input_data="\n".join(sorted(resolved)),
                    rate_limit=config.program.max_rps,
                )
            live_urls = []
            for res in http_results:
                host = res.get("host") or res.get("input") or _host_of(res.get("url", ""))
                if not host or host not in asset_map:
                    continue
                tech = res.get("tech") or []
                if isinstance(tech, list):
                    tech = ",".join(tech)
                session.add(HTTPProbe(
                    asset_id=asset_map[host].id,
                    scan_id=scan.id,
                    url=res.get("url"),
                    status_code=res.get("status_code"),
                    content_type=res.get("content_type"),
                    title=res.get("title"),
                    tech=tech,
                    webserver=res.get("webserver", ""),
                    location=res.get("location", ""),
                ))
                if res.get("url"):
                    live_urls.append(res["url"])
            session.commit()
            summary["alive"] = len(live_urls)
            progress.update(t, description=f"[4/{total_steps}] HTTP probing ............ {len(live_urls)} alive")
            progress.stop_task(t)

            if not api_scan or not live_urls:
                scan.status = "completed"
                session.commit()
                console.print(f"\nAssets discovered: {summary['subdomains']}")
                console.print(f"Live hosts: {summary['alive']}")
                console.print("\nScan completed.")
                return summary

            # 5) API discovery
            t = progress.add_task(f"[5/{total_steps}] API discovery ...", total=None)
            api_paths = load_api_paths(wordlist)
            console.print(f"[dim]wordlist: {len(api_paths)} paths "
                          f"({wordlist or 'wordlists/api_paths.txt'})[/dim]")
            api_results = HttpxAdapter().execute(
                input_data="\n".join(live_urls),
                paths=api_paths,
                rate_limit=config.program.max_rps,
            )
            api_count = 0
            for res in api_results:
                url = res.get("url") or ""
                kind = classify_api_endpoint(url, res)
                if not kind:
                    continue
                session.add(APIEndpoint(
                    scan_id=scan.id,
                    host=res.get("host") or _host_of(url),
                    url=url,
                    kind=kind,
                    status_code=res.get("status_code"),
                    content_type=res.get("content_type"),
                ))
                api_count += 1
            session.commit()
            summary["api"] = api_count
            progress.update(t, description=f"[5/{total_steps}] API discovery ............ {api_count} endpoints")
            progress.stop_task(t)

            # 6) Parameter extraction
            t = progress.add_task(f"[6/{total_steps}] Parameter extraction ...", total=None)
            param_count = 0
            seen = set()

            # 6a) query strings das URLs vivas + endpoints API
            all_urls = set(live_urls)
            for ep in session.query(APIEndpoint).filter_by(scan_id=scan.id):
                if ep.url:
                    all_urls.add(ep.url)
            for url in all_urls:
                for pname in extract_query_params(url):
                    key = (url, pname, "query")
                    if key in seen:
                        continue
                    seen.add(key)
                    session.add(Parameter(scan_id=scan.id, endpoint=url,
                                          name=pname, location="query"))
                    param_count += 1

            # 6b) forms em paginas HTML (limitado)
            html_urls = [u for u in live_urls if not u.endswith((".js", ".json", ".png", ".jpg", ".css"))]
            for url in html_urls[:MAX_FORM_FETCH]:
                html = fetch_html(url)
                if not html:
                    continue
                for pname in extract_form_params(html):
                    key = (url, pname, "form")
                    if key in seen:
                        continue
                    seen.add(key)
                    session.add(Parameter(scan_id=scan.id, endpoint=url,
                                          name=pname, location="form"))
                    param_count += 1
            session.commit()
            summary["params"] = param_count
            progress.update(t, description=f"[6/{total_steps}] Parameter extraction ... {param_count} params")
            progress.stop_task(t)

        scan.status = "completed"
        session.commit()

        console.print(f"\nAssets discovered: {summary['subdomains']}")
        console.print(f"Live hosts: {summary['alive']}")
        console.print(f"API endpoints: {summary['api']}")
        console.print(f"Parameters: {summary['params']}")
        console.print("\nScan completed.")
        return summary

    except Exception as e:
        session.rollback()
        try:
            scan_db = session.get(Scan, scan.id)
            if scan_db:
                scan_db.status = "error"
                session.commit()
        except Exception:
            session.rollback()
        console.print(f"[red]Erro durante scan: {e}[/red]")
        raise
    finally:
        session.close()
