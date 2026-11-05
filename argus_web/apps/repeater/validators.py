"""Validacoes de seguranca para o Repeater.

Bloqueia SSRF (localhost, IPs privados, metadata cloud).
"""
import ipaddress
import socket
from urllib.parse import urlparse


BLOCKED_HOSTS = {
    "localhost", "127.0.0.1", "::1", "0.0.0.0",
    "169.254.169.254",  # AWS metadata
    "metadata.google.internal", "metadata",
}

BLOCKED_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),  # link-local
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),  # ULA IPv6
    ipaddress.ip_network("fe80::/10"),  # link-local IPv6
]


class SSRFBlocked(Exception):
    pass


def validate_url(url: str, allow_private: bool = False) -> str:
    """Valida URL contra SSRF. Levanta SSRFBlocked se invalida."""
    if not url:
        raise SSRFBlocked("URL vazia")

    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise SSRFBlocked(f"Protocolo nao permitido: {parsed.scheme}")

    host = parsed.hostname
    if not host:
        raise SSRFBlocked("Hostname vazio")

    host_lower = host.lower()
    if host_lower in BLOCKED_HOSTS:
        raise SSRFBlocked(f"Host bloqueado: {host}")

    if allow_private:
        return url  # bypass explicito (lab mode)

    # Resolve DNS e checa todos os IPs
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        raise SSRFBlocked(f"Nao foi possivel resolver: {host}")

    for info in infos:
        ip_str = info[4][0]
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            continue
        for net in BLOCKED_NETWORKS:
            if ip in net:
                raise SSRFBlocked(
                    f"IP bloqueado: {ip_str} (resolvido de {host})"
                )

    return url
