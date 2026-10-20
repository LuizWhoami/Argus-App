import re
from typing import Dict, List, Optional
from urllib.parse import urlparse, parse_qs

import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

FORM_RE = re.compile(r"<form[^>]*>(.*?)</form>", re.IGNORECASE | re.DOTALL)
NAME_RE = re.compile(r'<input[^>]*name=["\']([^"\']+)["\']', re.IGNORECASE)
SELECT_RE = re.compile(r'<select[^>]*name=["\']([^"\']+)["\']', re.IGNORECASE)
TEXTAREA_RE = re.compile(r'<textarea[^>]*name=["\']([^"\']+)["\']', re.IGNORECASE)


def extract_query_params(url: str) -> List[str]:
    try:
        return list(parse_qs(urlparse(url).query).keys())
    except Exception:
        return []


def extract_form_params(html: str) -> List[str]:
    params = set()
    for form in FORM_RE.findall(html):
        for regex in (NAME_RE, SELECT_RE, TEXTAREA_RE):
            params.update(regex.findall(form))
    return sorted(params)


def fetch_html(url: str, timeout: int = 10) -> Optional[str]:
    try:
        r = requests.get(
            url,
            timeout=timeout,
            verify=False,
            allow_redirects=True,
            headers={"User-Agent": "bounty-agent/0.2 (+authorized-testing)"},
        )
        ctype = r.headers.get("Content-Type", "").lower()
        if r.status_code == 200 and "text/html" in ctype:
            return r.text
    except Exception:
        return None
    return None


def collect_params(url: str, fetch: bool = False) -> Dict[str, List[str]]:
    """
    Retorna {'query': [...], 'form': [...]}.
    Se fetch=True, baixa o HTML e extrai formulários.
    """
    query = extract_query_params(url)
    form: List[str] = []
    if fetch:
        html = fetch_html(url)
        if html:
            form = extract_form_params(html)
    return {"query": query, "form": form}
