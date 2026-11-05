"""Pipeline como gerador de eventos estruturados.

Nao escreve no banco, nao imprime. Cada chamador decide o que fazer
com os eventos:
  - CLI: imprime com Rich e grava em SQLAlchemy
  - Django: grava nos models e transmite pra UI

Etapas:
  scope → subdomains → dns → http → directories → crawl → api → vulns → params
"""
from typing import Generator, Optional
from urllib.parse import urlparse

from .adapters import (
    SubfinderAdapter, DnsxAdapter, HttpxAdapter, KatanaAdapter,
    NucleiAdapter, DirsearchAdapter,
)
from .discovery import (
    classify_api_endpoint, extract_query_params, extract_form_params,
)
from .discovery.paths import load_api_paths
from .discovery.params import fetch_html
from .scope import Scope


Event = dict

STAGE_ORDER = {
    "scope": 1,
    "subdomains": 2,
    "dns": 3,
    "http": 4,
    "directories": 5,
    "crawl": 6,
    "api": 7,
    "vulns": 8,
    "params": 9,
}


def _host_of(url: str) -> str:
    try:
        return urlparse(url).hostname or ""
    except Exception:
        return ""


def iter_scan_events(
    target: str,
    scope: Scope,
    *,
    max_rps: int = 5,
    api_scan: bool = True,
    crawl: bool = True,
    crawl_depth: int = 3,
    wordlist: Optional[str] = None,
    wordlist_lines: Optional[list] = None,
    form_fetch_limit: int = 40,
    vuln_scan: bool = False,
    vuln_tags: Optional[str] = None,
    dir_scan: bool = False,
    dir_wordlist_lines: Optional[list] = None,
    dir_depth: int = 2,
) -> Generator[Event, None, None]:
    """Gera eventos do scan. Nao escreve no banco, nao imprime."""

    yield {"event": "scan.started", "target": target}

    if not scope.is_allowed(target):
        yield {"event": "scan.failed",
               "error": f"target {target} fora do escopo"}
        return

    # ---- 1. scope ----
    yield {"event": "stage.started", "stage": "scope",
           "order": STAGE_ORDER["scope"]}
    yield {"event": "stage.completed", "stage": "scope", "count": 0}

    # ---- 2. subdomains ----
    yield {"event": "stage.started", "stage": "subdomains",
           "order": STAGE_ORDER["subdomains"]}
    try:
        subs = SubfinderAdapter().execute(target)
    except Exception as e:
        yield {"event": "stage.failed", "stage": "subdomains",
               "error": str(e)}
        yield {"event": "scan.failed", "error": str(e)}
        return

    subs.append(target)
    subs = sorted({s for s in subs if scope.is_allowed(s)})
    yield {"event": "stage.completed", "stage": "subdomains",
           "count": len(subs)}

    if not subs:
        yield {"event": "scan.completed",
               "summary": {"subdomains": 0, "resolved": 0,
                           "alive": 0, "crawled": 0,
                           "directories": 0, "api": 0, "vulns": 0,
                           "params": 0}}
        return

    # ---- 3. dns ----
    yield {"event": "stage.started", "stage": "dns",
           "order": STAGE_ORDER["dns"]}
    try:
        dns_results = DnsxAdapter().execute(input_data="\n".join(subs))
    except Exception as e:
        yield {"event": "stage.failed", "stage": "dns", "error": str(e)}
        dns_results = []

    resolved = set()
    for res in dns_results:
        host = res.get("host")
        if not host or host not in subs:
            continue
        resolved.add(host)
        ips = res.get("a") or []
        for ip in ips:
            yield {"event": "dns.record", "hostname": host,
                   "record_type": "A", "value": ip}
        yield {"event": "asset.found", "hostname": host,
               "ip": ips[0] if ips else None}
    yield {"event": "stage.completed", "stage": "dns",
           "count": len(resolved)}

    # ---- 4. http ----
    # httpx por host individual: se 1 falhar, os outros continuam
    yield {"event": "stage.started", "stage": "http",
           "order": STAGE_ORDER["http"]}
    http_results = []
    for host in sorted(resolved):
        try:
            results = HttpxAdapter().execute(
                input_data=host,
                rate_limit=max_rps,
            )
            http_results.extend(results)
        except Exception as e:
            yield {"event": "stage.info", "stage": "http",
                   "message": f"{host}: {str(e)[:100]}"}

    live_urls = []
    for res in http_results:
        host = (res.get("host") or res.get("input")
                or _host_of(res.get("url", "")))
        if not host or not scope.is_allowed(host):
            continue
        tech = res.get("tech") or []
        if isinstance(tech, list):
            tech = ",".join(tech)
        yield {
            "event": "http.probe",
            "hostname": host,
            "url": res.get("url"),
            "status_code": res.get("status_code"),
            "content_type": res.get("content_type"),
            "title": res.get("title"),
            "webserver": res.get("webserver", ""),
            "tech": tech,
            "location": res.get("location", ""),
        }
        if res.get("url"):
            live_urls.append(res["url"])

    # Fallback: httpx vazio mas DNS resolveu
    if not live_urls and resolved:
        for host in sorted(resolved):
            live_urls.append(f"https://{host}")
            live_urls.append(f"http://{host}")
        yield {"event": "stage.info", "stage": "http",
               "message": f"httpx vazio; fallback gerou {len(live_urls)} URLs sinteticas"}

    yield {"event": "stage.completed", "stage": "http",
           "count": len(live_urls)}

    # ---- 5. directories ----
    dir_count = 0
    if dir_scan and live_urls:
        yield {"event": "stage.started", "stage": "directories",
               "order": STAGE_ORDER["directories"]}

        # Se nao tem wordlist, usa a default do dirsearch
        wl_input = None
        if dir_wordlist_lines:
            wl_input = "\n".join(dir_wordlist_lines)

        for url in live_urls[:20]:
            try:
                results = DirsearchAdapter().execute(
                    target=url,
                    input_data=wl_input,
                    recursion_depth=dir_depth,
                    threads=min(max_rps, 15),
                )
            except Exception as e:
                yield {"event": "stage.info", "stage": "directories",
                       "message": f"{url}: {str(e)[:100]}"}
                continue

            for res in results:
                found_url = res.get("url") or ""
                host = _host_of(found_url)
                if not host or not scope.is_allowed(host):
                    continue
                dir_count += 1
                yield {
                    "event": "directory.found",
                    "hostname": host,
                    "url": found_url,
                    "status_code": res.get("status") or res.get("status_code"),
                    "content_length": (res.get("contentLength")
                                       or res.get("content-length")
                                       or res.get("length")),
                    "content_type": (res.get("contentType")
                                     or res.get("content_type")),
                    "redirect": res.get("redirect") or "",
                    "source": "dirsearch",
                }

        yield {"event": "stage.completed", "stage": "directories",
               "count": dir_count}

    # ---- 6. crawl ----
    crawled_urls = set()
    if crawl and live_urls:
        yield {"event": "stage.started", "stage": "crawl",
               "order": STAGE_ORDER["crawl"]}
        try:
            katana_results = KatanaAdapter().execute(
                input_data="\n".join(live_urls),
                depth=crawl_depth,
                rate_limit=max_rps,
            )
        except Exception as e:
            yield {"event": "stage.failed", "stage": "crawl",
                   "error": str(e)}
            katana_results = []

        for res in katana_results:
            url = (res.get("request", {}).get("endpoint")
                   or res.get("endpoint")
                   or res.get("url"))
            if not url:
                continue
            host = _host_of(url)
            if not host or not scope.is_allowed(host):
                continue
            crawled_urls.add(url)
            yield {
                "event": "endpoint.found",
                "hostname": host,
                "url": url,
                "method": res.get("request", {}).get("method", "GET"),
                "status_code": res.get("response", {}).get("status_code"),
                "content_type": res.get("response", {}).get("content_type"),
                "source": "katana",
            }
        yield {"event": "stage.completed", "stage": "crawl",
               "count": len(crawled_urls)}

    # ---- 7. api ----
    api_hits = set()
    if api_scan:
        yield {"event": "stage.started", "stage": "api",
               "order": STAGE_ORDER["api"]}

        for url in crawled_urls:
            kind = classify_api_endpoint(
                url, {"status_code": 200, "content_type": ""})
            if kind:
                api_hits.add((url, kind, "katana"))

        if wordlist_lines:
            api_paths = list(wordlist_lines)
        else:
            try:
                api_paths = load_api_paths(wordlist)
            except Exception:
                api_paths = []

        if live_urls and api_paths:
            api_targets = live_urls[:5]
            try:
                api_results = HttpxAdapter().execute(
                    input_data="\n".join(api_targets),
                    paths=api_paths,
                    rate_limit=max_rps,
                )
            except Exception as e:
                yield {"event": "stage.info", "stage": "api",
                       "message": f"httpx api falhou: {str(e)[:100]}"}
                api_results = []

            for res in api_results:
                url = res.get("url") or ""
                kind = classify_api_endpoint(url, res)
                if not kind:
                    continue
                api_hits.add((url, kind, "wordlist"))

        for url, kind, source in sorted(api_hits):
            yield {"event": "api.found", "hostname": _host_of(url),
                   "url": url, "kind": kind, "source": source}
        yield {"event": "stage.completed", "stage": "api",
               "count": len(api_hits)}

    # ---- 8. vulns ----
    finding_count = 0
    if vuln_scan and live_urls:
        yield {"event": "stage.started", "stage": "vulns",
               "order": STAGE_ORDER["vulns"]}
        try:
            nuclei_results = NucleiAdapter().execute(
                input_data="\n".join(live_urls[:5]),
                tags=vuln_tags,
                rate_limit=max_rps,
            )
        except Exception as e:
            yield {"event": "stage.failed", "stage": "vulns",
                   "error": str(e)}
            nuclei_results = []

        for res in nuclei_results:
            info = res.get("info", {}) or {}
            classification = info.get("classification", {}) or {}
            sev = (info.get("severity") or "info").lower()
            tid = res.get("template-id") or res.get("templateID") or "unknown"
            matched = res.get("matched-at") or res.get("host") or ""
            host = _host_of(matched)
            if not host or not scope.is_allowed(host):
                continue
            finding_count += 1
            yield {
                "event": "finding.found",
                "hostname": host,
                "url": matched,
                "title": (info.get("name") or tid)[:255],
                "template_id": tid,
                "severity": sev,
                "description": (info.get("description") or "")[:2000],
                "tags": ",".join(info.get("tags", []) or [])[:500],
                "cve": ",".join(classification.get("cve-id", []) or [])[:500],
                "cwe": ",".join(classification.get("cwe-id", []) or [])[:500],
                "reference": ",".join(info.get("reference", []) or [])[:1000],
                "curl_command": (res.get("curl-command") or "")[:2000],
                "matcher": (res.get("matcher-name") or "")[:200],
                "extracted": ",".join(res.get("extracted-results", []) or [])[:500],
                "source": "nuclei",
            }
        yield {"event": "stage.completed", "stage": "vulns",
               "count": finding_count}

    # ---- 9. params ----
    param_count = 0
    if api_scan:
        yield {"event": "stage.started", "stage": "params",
               "order": STAGE_ORDER["params"]}
        seen = set()
        all_urls = (set(live_urls) | crawled_urls
                    | {u for u, _, _ in api_hits})

        for url in list(all_urls)[:500]:
            for pname in extract_query_params(url):
                key = (url, pname, "query")
                if key in seen:
                    continue
                seen.add(key)
                yield {"event": "param.found", "endpoint_url": url,
                       "name": pname, "location": "query"}
                param_count += 1

        html_urls = [u for u in all_urls
                     if not u.endswith((".js", ".json", ".png",
                                        ".jpg", ".css"))]
        for url in html_urls[:form_fetch_limit]:
            html = fetch_html(url)
            if not html:
                continue
            for pname in extract_form_params(html):
                key = (url, pname, "form")
                if key in seen:
                    continue
                seen.add(key)
                yield {"event": "param.found", "endpoint_url": url,
                       "name": pname, "location": "form"}
                param_count += 1
        yield {"event": "stage.completed", "stage": "params",
               "count": param_count}

    yield {"event": "scan.completed", "summary": {
        "subdomains": len(subs),
        "resolved": len(resolved),
        "alive": len(live_urls),
        "crawled": len(crawled_urls),
        "directories": dir_count,
        "api": len(api_hits),
        "vulns": finding_count,
        "params": param_count,
    }}
