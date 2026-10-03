#!/bin/bash
set -euo pipefail

: "${MARKET_INSIGHT_ADMIN_PASSWORD:?MARKET_INSIGHT_ADMIN_PASSWORD is required}"
: "${MARKET_INSIGHT_APP_PASSWORD:?MARKET_INSIGHT_APP_PASSWORD is required}"
: "${MARKET_INSIGHT_READONLY_PASSWORD:?MARKET_INSIGHT_READONLY_PASSWORD is required}"

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
DO \$\$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'market_insight_admin') THEN
        CREATE ROLE market_insight_admin LOGIN PASSWORD '${MARKET_INSIGHT_ADMIN_PASSWORD}';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'market_insight_app') THEN
        CREATE ROLE market_insight_app LOGIN PASSWORD '${MARKET_INSIGHT_APP_PASSWORD}';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'market_insight_readonly') THEN
        CREATE ROLE market_insight_readonly LOGIN PASSWORD '${MARKET_INSIGHT_READONLY_PASSWORD}';
    END IF;
END
\$\$;

GRANT CONNECT ON DATABASE ${POSTGRES_DB} TO market_insight_admin, market_insight_app, market_insight_readonly;
GRANT USAGE ON SCHEMA public TO market_insight_admin, market_insight_app, market_insight_readonly;
ALTER ROLE market_insight_admin SET search_path = public;
ALTER ROLE market_insight_app SET search_path = public;
ALTER ROLE market_insight_readonly SET search_path = public;
ALTER ROLE market_insight_readonly SET default_transaction_read_only = on;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO market_insight_admin;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO market_insight_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO market_insight_readonly;
EOSQL
