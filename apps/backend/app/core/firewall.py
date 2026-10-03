"""Application firewall (WAF) and HTTP security headers.

FirewallMiddleware, in order, for every HTTP request:
  1. IP allowlist / denylist (CIDR) and temporary bans (Redis, shared across workers).
  2. Host header validation and HTTP method allowlist.
  3. Attack-signature inspection of the path, query string and User-Agent
     (SQL injection, XSS, path traversal, SSRF/Log4Shell, template injection,
     known vulnerability scanners).
  4. Request-body size cap, enforced on Content-Length *and* while streaming.
  5. Strike counting: blocked, 401, 403 and 429 responses add strikes to the client
     IP; reaching FIREWALL_BAN_THRESHOLD within 10 minutes bans it temporarily.

It is defence in depth on top of parameterised SQL and output encoding, not a
replacement: deploy an edge WAF / CDN in front of it in production as well.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from urllib.parse import unquote_plus

import redis.asyncio as redis
from starlette.datastructures import Headers
from starlette.requests import HTTPConnection
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.client_ip import client_ip, ip_in, parse_networks
from app.core.settings import get_settings

logger = logging.getLogger("app.security.firewall")

_ALLOWED_METHODS = {"GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"}
_UPLOAD_PATH_PREFIXES = ("/api/v1/documents",)
_STRIKE_STATUSES = {401, 403, 429}
_STRIKE_WINDOW_SECONDS = 600

# (rule id, compiled pattern) — matched against the URL-decoded path + query string.
_SIGNATURES: tuple[tuple[str, re.Pattern[str]], ...] = tuple(
    (rule, re.compile(pattern, re.IGNORECASE))
    for rule, pattern in (
        ("sqli_union", r"\bunion\b[\s/*+]+(all[\s/*+]+)?select\b"),
        ("sqli_tautology", r"['\"]\s*(or|and)\s+['\"]?\w+['\"]?\s*=\s*['\"]?\w+"),
        ("sqli_comment", r"(['\"]\s*;|;\s*)(drop|delete|insert|update|alter|truncate|exec)\b"),
        ("sqli_functions", r"\b(sleep|benchmark|pg_sleep|waitfor\s+delay|load_file|xp_cmdshell)\s*\("),
        ("sqli_catalog", r"\b(information_schema|pg_catalog|pg_shadow|sysobjects)\b"),
        ("xss_script", r"<\s*/?\s*(script|iframe|object|embed|svg|img)\b"),
        ("xss_handler", r"\bon(error|load|mouseover|focus|click)\s*="),
        ("xss_scheme", r"(javascript|vbscript|data:text/html)\s*:"),
        ("path_traversal", r"(\.\./|\.\.\\|%2e%2e|%252e)"),
        ("null_byte", r"%00|\x00"),
        ("sensitive_files", r"(/etc/passwd|/proc/self|\.env\b|\.git/|wp-admin|wp-login|phpmyadmin)"),
        ("log4shell", r"\$\{\s*(jndi|env|sys|lower|upper)\s*:"),
        ("template_injection", r"\{\{.*\}\}|\{%.*%\}"),
        ("command_injection", r"(;|\|\||&&|`|\$\()\s*(cat|curl|wget|bash|sh|nc|python|powershell)\b"),
        ("ssrf_metadata", r"169\.254\.169\.254|metadata\.google\.internal"),
    )
)
_SCANNER_AGENTS = re.compile(
    r"sqlmap|nikto|nmap|masscan|acunetix|nessus|openvas|dirbuster|gobuster|wpscan|zgrab|"
    r"nuclei|havij|w3af|arachni|fimap|hydra",
    re.IGNORECASE,
)


def inspect_request(path: str, query: str, user_agent: str) -> str | None:
    """Rule id of the first matching attack signature, or None."""
    if _SCANNER_AGENTS.search(user_agent or ""):
        return "scanner_user_agent"
    target = path
    if query:
        # Decode twice: double-encoded payloads (%253C) are a classic WAF bypass.
        target = f"{path}?{unquote_plus(unquote_plus(query))}"
    for rule, pattern in _SIGNATURES:
        if pattern.search(target):
            return rule
    return None


def _json_response(status: int, code: str, message: str) -> tuple[Message, Message]:
    body = json.dumps({"error": {"code": code, "message": message}}).encode()
    start = {
        "type": "http.response.start",
        "status": status,
        "headers": [
            (b"content-type", b"application/json"),
            (b"content-length", str(len(body)).encode()),
            (b"cache-control", b"no-store"),
        ],
    }
    return start, {"type": "http.response.body", "body": body}


class _BodyTooLarge(Exception):
    pass


class FirewallMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        settings = get_settings()
        self.enabled = settings.firewall_enabled
        self.allowlist = parse_networks(settings.firewall_ip_allowlist)
        self.denylist = parse_networks(settings.firewall_ip_denylist)
        self.allowed_hosts = [h.lower() for h in settings.allowed_hosts_list]
        self.ban_threshold = settings.firewall_ban_threshold
        self.ban_seconds = settings.firewall_ban_seconds
        # Locally every request comes from loopback: never auto-ban the developer's own machine.
        self.never_ban = parse_networks("127.0.0.0/8,::1") if settings.is_development else ()
        self.max_body = settings.max_request_body_bytes
        self.max_upload = settings.max_upload_body_bytes
        self._redis = redis.from_url(
            settings.redis_url, decode_responses=True, socket_connect_timeout=0.3, socket_timeout=0.3
        )

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not self.enabled:
            await self.app(scope, receive, send)
            return

        connection = HTTPConnection(scope)
        ip = client_ip(connection)
        headers = Headers(scope=scope)
        path = scope.get("path", "")
        query = scope.get("query_string", b"").decode("latin-1")

        reason = await self._reject_reason(ip, headers, scope["method"], path, query)
        if reason is not None:
            status, code, message, rule = reason
            if rule:
                await self._strike(ip, connection, rule=rule, path=path)
            start, body = _json_response(status, code, message)
            await send(start)
            await send(body)
            return

        limit = self.max_upload if path.startswith(_UPLOAD_PATH_PREFIXES) else self.max_body
        declared = headers.get("content-length")
        if declared and declared.isdigit() and int(declared) > limit:
            start, body = _json_response(413, "PAYLOAD_TOO_LARGE", "La solicitud supera el tamaño permitido.")
            await send(start)
            await send(body)
            return

        received = 0

        async def limited_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > limit:
                    raise _BodyTooLarge
            return message

        response_started = False
        status_code = 0

        async def tracking_send(message: Message) -> None:
            nonlocal response_started, status_code
            if message["type"] == "http.response.start":
                response_started = True
                status_code = message["status"]
            await send(message)

        try:
            await self.app(scope, limited_receive, tracking_send)
        except _BodyTooLarge:
            if not response_started:
                start, body = _json_response(413, "PAYLOAD_TOO_LARGE", "La solicitud supera el tamaño permitido.")
                await send(start)
                await send(body)
            return

        if status_code in _STRIKE_STATUSES:
            # Fire-and-forget: counting strikes must not add latency to the response.
            asyncio.ensure_future(self._strike(ip, connection, rule=f"http_{status_code}", path=path, audit=False))

    async def _reject_reason(
        self, ip: str, headers: Headers, method: str, path: str, query: str
    ) -> tuple[int, str, str, str | None] | None:
        if self.allowlist and not ip_in(ip, self.allowlist):
            return 403, "IP_NOT_ALLOWED", "Acceso no permitido desde esta dirección.", None
        if self.denylist and ip_in(ip, self.denylist):
            return 403, "IP_DENIED", "Acceso no permitido desde esta dirección.", None
        if await self._is_banned(ip):
            return 403, "IP_TEMPORARILY_BANNED", "Acceso bloqueado temporalmente por actividad sospechosa.", None
        if "*" not in self.allowed_hosts:
            host = (headers.get("host") or "").split(":")[0].lower()
            if host not in self.allowed_hosts:
                return 400, "INVALID_HOST", "Host no permitido.", None
        if method.upper() not in _ALLOWED_METHODS:
            return 405, "METHOD_NOT_ALLOWED", "Método HTTP no permitido.", "method_not_allowed"
        if len(path) > 2048 or len(query) > 4096:
            return 414, "URI_TOO_LONG", "La URL es demasiado larga.", "uri_too_long"
        rule = inspect_request(path, query, headers.get("user-agent", ""))
        if rule is not None:
            return 403, "REQUEST_BLOCKED", "La solicitud fue bloqueada por el firewall de la aplicación.", rule
        return None

    async def _is_banned(self, ip: str) -> bool:
        try:
            return bool(await self._redis.exists(f"fw_ban:{ip}"))
        except Exception:
            return False

    async def _strike(self, ip: str, connection: HTTPConnection, *, rule: str, path: str, audit: bool = True) -> None:
        # Imported lazily: the audit service pulls in the DB layer.
        from app.services import security_audit

        if audit:
            logger.warning("firewall blocked %s on %s (%s)", ip, path, rule)
            await security_audit.record(
                security_audit.FIREWALL_BLOCK, request=connection, success=False, detail={"rule": rule, "path": path[:300]}
            )
        try:
            key = f"fw_strikes:{ip}:{int(time.time()) // _STRIKE_WINDOW_SECONDS}"
            strikes = await self._redis.incr(key)
            if strikes == 1:
                await self._redis.expire(key, _STRIKE_WINDOW_SECONDS)
            if strikes == self.ban_threshold and not ip_in(ip, self.never_ban):
                await self._redis.set(f"fw_ban:{ip}", rule, ex=self.ban_seconds)
                logger.warning("firewall banned %s for %ss after %s strikes", ip, self.ban_seconds, strikes)
                await security_audit.record(
                    security_audit.IP_BANNED, request=connection, success=False,
                    detail={"strikes": strikes, "last_rule": rule, "ban_seconds": self.ban_seconds},
                )
        except Exception:
            return


_API_CSP = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"
# Swagger/ReDoc pages load their bundle from jsdelivr and need inline bootstrapping.
_DOCS_CSP = (
    "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
    "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; img-src 'self' data: https://fastapi.tiangolo.com; "
    "frame-ancestors 'none'; base-uri 'none'"
)
_DOCS_PATHS = ("/docs", "/redoc")


class SecurityHeadersMiddleware:
    """OWASP-recommended response headers on every HTTP response."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        self.hsts = not get_settings().is_development

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        path = scope.get("path", "")
        csp = _DOCS_CSP if path.startswith(_DOCS_PATHS) else _API_CSP

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = [(k, v) for k, v in message.get("headers", []) if k.lower() != b"server"]
                existing = {k.lower() for k, _ in headers}
                extra = {
                    b"x-content-type-options": b"nosniff",
                    b"x-frame-options": b"DENY",
                    b"referrer-policy": b"no-referrer",
                    b"content-security-policy": csp.encode(),
                    b"permissions-policy": b"camera=(), microphone=(), geolocation=(), payment=(), usb=()",
                    b"cross-origin-opener-policy": b"same-origin",
                    b"cross-origin-resource-policy": b"same-origin",
                    b"x-permitted-cross-domain-policies": b"none",
                }
                if path.startswith("/api/") and b"cache-control" not in existing:
                    extra[b"cache-control"] = b"no-store"
                if self.hsts:
                    extra[b"strict-transport-security"] = b"max-age=63072000; includeSubDomains; preload"
                headers.extend((k, v) for k, v in extra.items() if k not in existing)
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_with_headers)
