#!/usr/bin/env python3
"""Environment and Secrets Configuration Validator for MercadoInsight.

Validates that .env files adhere to environment specifications (development,
test, staging, production), contain all required variables, and do not use
insecure default/placeholder secrets in production or staging.

Usage:
    python validate-env.py --env development --file .env.example
    python validate-env.py --env staging --file .env.staging
    python validate-env.py --env production --file .env.prod --check-placeholders
"""

import argparse
import re
import sys
from pathlib import Path
from typing import Dict, List, Set

INSECURE_PLACEHOLDERS: Set[str] = {
    "change-me-in-production",
    "market_insight_dev",
    "market_insight_admin_dev",
    "market_insight_app_dev",
    "market_insight_readonly_dev",
    "marketinsight-dev-password",
    "market_insight_redis_dev",
    "replace_with_your_real_key",
    "your_secret_key_here",
    "password",
    "secret",
    "admin",
    "123456",
}

CORE_REQUIRED_VARS: List[str] = [
    "APP_ENV",
    "SECRET_KEY",
    "DATABASE_URL",
    "REDIS_URL",
    "CHILECOMPRA_API_KEY",
    "MINIO_ENDPOINT",
    "MINIO_ACCESS_KEY",
    "MINIO_SECRET_KEY",
]

PROD_STAGING_REQUIRED_VARS: List[str] = [
    "APP_ENV",
    "PUBLIC_BASE_URL",
    "SECRET_KEY",
    "CHILECOMPRA_API_KEY",
    "POSTGRES_PASSWORD",
    "MARKET_INSIGHT_ADMIN_PASSWORD",
    "MARKET_INSIGHT_APP_PASSWORD",
    "MARKET_INSIGHT_READONLY_PASSWORD",
    "REDIS_PASSWORD",
    "MINIO_ROOT_USER",
    "MINIO_ROOT_PASSWORD",
    "GRAFANA_ADMIN_PASSWORD",
    "ALERT_WEBHOOK_TOKEN",
]


def parse_env_file(filepath: Path) -> Dict[str, str]:
    """Parse a .env formatted file into key-value pairs."""
    env_vars: Dict[str, str] = {}
    if not filepath.exists():
        raise FileNotFoundError(f"Configuration file not found: {filepath}")

    with open(filepath, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, start=1):
            line = line.strip()
            # Ignore comments and empty lines
            if not line or line.startswith("#"):
                continue

            if "=" not in line:
                print(f"Warning: Line {line_num} does not contain an '=' assignment: '{line}'", file=sys.stderr)
                continue

            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip()

            # Remove inline comments if not inside quotes
            if val and (val.startswith('"') or val.startswith("'")):
                quote_char = val[0]
                closing_quote = val.find(quote_char, 1)
                if closing_quote != -1:
                    val = val[1:closing_quote]
            else:
                if " #" in val:
                    val = val.split(" #")[0].strip()

            env_vars[key] = val
    return env_vars


def validate_environment(
    env_name: str,
    env_vars: Dict[str, str],
    check_placeholders: bool = False,
    is_template: bool = False,
) -> List[str]:
    """Validate parsed env variables against requirements."""
    errors: List[str] = []
    env_name = env_name.lower().strip()

    # Determine required variables
    if env_name in ("production", "staging"):
        required = PROD_STAGING_REQUIRED_VARS
    else:
        required = CORE_REQUIRED_VARS

    # 1. Check presence of required keys
    for var in required:
        if var not in env_vars:
            # Check for allowed alias
            if var == "APP_ENV" and "ENVIRONMENT" in env_vars:
                continue
            if var == "CHILECOMPRA_API_KEY" and "CHILECOMPRA_API_TICKET" in env_vars:
                continue
            errors.append(f"Missing required variable: '{var}'")

    # 2. Check for empty values if this is not an example/template file
    if not is_template:
        for var in required:
            val = env_vars.get(var)
            if val is None or val == "":
                # Check alias
                if var == "APP_ENV" and env_vars.get("ENVIRONMENT"):
                    continue
                if var == "CHILECOMPRA_API_KEY" and env_vars.get("CHILECOMPRA_API_TICKET"):
                    continue
                errors.append(f"Variable '{var}' cannot be empty in {env_name}")

    # 3. Check insecure placeholders in production or staging
    if check_placeholders or (env_name in ("production", "staging") and not is_template):
        for key, val in env_vars.items():
            if not val:
                continue
            normalized_val = val.lower().strip()
            if normalized_val in INSECURE_PLACEHOLDERS:
                errors.append(
                    f"Insecure placeholder value detected for '{key}': '{val}'. "
                    f"Must be a secure random secret in {env_name}."
                )

        # Specifically check SECRET_KEY minimum entropy
        secret_key = env_vars.get("SECRET_KEY", "")
        if secret_key and not is_template:
            if len(secret_key) < 32 and env_name in ("production", "staging"):
                errors.append(f"SECRET_KEY length ({len(secret_key)}) is less than recommended 32 characters.")

    # 4. Check URL formats if present
    for url_key in ("DATABASE_URL", "REDIS_URL"):
        url_val = env_vars.get(url_key)
        if url_val and not is_template:
            if not re.match(r"^[a-zA-Z0-9+]+://", url_val):
                errors.append(f"Invalid URL scheme for '{url_key}': '{url_val}'")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate MercadoInsight environment configuration files.")
    parser.add_argument("--env", required=True, choices=["development", "test", "staging", "production"],
                        help="Target environment name")
    parser.add_argument("--file", required=True, type=Path, help="Path to .env file to validate")
    parser.add_argument("--check-placeholders", action="store_true",
                        help="Enforce rejection of insecure placeholders (automatic for prod/staging)")
    parser.add_argument("--template", action="store_true",
                        help="Treat as an example template file (allow empty values)")

    args = parser.parse_args()

    # Automatically identify template files from name if not specified
    is_template = args.template or "example" in args.file.name.lower() or "sample" in args.file.name.lower()

    try:
        env_vars = parse_env_file(args.file)
    except Exception as exc:
        print(f"[ERROR] Failed to read {args.file}: {exc}", file=sys.stderr)
        return 1

    errors = validate_environment(
        env_name=args.env,
        env_vars=env_vars,
        check_placeholders=args.check_placeholders,
        is_template=is_template,
    )

    if errors:
        print(f"[VALIDATION FAILED] {len(errors)} error(s) found in {args.file} for environment '{args.env}':")
        for err in errors:
            print(f"  - {err}")
        return 1

    print(f"[SUCCESS] Configuration in '{args.file}' is valid for environment '{args.env}' (vars: {len(env_vars)}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
