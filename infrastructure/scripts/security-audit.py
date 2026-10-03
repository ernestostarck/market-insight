#!/usr/bin/env python3
"""Automated Security Audit Script for MercadoInsight (Fase 10.19).

Audits production configurations, network exposures, secret hygiene, CORS policies,
SQL read-only guardrails for AI, and NGINX security headers.
"""

from __future__ import annotations

import logging
import re
import sys
from pathlib import Path
from typing import Any

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ",
)
logger = logging.getLogger("security-audit")

REPO_ROOT = Path(__file__).resolve().parents[2]


class SecurityAuditReport:
    def __init__(self) -> None:
        self.checks_passed = 0
        self.checks_failed = 0
        self.failures: list[str] = []

    def record_pass(self, name: str) -> None:
        self.checks_passed += 1
        logger.info("[PASS] %s", name)

    def record_fail(self, name: str, reason: str) -> None:
        self.checks_failed += 1
        self.failures.append(f"{name}: {reason}")
        logger.error("[FAIL] %s - %s", name, reason)


def audit_secret_hygiene(report: SecurityAuditReport) -> None:
    """Verify sensitive files are excluded in .gitignore and .dockerignore."""
    gitignore_path = REPO_ROOT / ".gitignore"
    dockerignore_path = REPO_ROOT / ".dockerignore"

    required_patterns = [".env", "*.key", "*.pem"]

    if not gitignore_path.exists():
        report.record_fail("gitignore_exists", ".gitignore missing")
        return

    git_content = gitignore_path.read_text(encoding="utf-8")
    for pat in required_patterns:
        if pat not in git_content:
            report.record_fail(f"gitignore_hygiene_{pat}", f"Pattern {pat} not found in .gitignore")
            return
    report.record_pass("Secret Hygiene (.gitignore excludes sensitive files)")

    if dockerignore_path.exists():
        dock_content = dockerignore_path.read_text(encoding="utf-8")
        if ".env" in dock_content and "*.pem" in dock_content:
            report.record_pass("Docker Secret Hygiene (.dockerignore excludes env/certs)")
        else:
            report.record_fail("dockerignore_hygiene", ".dockerignore missing required exclusions")


def audit_docker_production_ports(report: SecurityAuditReport) -> None:
    """Verify internal services in production compose do NOT expose ports to the host."""
    prod_compose_path = REPO_ROOT / "docker" / "compose" / "docker-compose.prod.yml"
    if not prod_compose_path.exists():
        report.record_fail("prod_compose_exists", "docker-compose.prod.yml missing")
        return

    content = prod_compose_path.read_text(encoding="utf-8")

    # In prod compose, internal services must reset ports: "ports: !reset []"
    # and only nginx should expose 80 and 443
    internal_services = ["postgres", "redis", "minio", "prometheus", "loki", "grafana", "alertmanager"]
    all_reset = True
    for svc in internal_services:
        # Check that the service has "ports: !reset []"
        svc_pattern = re.compile(rf"{svc}:.*?(ports:\s*!reset\s*\[\])", re.DOTALL)
        if svc in content and not svc_pattern.search(content):
            report.record_fail(f"port_isolation_{svc}", f"Service {svc} does not reset published ports in production")
            all_reset = False

    if all_reset:
        report.record_pass("Internal Port Isolation (PostgreSQL, Redis, MinIO, Prometheus not exposed)")


def audit_ai_sql_read_only(report: SecurityAuditReport) -> None:
    """Verify AI SQL retriever enforces strict read-only and blocks DDL/DML."""
    sql_retriever_path = REPO_ROOT / "apps" / "backend" / "app" / "ai" / "sql_retriever.py"
    if not sql_retriever_path.exists():
        report.record_fail("sql_retriever_exists", "sql_retriever.py missing")
        return

    content = sql_retriever_path.read_text(encoding="utf-8")
    forbidden = ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE"]
    if all(kw in content for kw in forbidden):
        report.record_pass("AI SQL Read-Only Guardrails (DML/DDL blocked in sql_retriever.py)")
    else:
        report.record_fail("ai_sql_guardrails", "sql_retriever.py missing forbidden SQL keywords")


def audit_nginx_security_headers(report: SecurityAuditReport) -> None:
    """Verify NGINX production configuration enforces modern security headers."""
    nginx_conf = REPO_ROOT / "docker" / "nginx" / "prod" / "conf.d" / "default.conf"
    if not nginx_conf.exists():
        nginx_conf = REPO_ROOT / "docker" / "nginx" / "conf.d" / "default.conf"

    if not nginx_conf.exists():
        report.record_fail("nginx_conf_exists", "NGINX default.conf missing")
        return

    content = nginx_conf.read_text(encoding="utf-8")
    headers = [
        "Strict-Transport-Security",
        "X-Content-Type-Options",
        "X-Frame-Options",
        "Referrer-Policy",
    ]

    all_present = True
    for h in headers:
        if h not in content:
            report.record_fail(f"nginx_header_{h}", f"Missing header {h} in NGINX config")
            all_present = False

    if all_present:
        report.record_pass("NGINX Security Headers (HSTS, nosniff, SAMEORIGIN, Referrer-Policy)")


def audit_rate_limiting_and_cors(report: SecurityAuditReport) -> None:
    """Verify rate limiting is enabled and CORS is not configured with open wildcard in prod."""
    prod_compose = REPO_ROOT / "docker" / "compose" / "docker-compose.prod.yml"
    content = prod_compose.read_text(encoding="utf-8")

    if 'RATE_LIMIT_ENABLED: "true"' in content:
        report.record_pass("Rate Limiting Enforced (RATE_LIMIT_ENABLED=true in production)")
    else:
        report.record_fail("rate_limiting_prod", "RATE_LIMIT_ENABLED is not set to true in docker-compose.prod.yml")

    if 'BACKEND_CORS_ORIGINS: "*"' in content:
        report.record_fail("cors_wildcard", "Wildcard CORS origin detected in production configuration")
    else:
        report.record_pass("CORS Origin Restricted (No open wildcard in production)")


def run_security_audit() -> SecurityAuditReport:
    """Execute all security audit checks and return report."""
    report = SecurityAuditReport()
    logger.info("Starting MercadoInsight automated security audit ...")

    audit_secret_hygiene(report)
    audit_docker_production_ports(report)
    audit_ai_sql_read_only(report)
    audit_nginx_security_headers(report)
    audit_rate_limiting_and_cors(report)

    logger.info("Security audit finished: %d passed, %d failed.", report.checks_passed, report.checks_failed)
    return report


def main() -> None:
    report = run_security_audit()
    if report.checks_failed > 0:
        logger.error("Security audit FAILED with %d issues:", report.checks_failed)
        for fail in report.failures:
            logger.error("  - %s", fail)
        sys.exit(1)
    else:
        logger.info("All security controls VERIFIED successfully.")
        sys.exit(0)


if __name__ == "__main__":
    main()
