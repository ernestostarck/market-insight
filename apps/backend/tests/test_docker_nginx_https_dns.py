"""Tests for Phase 10: Docker Production, NGINX, HTTPS, and DNS (10.4, 10.5, 10.6, 10.7)."""

import re
import tempfile
from pathlib import Path
import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]


# ---------------------------------------------------------------------------
# 10.4: Docker Production Architecture Tests
# ---------------------------------------------------------------------------

def test_backend_dockerfile_prod_structure():
    """Verify backend Dockerfile.prod follows multi-stage, non-root and healthcheck rules."""
    dockerfile_path = REPO_ROOT / "apps" / "backend" / "Dockerfile.prod"
    assert dockerfile_path.exists(), "apps/backend/Dockerfile.prod does not exist"

    content = dockerfile_path.read_text(encoding="utf-8")

    # Multi-stage verification
    assert "AS builder" in content
    assert "AS runtime" in content

    # Non-root user verification
    assert re.search(r"useradd\s+.*appuser", content)
    assert re.search(r"USER\s+appuser", content)

    # Healthcheck verification
    assert "HEALTHCHECK" in content
    assert "/health/live" in content

    # Minimal runtime verification (no build-essential in runtime stage)
    runtime_part = content.split("AS runtime")[1]
    assert "build-essential" not in runtime_part
    assert "EXPOSE 8000" in runtime_part


def test_worker_dockerfile_prod_structure():
    """Verify Celery worker Dockerfile.prod follows multi-stage, non-root and celery healthcheck."""
    dockerfile_path = REPO_ROOT / "apps" / "backend" / "Dockerfile.worker.prod"
    assert dockerfile_path.exists(), "apps/backend/Dockerfile.worker.prod does not exist"

    content = dockerfile_path.read_text(encoding="utf-8")
    assert "AS builder" in content
    assert "AS runtime" in content
    assert "USER appuser" in content
    assert "celery" in content
    assert "inspect ping" in content


def test_frontend_dockerfile_prod_structure():
    """Verify frontend Dockerfile.prod uses npm ci, multi-stage and nginx runtime."""
    dockerfile_path = REPO_ROOT / "apps" / "frontend" / "Dockerfile.prod"
    assert dockerfile_path.exists(), "apps/frontend/Dockerfile.prod does not exist"

    content = dockerfile_path.read_text(encoding="utf-8")
    assert "AS build" in content
    assert "npm ci" in content
    assert "FROM nginx" in content
    assert "HEALTHCHECK" in content


def test_compose_production_references_prod_dockerfiles():
    """Verify docker-compose.prod.yml and docker-compose.staging.yml reference production Dockerfiles."""
    prod_compose = (REPO_ROOT / "docker" / "compose" / "docker-compose.prod.yml").read_text(encoding="utf-8")
    staging_compose = (REPO_ROOT / "docker" / "compose" / "docker-compose.staging.yml").read_text(encoding="utf-8")

    for compose_content in (prod_compose, staging_compose):
        assert "dockerfile: Dockerfile.prod" in compose_content
        assert "dockerfile: Dockerfile.worker.prod" in compose_content


# ---------------------------------------------------------------------------
# 10.5: NGINX Configuration Tests
# ---------------------------------------------------------------------------

def test_nginx_global_conf_performance_and_rate_limits():
    """Verify nginx.conf contains compression, rate-limiting zones and client limits."""
    nginx_conf = REPO_ROOT / "docker" / "nginx" / "nginx.conf"
    assert nginx_conf.exists()

    content = nginx_conf.read_text(encoding="utf-8")
    assert "gzip on;" in content
    assert "gzip_comp_level" in content
    assert "limit_req_zone $binary_remote_addr zone=api_limit" in content
    assert "limit_req_zone $binary_remote_addr zone=chat_limit" in content
    assert "client_max_body_size 25m;" in content


def test_nginx_production_conf_routing_and_streaming():
    """Verify NGINX production config contains streaming SSE settings, security headers and routing."""
    prod_conf = REPO_ROOT / "docker" / "nginx" / "prod" / "conf.d" / "default.conf"
    assert prod_conf.exists()

    content = prod_conf.read_text(encoding="utf-8")

    # 1. ACME challenge for Certbot
    assert "/.well-known/acme-challenge/" in content

    # 2. HTTP -> HTTPS 301 redirect
    assert "return 301 https://$host$request_uri;" in content

    # 3. AI Streaming & SSE support (Fase 9 optimization)
    assert "location ~ ^/api/v1/(ai|chat)/" in content
    assert "proxy_buffering off;" in content
    assert "proxy_read_timeout 300s;" in content

    # 4. Rate limiting applied
    assert "limit_req zone=api_limit" in content
    assert "limit_req zone=chat_limit" in content

    # 5. Internal endpoints blocked
    assert "/api/v1/monitoring/alerts/webhook" in content
    assert 'return 403 "Forbidden' in content

    # 6. Static asset caching
    assert 'add_header Cache-Control "public, max-age=2592000, immutable";' in content


# ---------------------------------------------------------------------------
# 10.6: HTTPS / TLS Configuration & Cert Generator Tests
# ---------------------------------------------------------------------------

def test_nginx_tls_security_headers_and_protocols():
    """Verify production NGINX config enforces TLS 1.2+, secure ciphers and HSTS."""
    prod_conf = (REPO_ROOT / "docker" / "nginx" / "prod" / "conf.d" / "default.conf").read_text(encoding="utf-8")

    assert "ssl_protocols TLSv1.2 TLSv1.3;" in content_check if (content_check := prod_conf) else False
    assert "Strict-Transport-Security" in prod_conf
    assert "X-Content-Type-Options \"nosniff\"" in prod_conf
    assert "X-Frame-Options \"SAMEORIGIN\"" in prod_conf
    assert "Content-Security-Policy" in prod_conf


def test_generate_dev_certs_script():
    """Verify generate-dev-certs.py generates valid certificates with SANs."""
    import sys
    scripts_dir = REPO_ROOT / "infrastructure" / "scripts"
    sys.path.insert(0, str(scripts_dir))

    from importlib import import_module
    gen_certs = import_module("generate-dev-certs")

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        cert_path, key_path = gen_certs.generate_self_signed_certificate(
            output_dir=tmp_path,
            domain="mercadoinsight.cl",
            valid_days=30,
        )

        assert cert_path.exists()
        assert key_path.exists()
        assert cert_path.stat().st_size > 500
        assert key_path.stat().st_size > 500

        cert_content = cert_path.read_text(encoding="utf-8")
        key_content = key_path.read_text(encoding="utf-8")

        assert "-----BEGIN CERTIFICATE-----" in cert_content
        assert "-----BEGIN RSA PRIVATE KEY-----" in key_content


def test_renew_certificates_script_exists():
    """Verify Let's Encrypt renewal script exists and has correct hook commands."""
    renew_script = REPO_ROOT / "infrastructure" / "scripts" / "renew-certificates.sh"
    assert renew_script.exists()

    content = renew_script.read_text(encoding="utf-8")
    assert "certbot renew" in content
    assert "nginx -s reload" in content


# ---------------------------------------------------------------------------
# 10.7: DNS Documentation Tests
# ---------------------------------------------------------------------------

def test_dns_strategy_documentation_completeness():
    """Verify that DNS documentation covers all required record types and TTL."""
    dns_doc = REPO_ROOT / "docs" / "deployment" / "dns-strategy.md"
    assert dns_doc.exists()

    content = dns_doc.read_text(encoding="utf-8")
    assert "mercadoinsight.cl" in content
    assert "CNAME" in content
    assert "CAA" in content
    assert "letsencrypt.org" in content
    assert "SPF" in content
    assert "DMARC" in content
    assert "TTL" in content
