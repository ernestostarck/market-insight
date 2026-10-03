"""Tests for Phase 10: Versioning, Database Migrations, Backup, and Disaster Recovery (10.12, 10.13, 10.14, 10.15)."""

import json
import os
import sys
import time
from pathlib import Path
import pytest
try:
    import tomllib
except ImportError:
    import tomli as tomllib

REPO_ROOT = Path(__file__).resolve().parents[3]
DOCS_DIR = REPO_ROOT / "docs" / "deployment"
SCRIPTS_DIR = REPO_ROOT / "infrastructure" / "scripts"

# Add infrastructure scripts to sys.path for direct testing
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import backup  # noqa: E402
import restore  # noqa: E402


# ---------------------------------------------------------------------------
# 10.12: Versioning Tests
# ---------------------------------------------------------------------------

def test_version_consistency_across_codebase():
    """Verify backend pyproject.toml, frontend package.json, and settings.py are at version 1.0.0."""
    # 1. pyproject.toml
    pyproject_path = REPO_ROOT / "apps" / "backend" / "pyproject.toml"
    assert pyproject_path.exists()
    with open(pyproject_path, "rb") as f:
        pyproject = tomllib.load(f)
    assert pyproject["project"]["version"] == "1.0.0", f"pyproject version is {pyproject['project']['version']}"

    # 2. package.json
    package_path = REPO_ROOT / "apps" / "frontend" / "package.json"
    assert package_path.exists()
    with open(package_path, "r", encoding="utf-8") as f:
        pkg = json.load(f)
    assert pkg["version"] == "1.0.0", f"package.json version is {pkg['version']}"

    # 3. settings.py
    from app.core.settings import Settings
    s = Settings()
    assert s.app_version == "1.0.0", f"Settings app_version default is {s.app_version}"


def test_changelog_structure_and_keep_a_changelog():
    """Verify CHANGELOG.md adheres to Keep a Changelog standard and lists releases."""
    changelog_path = REPO_ROOT / "CHANGELOG.md"
    assert changelog_path.exists(), "CHANGELOG.md does not exist"

    content = changelog_path.read_text(encoding="utf-8")
    assert "Keep a Changelog" in content
    assert "Semantic Versioning" in content or "semver.org" in content
    assert "[Unreleased]" in content
    assert "[1.0.0] - 2026-09-22" in content
    assert "[0.2.0]" in content
    assert "[0.1.0]" in content
    assert "### Added" in content


def test_versioning_documentation():
    """Verify docs/deployment/versioning.md documents SemVer, Git tags, Docker tags, and Sentry."""
    doc_path = DOCS_DIR / "versioning.md"
    assert doc_path.exists(), "docs/deployment/versioning.md does not exist"

    content = doc_path.read_text(encoding="utf-8")
    assert "MAJOR" in content
    assert "MINOR" in content
    assert "PATCH" in content
    assert "CHANGELOG.md" in content
    assert "git tag" in content
    assert "ghcr.io/ernestostarck/market-insight" in content
    assert "Sentry" in content


# ---------------------------------------------------------------------------
# 10.13: Database Migrations Tests (Alembic)
# ---------------------------------------------------------------------------

def test_alembic_single_head_and_linear_graph():
    """Verify Alembic has a single linear head with no branched or missing revisions."""
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    alembic_ini_path = REPO_ROOT / "apps" / "backend" / "alembic.ini"
    assert alembic_ini_path.exists()

    cfg = Config(str(alembic_ini_path))
    cfg.set_main_option("script_location", str(REPO_ROOT / "apps" / "backend" / "alembic"))
    script = ScriptDirectory.from_config(cfg)

    heads = script.get_heads()
    assert len(heads) == 1, f"Expected exactly 1 Alembic head, but found: {heads}"
    assert heads[0] == "20261002_0019", f"Unexpected head revision: {heads[0]}"

    # Traverse revisions backwards from head to base to verify linear continuity
    current = script.get_revision(heads[0])
    revision_count = 0
    while current is not None:
        revision_count += 1
        if current.down_revision is None:
            break
        current = script.get_revision(current.down_revision)

    assert revision_count >= 18, f"Expected at least 18 revisions in linear chain, counted: {revision_count}"


def test_database_migrations_documentation():
    """Verify docs/deployment/database-migrations.md documents zero-downtime, expand/contract, and rollback."""
    doc_path = DOCS_DIR / "database-migrations.md"
    assert doc_path.exists(), "docs/deployment/database-migrations.md does not exist"

    content = doc_path.read_text(encoding="utf-8")
    assert "Alembic" in content
    assert "alembic upgrade head" in content
    assert "alembic downgrade -1" in content
    assert "Expand / Contract" in content
    assert "Zero-Downtime" in content or "zero-downtime" in content.lower()
    assert "alembic_version" in content


# ---------------------------------------------------------------------------
# 10.14: Backup Strategy Tests
# ---------------------------------------------------------------------------

def test_backup_script_manifest_and_checksums(tmp_path):
    """Test backup.py generates valid manifest with SHA-256 checksums."""
    result = backup.run_backup(
        backup_type="full",
        output_dir=tmp_path,
        retention_days=14,
        dry_run=True,
    )

    assert result["status"] == "SUCCESS"
    assert result["app_version"] == "1.0.0"
    assert len(result["files"]) >= 2  # postgres and config

    manifest_file = tmp_path / "manifest.json"
    assert manifest_file.exists()

    with open(manifest_file, "r", encoding="utf-8") as f:
        loaded_manifest = json.load(f)

    for item in loaded_manifest["files"]:
        target_file = tmp_path / item["filename"]
        assert target_file.exists()
        assert item["size_bytes"] == target_file.stat().st_size
        # Re-compute sha256 to ensure accuracy
        assert item["sha256"] == backup.compute_sha256(target_file)
        assert len(item["sha256"]) == 64  # SHA-256 hex string length


def test_backup_pruning_retention(tmp_path):
    """Test backup.py prunes expired backups beyond retention days."""
    # Create an old dummy backup file with mtime set to 20 days ago
    old_file = tmp_path / "postgres_backup_old.dump"
    old_file.write_bytes(b"OLD_BACKUP_DUMP")
    old_mtime = time.time() - (20 * 86400)
    os.utime(old_file, (old_mtime, old_mtime))

    # Create a recent dummy backup file with mtime set to 2 days ago
    recent_file = tmp_path / "postgres_backup_recent.dump"
    recent_file.write_bytes(b"RECENT_BACKUP_DUMP")
    recent_mtime = time.time() - (2 * 86400)
    os.utime(recent_file, (recent_mtime, recent_mtime))

    # Prune with 14 days retention
    pruned = backup.prune_expired_backups(tmp_path, retention_days=14, dry_run=False)

    assert "postgres_backup_old.dump" in pruned
    assert not old_file.exists(), "Old backup file was not pruned"
    assert recent_file.exists(), "Recent backup file should not be pruned"


def test_backup_strategy_documentation():
    """Verify docs/deployment/backup-strategy.md documents frequencies, pg_dump, MinIO, and PITR."""
    doc_path = DOCS_DIR / "backup-strategy.md"
    assert doc_path.exists(), "docs/deployment/backup-strategy.md does not exist"

    content = doc_path.read_text(encoding="utf-8")
    assert "pg_dump -Fc" in content or "pg_dump" in content
    assert "MinIO" in content
    assert "WAL Archiving" in content or "WAL" in content
    assert "PITR" in content or "Point-in-Time" in content
    assert "manifest.json" in content
    assert "SHA-256" in content or "sha256" in content.lower()


# ---------------------------------------------------------------------------
# 10.15: Disaster Recovery Tests
# ---------------------------------------------------------------------------

def test_restore_script_checksum_tamper_detection(tmp_path):
    """Test restore.py detects tampered/corrupted backups and rejects restoration."""
    # 1. Generate clean backup
    manifest_data = backup.run_backup(
        backup_type="full",
        output_dir=tmp_path,
        retention_days=14,
        dry_run=True,
    )

    manifest_file = tmp_path / "manifest.json"
    assert manifest_file.exists()

    # 2. Verify clean manifest passes
    restore.verify_manifest(manifest_file)

    # 3. Tamper with one of the backup files
    first_file = tmp_path / manifest_data["files"][0]["filename"]
    first_file.write_bytes(b"CORRUPTED_MODIFIED_CONTENT_INJECTED")

    # 4. Expect restore.verify_manifest to raise ValueError
    with pytest.raises(ValueError, match="Checksum mismatch"):
        restore.verify_manifest(manifest_file)


def test_restore_script_dry_run_and_integrity_check(tmp_path):
    """Test restore.py runs dry-run restore and executes integrity verification."""
    backup.run_backup(
        backup_type="full",
        output_dir=tmp_path,
        retention_days=14,
        dry_run=True,
    )

    manifest_file = tmp_path / "manifest.json"

    # Test verify-only mode
    res_verify = restore.run_restore(manifest_file, verify_only=True)
    assert res_verify["status"] == "VERIFIED_ONLY"

    # Test dry-run restore mode
    res_restore = restore.run_restore(manifest_file, dry_run=True)
    assert res_restore["status"] == "RESTORE_COMPLETE"
    assert res_restore["integrity"]["status"] == "HEALTHY"
    assert "alembic_version" in res_restore["integrity"]


def test_disaster_recovery_runbook_documentation():
    """Verify DISASTER_RECOVERY.md exists at repo root with RTO/RPO, runbooks, and recovery sandbox."""
    dr_path = REPO_ROOT / "DISASTER_RECOVERY.md"
    assert dr_path.exists(), "DISASTER_RECOVERY.md does not exist at repo root"

    content = dr_path.read_text(encoding="utf-8")
    assert "RTO" in content
    assert "RPO" in content
    assert "restore.py" in content
    assert "Alembic" in content or "alembic" in content
    assert "Recovery Sandbox" in content
    assert "Checklist" in content
    assert "Simulacros" in content or "Drills" in content


def test_deployment_guide_references_all_four_new_docs():
    """Verify DEPLOYMENT.md contains direct links to versioning, migrations, backup, and recovery."""
    deploy_md = REPO_ROOT / "DEPLOYMENT.md"
    assert deploy_md.exists(), "DEPLOYMENT.md does not exist"

    content = deploy_md.read_text(encoding="utf-8")
    assert "docs/deployment/versioning.md" in content
    assert "docs/deployment/database-migrations.md" in content
    assert "docs/deployment/backup-strategy.md" in content
    assert "DISASTER_RECOVERY.md" in content
