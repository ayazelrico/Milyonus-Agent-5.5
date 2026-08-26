"""SSRF protection (PLAN §6 layer 6).

Always on, fail-closed, cannot be disabled from config. Blocks requests to
private, loopback, link-local (incl. the cloud metadata address
169.254.169.254), CGNAT ranges, and known cloud-metadata hostnames. DNS failure
counts as blocked. Redirect chains must be re-validated at every hop by the
caller (the web tool passes each resolved URL back through `check_url`).
"""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

_METADATA_HOSTS = {
    "metadata.google.internal",
    "metadata.goog",
    "169.254.169.254",
    "metadata",
}

_BLOCKED_SCHEMES = {"file", "gopher", "ftp", "data", "dict"}


class SSRFBlocked(Exception):
    """Raised when a URL targets a disallowed destination."""


def _ip_is_blocked(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    if (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    ):
        return True
    # CGNAT 100.64.0.0/10.
    return isinstance(ip, ipaddress.IPv4Address) and ip in ipaddress.ip_network("100.64.0.0/10")


def check_url(url: str) -> str:
    """Validate a URL. Return it if allowed; raise SSRFBlocked otherwise."""
    parsed = urlparse(url)
    scheme = (parsed.scheme or "").lower()
    if scheme in _BLOCKED_SCHEMES:
        raise SSRFBlocked(f"izin verilmeyen şema: {scheme}")
    if scheme not in ("http", "https"):
        raise SSRFBlocked(f"sadece http/https: {scheme or '(yok)'}")
    host = parsed.hostname
    if not host:
        raise SSRFBlocked("host yok")
    if host.lower() in _METADATA_HOSTS:
        raise SSRFBlocked(f"bulut metadata host'u engellendi: {host}")

    # Resolve and check every returned address. DNS failure => blocked.
    try:
        infos = socket.getaddrinfo(host, parsed.port or (443 if scheme == "https" else 80))
    except socket.gaierror as exc:
        raise SSRFBlocked(f"DNS çözülemedi (fail-closed): {host}") from exc
    for info in infos:
        addr = str(info[4][0])
        try:
            ip = ipaddress.ip_address(addr.split("%")[0])
        except ValueError:
            raise SSRFBlocked(f"IP ayrıştırılamadı: {addr}") from None
        if _ip_is_blocked(ip):
            raise SSRFBlocked(f"özel/dahili adres engellendi: {ip}")
    return url
