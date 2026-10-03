"""Real client IP resolution that can't be spoofed with a forged X-Forwarded-For."""

from __future__ import annotations

import ipaddress
from functools import lru_cache

from starlette.requests import HTTPConnection

from app.core.settings import get_settings


@lru_cache(maxsize=1)
def _trusted_proxies() -> tuple[ipaddress.IPv4Network | ipaddress.IPv6Network, ...]:
    return parse_networks(get_settings().trusted_proxies)


def parse_networks(value: str) -> tuple[ipaddress.IPv4Network | ipaddress.IPv6Network, ...]:
    networks = []
    for item in value.split(","):
        item = item.strip()
        if not item:
            continue
        try:
            networks.append(ipaddress.ip_network(item, strict=False))
        except ValueError:
            continue
    return tuple(networks)


def ip_in(ip: str, networks: tuple[ipaddress.IPv4Network | ipaddress.IPv6Network, ...]) -> bool:
    try:
        address = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return any(address in network for network in networks)


def client_ip(request: HTTPConnection) -> str:
    """The peer address, or — only when the peer is a trusted proxy — the right-most
    X-Forwarded-For hop that isn't itself a trusted proxy."""
    peer = request.client.host if request.client else "unknown"
    if not ip_in(peer, _trusted_proxies()):
        return peer
    forwarded = request.headers.get("x-forwarded-for", "")
    for hop in reversed([h.strip() for h in forwarded.split(",") if h.strip()]):
        if not ip_in(hop, _trusted_proxies()):
            try:
                return str(ipaddress.ip_address(hop))
            except ValueError:
                return peer
    return peer
