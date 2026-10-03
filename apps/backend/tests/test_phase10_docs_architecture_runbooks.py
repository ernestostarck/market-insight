"""
Test Suite: Phase 10 Subphases 10.21 - 10.25 Verification
Validates technical documentation structure, README portal completeness,
C4 Model architecture diagrams, OpenAPI specifications, and incident troubleshooting runbooks.
"""

import os
import re
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent


def test_technical_documentation_files_exist():
    """10.21: Verify that all expected technical documentation files exist in docs/."""
    expected_files = [
        # Architecture
        "docs/architecture/overview.md",
        "docs/architecture/backend.md",
        "docs/architecture/frontend.md",
        "docs/architecture/database.md",
        "docs/architecture/ai.md",
        "docs/architecture/infrastructure.md",
        # Deployment
        "docs/deployment/development.md",
        "docs/deployment/staging.md",
        "docs/deployment/production.md",
        "docs/deployment/rollback.md",
        "docs/deployment/disaster-recovery.md",
        # Operations
        "docs/operations/monitoring.md",
        "docs/operations/backups.md",
        "docs/operations/incidents.md",
        "docs/operations/troubleshooting.md",
        # API
        "docs/api/README.md",
        # Data
        "docs/data/model.md",
        "docs/data/etl.md",
        "docs/data/data-quality.md",
        # AI
        "docs/ai/rag.md",
        "docs/ai/evaluation.md",
        "docs/ai/guardrails.md",
    ]

    missing = []
    for rel_path in expected_files:
        p = REPO_ROOT / rel_path
        if not p.is_file():
            missing.append(rel_path)

    assert not missing, f"Missing required documentation files: {missing}"


def test_readme_completeness_and_sections():
    """10.22: Verify README.md contains all 16 required sections and core product vision."""
    readme_path = REPO_ROOT / "README.md"
    assert readme_path.is_file(), "README.md must exist"

    content = readme_path.read_text(encoding="utf-8")

    # Product description & problem
    assert "MercadoInsight" in content
    assert "ChileCompra" in content
    assert "inteligencia de mercado" in content.lower()
    assert "geriátrica" in content.lower() or "discapacidad" in content.lower()

    # All 16 sections
    required_sections = [
        "Overview",
        "Features",
        "Architecture",
        "Tech Stack",
        "Screenshots",
        "Installation",
        "Development",
        "Testing",
        "Deployment",
        "API",
        "AI / RAG",
        "Data",
        "Monitoring",
        "Security",
        "Roadmap",
        "License",
    ]

    for section in required_sections:
        pattern = rf"(?i)##\s+.*{re.escape(section)}"
        assert re.search(pattern, content), f"Section '{section}' missing from README.md"


def test_c4_model_architecture_diagrams():
    """10.23: Verify ARCHITECTURE.md and docs/architecture/overview.md feature C4 Model diagrams."""
    arch_path = REPO_ROOT / "ARCHITECTURE.md"
    overview_path = REPO_ROOT / "docs/architecture/overview.md"

    assert arch_path.is_file(), "ARCHITECTURE.md must exist"
    assert overview_path.is_file(), "docs/architecture/overview.md must exist"

    content = arch_path.read_text(encoding="utf-8")

    # Level 1: System Context
    assert "C4Context" in content or "Nivel 1" in content
    assert "ChileCompra" in content
    assert "LLM" in content or "OpenAI" in content

    # Level 2: Containers
    assert "C4Container" in content or "Nivel 2" in content
    assert "FastAPI" in content
    assert "PostgreSQL" in content
    assert "Redis" in content
    assert "MinIO" in content
    assert "Celery" in content or "Worker" in content

    # Level 3: Components
    assert "C4Component" in content or "Nivel 3" in content
    assert "Auth Router" in content or "router" in content.lower()
    assert "RAG Orchestrator" in content or "rag" in content.lower()
    assert "ETL" in content

    # Mermaid diagrams syntax check
    assert "```mermaid" in content


def test_api_documentation_completeness():
    """10.24: Verify API.md and docs/api/README.md document OpenAPI, JWT, errors, streaming, rate limits."""
    api_root = REPO_ROOT / "API.md"
    api_docs = REPO_ROOT / "docs/api/README.md"

    for doc_path in (api_root, api_docs):
        assert doc_path.is_file(), f"{doc_path} must exist"
        content = doc_path.read_text(encoding="utf-8")

        # Interactive docs
        assert "/api/docs" in content
        assert "/api/redoc" in content
        assert "/api/openapi.json" in content

        # Auth & Errors
        assert "JWT" in content or "Bearer" in content
        assert "401" in content or "404" in content or "422" in content

        # Pagination & Streaming & Rate Limit
        assert "page" in content.lower() and "page_size" in content.lower()
        assert "stream" in content.lower() or "Server-Sent Events" in content or "SSE" in content
        assert "rate limit" in content.lower()


def test_operations_incident_runbooks():
    """10.25: Verify troubleshooting.md and incidents.md cover API caída, ETL detenido, Postgres lleno."""
    troubleshooting_path = REPO_ROOT / "docs/operations/troubleshooting.md"
    incidents_path = REPO_ROOT / "docs/operations/incidents.md"

    assert troubleshooting_path.is_file()
    assert incidents_path.is_file()

    tb_content = troubleshooting_path.read_text(encoding="utf-8")

    # Runbook 1: API caída
    assert "API Caída" in tb_content or "api caída" in tb_content.lower()
    assert "health/ready" in tb_content
    assert "docker ps" in tb_content or "docker compose" in tb_content

    # Runbook 2: ETL detenido
    assert "ETL Detenido" in tb_content or "etl detenido" in tb_content.lower()
    assert "etl_runs" in tb_content
    assert "ChileCompra" in tb_content

    # Runbook 3: PostgreSQL lleno
    assert "PostgreSQL Lleno" in tb_content or "postgresql lleno" in tb_content.lower()
    assert "pg_database_size" in tb_content
    assert "VACUUM" in tb_content or "wal" in tb_content.lower()

    # Escalation
    assert "Escalamiento" in tb_content or "escalamiento" in tb_content.lower()

    # Incidents severity matrix
    inc_content = incidents_path.read_text(encoding="utf-8")
    assert "P1" in inc_content and "P2" in inc_content
    assert "Post-Mortem" in inc_content or "post-mortem" in inc_content.lower()


def test_deployment_guide_references_10_21_to_10_25():
    """Verify DEPLOYMENT.md contains references to all subphases 10.21 to 10.25."""
    deploy_path = REPO_ROOT / "DEPLOYMENT.md"
    content = deploy_path.read_text(encoding="utf-8")

    assert "Fase 10.21" in content or "overview.md" in content
    assert "Fase 10.22" in content or "README.md" in content
    assert "Fase 10.23" in content or "ARCHITECTURE.md" in content
    assert "Fase 10.24" in content or "API.md" in content
    assert "Fase 10.25" in content or "troubleshooting.md" in content
