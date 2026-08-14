"""IP → country resolution for country-gated advertising rules.

The client's country determines which advertising structure the app shows (we
start with UK rules). Resolution order: an explicit override (for testing) →
a private/loopback IP falls back to the configured default (GB) → otherwise a
lookup against the free ip-api.com service. Failures fall back to the default so
the app never breaks on a geo hiccup.
"""

from __future__ import annotations

import ipaddress

import httpx

DEFAULT_CC = "GB"
DEFAULT_NAME = "United Kingdom"
_GEO_URL = "http://ip-api.com/json/{ip}"


def flag_emoji(country_code: str) -> str:
    """Regional-indicator flag emoji for a 2-letter ISO country code."""
    cc = country_code.strip().upper()
    if len(cc) != 2 or not cc.isalpha():
        return "🏳"
    # 'A' (0x41) maps to regional indicator symbol 'A' (0x1F1E6); offset 127397.
    return "".join(chr(ord(ch) + 127397) for ch in cc)


def is_private_ip(ip: str) -> bool:
    """True for loopback/private/invalid addresses — i.e. not geolocatable."""
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return True
    return addr.is_private or addr.is_loopback or addr.is_link_local


def client_ip(forwarded_for: str | None, remote: str | None) -> str:
    """The originating client IP, preferring the first X-Forwarded-For hop (set by
    a proxy/load balancer) over the direct socket peer."""
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return (remote or "").strip()


def ad_policy(country_code: str) -> str:
    """Advertising policy id for a country. Only UK rules exist so far; everything
    else gets the generic (AdSense-only) policy until its rules are added."""
    return "uk" if country_code.upper() == "GB" else "generic"


async def lookup_country(
    ip: str,
    *,
    client: httpx.AsyncClient,
    default_cc: str = DEFAULT_CC,
    default_name: str = DEFAULT_NAME,
) -> tuple[str, str]:
    """Resolve (country_code, country_name) for an IP. Private/loopback IPs and any
    lookup failure fall back to the default (UK)."""
    if is_private_ip(ip):
        return default_cc, default_name
    try:
        resp = await client.get(
            _GEO_URL.format(ip=ip), params={"fields": "status,country,countryCode"}
        )
        data = resp.json()
        if data.get("status") == "success" and data.get("countryCode"):
            return str(data["countryCode"]), str(data.get("country") or data["countryCode"])
    except (httpx.HTTPError, ValueError):
        pass
    return default_cc, default_name
