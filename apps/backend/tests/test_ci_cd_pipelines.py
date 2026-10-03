"""Tests for Phase 10: CI/CD Strategy, Pipelines, and Security Scans (10.8, 10.9, 10.10, 10.11)."""

import json
from pathlib import Path
import pytest
import yaml


REPO_ROOT = Path(__file__).resolve().parents[3]
WORKFLOWS_DIR = REPO_ROOT / ".github" / "workflows"
DOCS_DIR = REPO_ROOT / "docs" / "deployment"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_workflow(filename: str) -> dict:
    workflow_path = WORKFLOWS_DIR / filename
    assert workflow_path.exists(), f"Workflow file {filename} does not exist at {workflow_path}"
    with open(workflow_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


# ---------------------------------------------------------------------------
# 10.8: CI/CD Strategy & Automation Workflows
# ---------------------------------------------------------------------------

def test_workflow_files_exist_and_valid_yaml():
    """Verify all required CI/CD workflows exist and parse cleanly as YAML."""
    expected_workflows = ["backend.yml", "frontend.yml", "security.yml", "deploy.yml"]
    for wf in expected_workflows:
        data = load_workflow(wf)
        assert isinstance(data, dict), f"Workflow {wf} did not parse into a dictionary"
        assert "name" in data, f"Workflow {wf} missing 'name' attribute"
        assert "jobs" in data, f"Workflow {wf} missing 'jobs' attribute"


def test_deploy_workflow_structure():
    """Verify deploy workflow covers staging, production gate, smoke tests, and rollback."""
    data = load_workflow("deploy.yml")
    jobs = data.get("jobs", {})

    assert "deploy-staging" in jobs, "deploy.yml missing deploy-staging job"
    assert "deploy-production" in jobs, "deploy.yml missing deploy-production job"

    # Staging assertions
    staging_job = jobs["deploy-staging"]
    staging_env = staging_job.get("environment", {})
    staging_env_name = staging_env.get("name") if isinstance(staging_env, dict) else staging_env
    assert staging_env_name == "staging"

    # Production assertions (depends on staging, environment is production)
    prod_job = jobs["deploy-production"]
    assert "deploy-staging" in prod_job.get("needs", [])
    prod_env = prod_job.get("environment", {})
    prod_env_name = prod_env.get("name") if isinstance(prod_env, dict) else prod_env
    assert prod_env_name == "production"

    # Rollback and smoke test steps inside deploy-production
    prod_steps_str = json.dumps(prod_job.get("steps", []))
    assert "smoke-test" in prod_steps_str or "Smoke Tests" in prod_steps_str
    assert "Rollback on Failure" in prod_steps_str
    assert "failure()" in prod_steps_str


def test_ci_cd_documentation_exists():
    """Verify docs/deployment/ci-cd.md exists and covers strategy and secrets."""
    doc_path = DOCS_DIR / "ci-cd.md"
    assert doc_path.exists(), "docs/deployment/ci-cd.md does not exist"

    content = doc_path.read_text(encoding="utf-8")
    assert "Trunk-Based Development" in content
    assert "staging" in content.lower()
    assert "production" in content.lower()
    assert "ghcr.io/ernestostarck/market-insight" in content
    assert "SECRETS" in content.upper()


# ---------------------------------------------------------------------------
# 10.9: Backend Pipeline Tests
# ---------------------------------------------------------------------------

def test_backend_workflow_structure():
    """Verify backend.yml covers lint, typecheck, pytest+cov, security, and GHCR build."""
    data = load_workflow("backend.yml")
    jobs = data.get("jobs", {})

    expected_jobs = ["lint-and-types", "test-and-coverage", "security-audit", "docker-build-push"]
    for ej in expected_jobs:
        assert ej in jobs, f"backend.yml missing job: {ej}"

    # Path filter verification
    triggers = data.get(True) or data.get("on") or {}
    push_paths = triggers.get("push", {}).get("paths", [])
    pr_paths = triggers.get("pull_request", {}).get("paths", [])
    assert any("apps/backend/**" in p for p in push_paths), "push triggers missing apps/backend/** path"
    assert any("apps/backend/**" in p for p in pr_paths), "pull_request triggers missing apps/backend/** path"

    # Lint and types steps
    lint_steps_str = json.dumps(jobs["lint-and-types"].get("steps", []))
    assert "ruff check" in lint_steps_str
    assert "ruff format" in lint_steps_str
    assert "mypy" in lint_steps_str

    # Test steps & coverage
    test_steps_str = json.dumps(jobs["test-and-coverage"].get("steps", []))
    assert "pytest" in test_steps_str
    assert "--cov" in test_steps_str

    # Security steps
    security_steps_str = json.dumps(jobs["security-audit"].get("steps", []))
    assert "bandit" in security_steps_str
    assert "pip-audit" in security_steps_str

    # Build and push to GHCR
    build_job = jobs["docker-build-push"]
    assert set(["lint-and-types", "test-and-coverage", "security-audit"]).issubset(set(build_job.get("needs", [])))
    build_steps_str = json.dumps(build_job.get("steps", []))
    assert "IMAGE_NAME_BACKEND" in build_steps_str or "backend" in build_steps_str
    assert "IMAGE_NAME_WORKER" in build_steps_str or "worker" in build_steps_str


def test_backend_pipeline_documentation():
    """Verify docs/deployment/pipeline-backend.md exists and contains detailed stage info."""
    doc_path = DOCS_DIR / "pipeline-backend.md"
    assert doc_path.exists(), "docs/deployment/pipeline-backend.md does not exist"

    content = doc_path.read_text(encoding="utf-8")
    assert "ruff" in content.lower()
    assert "mypy" in content.lower()
    assert "pytest" in content.lower()
    assert "bandit" in content.lower()
    assert "pip-audit" in content.lower()
    assert "ghcr.io/ernestostarck/market-insight/backend" in content


# ---------------------------------------------------------------------------
# 10.10: Frontend Pipeline Tests
# ---------------------------------------------------------------------------

def test_frontend_workflow_structure():
    """Verify frontend.yml covers lint, typecheck, vitest, build, e2e, and GHCR build."""
    data = load_workflow("frontend.yml")
    jobs = data.get("jobs", {})

    expected_jobs = ["lint-and-types", "unit-tests", "build", "e2e-tests", "docker-build-push"]
    for ej in expected_jobs:
        assert ej in jobs, f"frontend.yml missing job: {ej}"

    # Path filter verification
    triggers = data.get(True) or data.get("on") or {}
    push_paths = triggers.get("push", {}).get("paths", [])
    pr_paths = triggers.get("pull_request", {}).get("paths", [])
    assert any("apps/frontend/**" in p for p in push_paths), "push triggers missing apps/frontend/** path"
    assert any("apps/frontend/**" in p for p in pr_paths), "pull_request triggers missing apps/frontend/** path"

    # Steps verification
    lint_steps_str = json.dumps(jobs["lint-and-types"].get("steps", []))
    assert "npm run lint" in lint_steps_str
    assert "npm run typecheck" in lint_steps_str

    unit_steps_str = json.dumps(jobs["unit-tests"].get("steps", []))
    assert "npm run test" in unit_steps_str

    build_steps_str = json.dumps(jobs["build"].get("steps", []))
    assert "npm run build" in build_steps_str

    e2e_steps_str = json.dumps(jobs["e2e-tests"].get("steps", []))
    assert "playwright" in e2e_steps_str

    # Build and push to GHCR
    build_push_job = jobs["docker-build-push"]
    build_push_steps_str = json.dumps(build_push_job.get("steps", []))
    assert "IMAGE_NAME_FRONTEND" in build_push_steps_str or "frontend" in build_push_steps_str


def test_frontend_package_json_typecheck_script():
    """Verify frontend package.json includes typecheck script."""
    pkg_path = REPO_ROOT / "apps" / "frontend" / "package.json"
    assert pkg_path.exists(), "apps/frontend/package.json does not exist"

    with open(pkg_path, "r", encoding="utf-8") as f:
        pkg = json.load(f)

    assert "typecheck" in pkg.get("scripts", {}), "package.json missing 'typecheck' script"
    assert "tsc" in pkg["scripts"]["typecheck"]


def test_frontend_pipeline_documentation():
    """Verify docs/deployment/pipeline-frontend.md exists and contains detailed stage info."""
    doc_path = DOCS_DIR / "pipeline-frontend.md"
    assert doc_path.exists(), "docs/deployment/pipeline-frontend.md does not exist"

    content = doc_path.read_text(encoding="utf-8")
    assert "eslint" in content.lower()
    assert "typecheck" in content.lower()
    assert "vitest" in content.lower()
    assert "playwright" in content.lower()
    assert "ghcr.io/ernestostarck/market-insight/frontend" in content


# ---------------------------------------------------------------------------
# 10.11: Docker Security Scan Tests
# ---------------------------------------------------------------------------

def test_security_workflow_structure():
    """Verify security.yml scans filesystems, Docker images, and uploads SARIF."""
    data = load_workflow("security.yml")
    jobs = data.get("jobs", {})

    assert "fs-and-secret-scan" in jobs, "security.yml missing fs-and-secret-scan job"
    assert "docker-image-scan" in jobs, "security.yml missing docker-image-scan job"
    assert "dependency-audit" in jobs, "security.yml missing dependency-audit job"

    # Trivy scan steps
    trivy_repo_steps = json.dumps(jobs["fs-and-secret-scan"].get("steps", []))
    assert "aquasecurity/trivy-action" in trivy_repo_steps
    assert "upload-sarif" in trivy_repo_steps

    trivy_container_steps = json.dumps(jobs["docker-image-scan"].get("steps", []))
    assert "aquasecurity/trivy-action" in trivy_container_steps
    assert "CRITICAL,HIGH" in trivy_container_steps

    # Dependency audits steps
    dep_audit_steps = json.dumps(jobs["dependency-audit"].get("steps", []))
    assert "pip-audit" in dep_audit_steps
    assert "npm audit" in dep_audit_steps

    # Trigger verification (includes cron/schedule)
    triggers = data.get(True) or data.get("on") or {}
    assert "schedule" in triggers or "schedule" in data.get("on", {}), "security.yml missing schedule trigger"


def test_security_scan_documentation():
    """Verify docs/deployment/security-scan.md exists and documents Trivy, SARIF, and triage."""
    doc_path = DOCS_DIR / "security-scan.md"
    assert doc_path.exists(), "docs/deployment/security-scan.md does not exist"

    content = doc_path.read_text(encoding="utf-8")
    assert "Trivy" in content
    assert "SARIF" in content
    assert "CRITICAL" in content
    assert "HIGH" in content
    assert "pip-audit" in content
    assert "npm audit" in content


def test_deployment_guide_references_new_docs():
    """Verify DEPLOYMENT.md references all 4 newly created deployment guide documents."""
    deploy_md = REPO_ROOT / "DEPLOYMENT.md"
    assert deploy_md.exists(), "DEPLOYMENT.md does not exist"

    content = deploy_md.read_text(encoding="utf-8")
    assert "docs/deployment/ci-cd.md" in content
    assert "docs/deployment/pipeline-backend.md" in content
    assert "docs/deployment/pipeline-frontend.md" in content
    assert "docs/deployment/security-scan.md" in content
