#!/usr/bin/env python3
"""
CLI script to create or update an active user in MercadoInsight.
Usage:
    python infrastructure/scripts/create-user.py --email user@example.com --password MyPassword123.
"""

import argparse
import getpass
import os
import subprocess
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent / "apps" / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.core.security import get_password_hash


def create_or_update_user(email: str, password: str, db_url: str | None = None) -> bool:
    hashed_pwd = get_password_hash(password)
    
    # Check if docker container 'mercadoinsight-postgres-1' is running
    try:
        res = subprocess.run(
            ["docker", "ps", "--filter", "name=postgres", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        container_names = res.stdout.strip().splitlines()
        for cname in container_names:
            if "postgres" in cname:
                # Execute inside container via psql
                escaped_hash = hashed_pwd.replace("$", "\\$")
                sql = (
                    f"INSERT INTO users (id, email, hashed_password, is_active, created_at, updated_at) "
                    f"VALUES (gen_random_uuid(), '{email}', '{escaped_hash}', true, now(), now()) "
                    f"ON CONFLICT (email) DO UPDATE "
                    f"SET hashed_password = EXCLUDED.hashed_password, is_active = true, updated_at = now();"
                )
                cmd = ["docker", "exec", cname, "psql", "-U", "market_insight", "-d", "market_insight", "-c", sql]
                psql_res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                if psql_res.returncode == 0:
                    print(f"[SUCCESS] User '{email}' created/updated via Docker container '{cname}'.")
                    return True
                else:
                    print(f"[WARN] psql in container failed: {psql_res.stderr.strip()}")
    except Exception as exc:
        print(f"[INFO] Docker check skipped: {exc}")

    # Fallback to direct SQLAlchemy
    try:
        import sqlalchemy as sa
        target_url = db_url or os.environ.get("DATABASE_URL")
        if not target_url:
            target_url = "postgresql+psycopg://market_insight:market_insight_dev@localhost:5432/market_insight"
            
        engine = sa.create_engine(target_url, connect_args={"connect_timeout": 5})
        upsert_sql = sa.text("""
            INSERT INTO users (id, email, hashed_password, is_active, created_at, updated_at)
            VALUES (gen_random_uuid(), :email, :hashed_password, true, now(), now())
            ON CONFLICT (email) DO UPDATE
            SET hashed_password = EXCLUDED.hashed_password,
                is_active = true,
                updated_at = now();
        """)
        with engine.connect() as conn:
            with conn.begin():
                conn.execute(upsert_sql, {"email": email, "hashed_password": hashed_pwd})
        print(f"[SUCCESS] User '{email}' created/updated via direct database connection.")
        return True
    except Exception as exc:
        print(f"[ERROR] Failed to create/update user: {exc}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(description="Create or update MercadoInsight user")
    parser.add_argument("--email", required=True, help="User email")
    parser.add_argument("--db-url", default=None, help="Database connection URL")
    args = parser.parse_args()

    # Prompted, never passed on the command line (it would land in shell history / ps).
    password = getpass.getpass("Password: ")
    if password != getpass.getpass("Repeat password: "):
        print("[ERROR] Passwords do not match.", file=sys.stderr)
        sys.exit(1)

    success = create_or_update_user(args.email, password, args.db_url)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
