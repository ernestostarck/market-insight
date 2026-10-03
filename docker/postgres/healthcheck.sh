#!/bin/bash
set -euo pipefail

exec pg_isready \
  -h 127.0.0.1 \
  -p "${POSTGRES_PORT:-5432}" \
  -U "${POSTGRES_USER:-market_insight}" \
  -d "${POSTGRES_DB:-market_insight}"