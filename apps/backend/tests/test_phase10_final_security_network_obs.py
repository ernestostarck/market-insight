"""Tests for Phase 10: RPO/RTO, Final Observability, AI Cost Monitoring, Security Audit, and Network Architecture (10.16 to 10.20)."""

import sys
from pathlib import Path
import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
DOCS_DIR = REPO_ROOT / "docs" / "deployment"
SCRIPTS_DIR = REPO_ROOT / "infrastructure" / "scripts"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import importlib.util
spec = importlib.util.spec_from_file_location("security_audit", str(SCRIPTS_DIR / "security-audit.py"))
security_audit = importlib.util.module_from_spec(spec)
sys.modules["security_audit"] = security_audit
spec.loader.exec_module(security_audit)

from app.ai.cost_tracker import (
    MODEL_PRICING_CATALOG,
    CostTracker,
)


# ---------------------------------------------------------------------------
# 10.16: RPO / RTO Tests
# ---------------------------------------------------------------------------

def test_rpo_rto_documentation_completeness():
    """Verify docs/deployment/rpo-rto.md defines RTO/RPO with technical derivations and simulation."""
    doc_path = DOCS_DIR / "rpo-rto.md"
    assert doc_path.exists(), "docs/deployment/rpo-rto.md does not exist"

    content = doc_path.read_text(encoding="utf-8")
    assert "RPO (Recovery Point Objective)" in content
    assert "RTO (Recovery Time Objective)" in content
    assert "ChileCompra" in content
    assert "WAL" in content
    assert "SLA" in content
    assert "Supuestos de Infraestructura" in content
    assert "Simulación de RTO" in content


# ---------------------------------------------------------------------------
# 10.17: Final Observability & 10.18: AI Cost Monitoring Tests
# ---------------------------------------------------------------------------

def test_ai_cost_prometheus_rules():
    """Verify docker/monitoring/prometheus/rules/ai-cost.yml is valid YAML and has expected alerts."""
    rules_path = REPO_ROOT / "docker" / "monitoring" / "prometheus" / "rules" / "ai-cost.yml"
    assert rules_path.exists(), "ai-cost.yml rule file does not exist"

    with open(rules_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    assert "groups" in data
    group = data["groups"][0]
    rule_names = [r["alert"] for r in group.get("rules", [])]

    assert "AICostSpikeDaily" in rule_names
    assert "AIHighTokenConsumptionRate" in rule_names
    assert "AIGroundingFailureRateHigh" in rule_names
    assert "AICostlyQueriesSpike" in rule_names


def test_ai_cost_tracker_calculation_and_anomaly_detection():
    """Verify CostTracker calculates USD expenditure and flags anomalies correctly."""
    tracker = CostTracker()
    # 1,000,000 input tokens = $0.075, 1,000,000 output tokens = $0.30 -> Total $0.375
    cost_usd = tracker.calculate_cost("gemini-2.5-flash", tokens_input=1_000_000, tokens_output=1_000_000)
    assert abs(cost_usd - 0.375) < 1e-4

    # Normal query
    rec_normal = tracker.record_query_cost(
        query_id="q-normal-1",
        model="gemini-2.5-flash",
        intent="tender_analysis",
        tokens_input=500,
        tokens_output=200,
    )
    assert not rec_normal.is_anomalous
    assert rec_normal.cost_usd > 0

    # Anomalous query exceeding max tokens threshold
    rec_anomalous = tracker.record_query_cost(
        query_id="q-huge-1",
        model="gemini-1.5-pro",
        intent="multi_document_synthesis",
        tokens_input=20_000,
        tokens_output=4_000,
    )
    assert rec_anomalous.is_anomalous, "Query exceeding 8,000 tokens should be flagged as anomalous"


def test_observability_and_cost_documentation():
    """Verify docs/deployment/observability-final.md and ai-cost-monitoring.md exist and cover requirements."""
    obs_doc = DOCS_DIR / "observability-final.md"
    assert obs_doc.exists()
    obs_content = obs_doc.read_text(encoding="utf-8")
    assert "Prometheus" in obs_content
    assert "Grafana" in obs_content
    assert "Loki" in obs_content
    assert "Sentry" in obs_content
    assert "OpenTelemetry" in obs_content
    assert "rag-monitoring.json" in obs_content

    cost_doc = DOCS_DIR / "ai-cost-monitoring.md"
    assert cost_doc.exists()
    cost_content = cost_doc.read_text(encoding="utf-8")
    assert "gemini-2.5-flash" in cost_content
    assert "QueryCostRecord" in cost_content
    assert "AICostSpikeDaily" in cost_content
    assert "Grafana" in cost_content


# ---------------------------------------------------------------------------
# 10.19: Final Security Audit Tests
# ---------------------------------------------------------------------------

def test_automated_security_audit_script():
    """Verify security-audit.py runs cleanly and passes all hardening checks."""
    report = security_audit.run_security_audit()
    assert report.checks_failed == 0, f"Security audit failed with issues: {report.failures}"
    assert report.checks_passed >= 7


def test_security_audit_documentation():
    """Verify docs/deployment/security-audit.md contains the 18-point checklist and audit results."""
    doc_path = DOCS_DIR / "security-audit.md"
    assert doc_path.exists()

    content = doc_path.read_text(encoding="utf-8")
    assert "Checklist Integral de Seguridad" in content
    assert "HTTPS Obligatorio" in content
    assert "SQL Read-Only para IA" in content
    assert "security-audit.py" in content
    assert "Matriz de Exposición de Puertos" in content


# ---------------------------------------------------------------------------
# 10.20: Network Architecture Tests
# ---------------------------------------------------------------------------

class ComposeLoader(yaml.SafeLoader):
    pass

ComposeLoader.add_constructor(
    "!reset",
    lambda loader, node: loader.construct_sequence(node) if isinstance(node, yaml.SequenceNode) else None,
)
ComposeLoader.add_constructor(
    "!override",
    lambda loader, node: (
        loader.construct_sequence(node)
        if isinstance(node, yaml.SequenceNode)
        else loader.construct_mapping(node)
        if isinstance(node, yaml.MappingNode)
        else None
    ),
)


def _load_compose(filepath: Path) -> dict:
    assert filepath.exists(), f"Compose file {filepath} not found"
    with open(filepath, "r", encoding="utf-8") as f:
        return yaml.load(f, Loader=ComposeLoader)


def test_network_isolation_in_docker_compose_prod_and_staging():
    """Verify production and staging compose enforce two-tier public-net and private-net isolation."""
    for comp_name in ["docker-compose.prod.yml", "docker-compose.staging.yml"]:
        comp_path = REPO_ROOT / "docker" / "compose" / comp_name
        data = _load_compose(comp_path)

        # 1. Networks definition
        networks = data.get("networks", {})
        assert "public-net" in networks, f"{comp_name} missing 'public-net'"
        assert "private-net" in networks, f"{comp_name} missing 'private-net'"

        services = data.get("services", {})

        # 2. Public only services
        assert "public-net" in services["nginx"]["networks"]
        assert "private-net" not in services["nginx"]["networks"]

        assert "public-net" in services["frontend"]["networks"]
        assert "private-net" not in services["frontend"]["networks"]

        # 3. Bridge services (connected to both)
        backend_nets = services["backend"]["networks"]
        assert "public-net" in backend_nets and "private-net" in backend_nets

        # 4. Strictly private services (must NOT be in public-net)
        private_only_services = [
            "postgres",
            "redis",
            "minio",
            "nlp-worker",
            "etl-worker",
            "etl-beat",
            "prometheus",
            "loki",
            "promtail",
        ]
        for svc in private_only_services:
            assert svc in services, f"{comp_name} missing service {svc}"
            svc_nets = services[svc].get("networks", [])
            assert "private-net" in svc_nets, f"{svc} in {comp_name} not attached to private-net"
            assert "public-net" not in svc_nets, f"{svc} in {comp_name} should NOT be in public-net"


def test_network_architecture_documentation():
    """Verify docs/deployment/network-architecture.md documents the two-tier topology and minimal exposure."""
    doc_path = DOCS_DIR / "network-architecture.md"
    assert doc_path.exists()

    content = doc_path.read_text(encoding="utf-8")
    assert "public-net" in content
    assert "private-net" in content
    assert "NGINX" in content
    assert "PostgreSQL" in content
    assert "Principio de Mínima Exposición de Puertos" in content


def test_deployment_guide_references_phase10_all_docs():
    """Verify DEPLOYMENT.md references all documents from 10.16 to 10.20."""
    deploy_md = REPO_ROOT / "DEPLOYMENT.md"
    assert deploy_md.exists()

    content = deploy_md.read_text(encoding="utf-8")
    assert "docs/deployment/rpo-rto.md" in content
    assert "docs/deployment/observability-final.md" in content
    assert "docs/deployment/ai-cost-monitoring.md" in content
    assert "docs/deployment/security-audit.md" in content
    assert "docs/deployment/network-architecture.md" in content
