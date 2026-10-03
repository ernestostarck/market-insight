"""
Test Suite: Phase 10 Subphases 10.26 - 10.29 Verification
Validates functional user guides, AI manual with core principles,
Architecture Decision Records (ADR), and formal release gate checklist.
"""

import re
import sys
import subprocess
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent


def test_user_guide_documentation_completeness():
    """10.26: Verify all functional user guides exist and explain filters, indicators, sources, and limitations."""
    expected_guides = [
        "docs/user-guide/getting-started.md",
        "docs/user-guide/dashboard.md",
        "docs/user-guide/search.md",
        "docs/user-guide/suppliers.md",
        "docs/user-guide/organizations.md",
        "docs/user-guide/market-analysis.md",
        "docs/user-guide/ai-assistant.md",
    ]

    for rel_path in expected_guides:
        p = REPO_ROOT / rel_path
        assert p.is_file(), f"Missing user guide: {rel_path}"
        content = p.read_text(encoding="utf-8")
        assert len(content) > 300, f"User guide {rel_path} is too short"

    # Specific checks
    search_content = (REPO_ROOT / "docs/user-guide/search.md").read_text(encoding="utf-8")
    assert "filtro" in search_content.lower()

    dashboard_content = (REPO_ROOT / "docs/user-guide/dashboard.md").read_text(encoding="utf-8")
    assert "indicador" in dashboard_content.lower() or "kpi" in dashboard_content.lower()

    ai_assistant_content = (REPO_ROOT / "docs/user-guide/ai-assistant.md").read_text(encoding="utf-8")
    assert "fuente" in ai_assistant_content.lower()
    assert "limitaci" in ai_assistant_content.lower()


def test_ai_manual_and_core_principle():
    """10.27: Verify docs/ai/manual.md answers all 11 required questions and contains the core principle."""
    manual_path = REPO_ROOT / "docs/ai/manual.md"
    assert manual_path.is_file(), "docs/ai/manual.md must exist"

    content = manual_path.read_text(encoding="utf-8")

    # Core principle
    assert "fuente primaria" in content.lower()
    assert "mercado público" in content.lower() or "chilecompra" in content.lower()

    # 11 questions
    questions = [
        "¿Qué puede hacer?",
        "¿Qué datos utiliza?",
        "¿Cómo realiza una búsqueda?",
        "¿Cuándo utiliza SQL?",
        "¿Cuándo utiliza RAG?",
        "¿Cómo calcula indicadores?",
        "¿Qué significa una fuente?",
        "¿Qué sucede cuando no encuentra información?",
        "¿Cuáles son sus limitaciones?",
        "¿Cómo se protege contra prompt injection?",
        "¿Cómo se evalúa?",
    ]

    for q in questions:
        # Search leniently for question keyword
        clean_q = q.replace("¿", "").replace("?", "").strip()
        assert clean_q.lower() in content.lower(), f"Question '{q}' not covered in AI manual"


def test_adr_records_completeness():
    """10.28: Verify all 14 ADRs exist with required structure (Context, Decision, Alternatives, Consequences, Status)."""
    adr_dir = REPO_ROOT / "docs/adr"
    assert adr_dir.is_dir(), "docs/adr directory must exist"

    expected_adrs = [
        "ADR-001-use-postgresql.md",
        "ADR-002-use-pgvector.md",
        "ADR-003-use-fastapi.md",
        "ADR-004-hybrid-search.md",
        "ADR-005-llm-gateway.md",
        "ADR-006-react-frontend.md",
        "ADR-007-docker-deployment.md",
        "ADR-008-redis-broker-cache.md",
        "ADR-009-minio-object-storage.md",
        "ADR-010-hybrid-rag-strategy.md",
        "ADR-011-observability-stack.md",
        "ADR-012-github-actions-cicd.md",
        "ADR-013-two-tier-network-architecture.md",
        "ADR-014-backup-manifest-sha256.md",
    ]

    for adr_name in expected_adrs:
        adr_file = adr_dir / adr_name
        assert adr_file.is_file(), f"Missing ADR: {adr_name}"
        content = adr_file.read_text(encoding="utf-8")

        assert "Status" in content or "Estado" in content
        assert "Context" in content or "Contexto" in content
        assert "Decisión" in content or "Decision" in content
        assert "Alternativas" in content or "Alternatives" in content
        assert "Consecuencias" in content or "Consequences" in content


def test_release_checklist_documentation_and_script():
    """10.29: Verify release checklist documentation and automated release-check.py execution."""
    checklist_path = REPO_ROOT / "docs/deployment/release-checklist.md"
    assert checklist_path.is_file(), "docs/deployment/release-checklist.md must exist"

    content = checklist_path.read_text(encoding="utf-8")
    assert "Code" in content or "Código" in content
    assert "Data" in content or "Datos" in content
    assert "AI" in content
    assert "Security" in content or "Seguridad" in content
    assert "Infrastructure" in content or "Infraestructura" in content
    assert "Deployment" in content or "Despliegue" in content

    # Test release-check.py execution
    script_path = REPO_ROOT / "infrastructure" / "scripts" / "release-check.py"
    assert script_path.is_file(), "infrastructure/scripts/release-check.py must exist"

    res = subprocess.run([sys.executable, str(script_path)], capture_output=True, text=True, cwd=REPO_ROOT)
    assert res.returncode == 0, f"release-check.py failed with: {res.stderr}\n{res.stdout}"
