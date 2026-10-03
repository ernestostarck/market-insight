#!/usr/bin/env bash
# Test environment cycle: up -> health checks -> minimal metrics -> pytest -> logs -> down.
# Artifacts land in ./test-results (junit.xml, logs/*.log). Exit code is non-zero if any step fails.
# Uses its own compose project, so it can run alongside the dev stack.
set -uo pipefail
# Git Bash rewrites absolute-looking arguments (/etc/...) into Windows paths; harmless elsewhere.
export MSYS_NO_PATHCONV=1

cd "$(dirname "$0")/../.."
COMPOSE="docker compose -p mercadoinsight-test -f docker-compose.yml -f docker/compose/docker-compose.test.yml"
OUT=test-results
FAILED=0

mkdir -p "$OUT/logs"
rm -f "$OUT/junit.xml"

step() { printf '\n== %s ==\n' "$1"; }
check() { # check <label> <command...>
  local label=$1; shift
  if "$@" >/dev/null 2>&1; then echo "  ok    $label"; else echo "  FAIL  $label"; FAILED=1; fi
}
retry() { # retry <seconds> <command...>
  local deadline=$((SECONDS + $1)); shift
  until "$@" >/dev/null 2>&1; do [ $SECONDS -ge $deadline ] && return 1; sleep 2; done
}

cleanup() { $COMPOSE --profile test down -v --remove-orphans >/dev/null 2>&1; }
trap cleanup EXIT

step "up"
# No `--wait`: it treats the one-shot minio-init container (exits 0) as a failure.
# A fresh Postgres volume runs its init scripts on first boot and can outlast the
# healthcheck window, aborting `up`; a second `up` just waits for it and starts the rest.
$COMPOSE up -d --build || $COMPOSE up -d || { echo "  FAIL  could not start the stack"; FAILED=1; }

step "health checks"
api_ready() { $COMPOSE exec -T backend curl -fsS http://localhost:8000/health/ready; }
if retry 120 api_ready; then echo "  ok    readiness /health/ready (postgres, redis, storage, workers)"; else echo "  FAIL  readiness /health/ready"; FAILED=1; fi
check "liveness  /health/live" $COMPOSE exec -T backend curl -fsS http://localhost:8000/health/live

step "minimal metrics"
check "backend exposes /metrics" $COMPOSE exec -T backend curl -fsS http://localhost:8000/metrics
prom_job_up() { # prom_job_up <job>
  $COMPOSE exec -T prometheus wget -qO- "http://localhost:9090/api/v1/query?query=up%7Bjob%3D%22$1%22%7D" | grep -q '"1"\]'
}
for job in backend nlp-worker; do
  # the NLP worker loads its model at startup, which can take a couple of minutes
  if retry 240 prom_job_up "$job"; then echo "  ok    prometheus scrapes $job (up=1)"; else echo "  FAIL  prometheus scrapes $job (up=1)"; FAILED=1; fi
done

step "alerting"
prom_get() { $COMPOSE exec -T prometheus wget -qO- "http://localhost:9090$1"; }
am_post() { # am_post <path> <json>
  $COMPOSE exec -T alertmanager wget -qO- --header 'Content-Type: application/json' --post-data "$2" "http://localhost:9093$1"
}
delivered() { # delivered <alertname> -> number of notifications the backend webhook received
  $COMPOSE exec -T backend curl -fsS http://localhost:8000/metrics     | grep "^alertmanager_notifications_received_total{alertname=\"$1\"" | awk '{s+=$2} END {print s+0}'
}
fire() { am_post /api/v2/alerts "[{\"labels\":{\"alertname\":\"$1\",\"severity\":\"critical\",\"team\":\"test\"},\"annotations\":{\"summary\":\"synthetic $1\"}}]" >/dev/null; }
check "alert rules pass their promtool unit tests" $COMPOSE exec -T prometheus promtool test rules /etc/prometheus/tests/alerts.test.yml
check "prometheus loaded the alert rules" sh -c "$COMPOSE exec -T prometheus wget -qO- http://localhost:9090/api/v1/rules | grep -q APIUnavailable"
retry 60 sh -c "$COMPOSE exec -T prometheus wget -qO- http://localhost:9090/api/v1/alertmanagers | grep -q alertmanager:9093"   && echo "  ok    prometheus is connected to alertmanager" || { echo "  FAIL  prometheus is connected to alertmanager"; FAILED=1; }

fire SyntheticDelivered
delivered_ok() { [ "$(delivered SyntheticDelivered)" -ge 1 ]; }
if retry 60 delivered_ok; then echo "  ok    alert delivered to the backend webhook"; else echo "  FAIL  alert delivered to the backend webhook"; FAILED=1; fi

fire SyntheticDelivered; fire SyntheticDelivered; sleep 15
[ "$(delivered SyntheticDelivered)" -eq 1 ] && echo "  ok    duplicate alerts are deduplicated (1 notification)" || { echo "  FAIL  duplicate alerts are deduplicated (got $(delivered SyntheticDelivered))"; FAILED=1; }

now=$(date -u +%Y-%m-%dT%H:%M:%SZ); later=$(date -u -d '+10 minutes' +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -v+10M +%Y-%m-%dT%H:%M:%SZ)
am_post /api/v2/silences "{\"matchers\":[{\"name\":\"alertname\",\"value\":\"SyntheticSilenced\",\"isRegex\":false,\"isEqual\":true}],\"startsAt\":\"$now\",\"endsAt\":\"$later\",\"createdBy\":\"test-env\",\"comment\":\"silence test\"}" >/dev/null
fire SyntheticSilenced; sleep 15
[ "$(delivered SyntheticSilenced)" -eq 0 ] && echo "  ok    silenced alert is not delivered" || { echo "  FAIL  silenced alert is not delivered"; FAILED=1; }
check "alert notification logged as structured JSON" sh -c "$COMPOSE logs --no-color backend | grep -q alert_notification"

step "tests"
$COMPOSE --profile test run --rm test-runner || FAILED=1

step "logs"
for svc in backend nlp-worker postgres redis minio prometheus alertmanager; do
  $COMPOSE logs --no-color --no-log-prefix --timestamps "$svc" > "$OUT/logs/$svc.log" 2>&1
done
check "backend logs are structured JSON" grep -q '"level"' "$OUT/logs/backend.log"
echo "  saved $OUT/logs/*.log"

step "result"
[ -f "$OUT/junit.xml" ] && echo "  junit: $OUT/junit.xml" || { echo "  FAIL  no junit.xml produced"; FAILED=1; }
[ $FAILED -eq 0 ] && echo "  TEST ENVIRONMENT: PASS" || echo "  TEST ENVIRONMENT: FAIL"
exit $FAILED
