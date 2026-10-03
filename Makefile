SHELL := powershell

.PHONY: help bootstrap structure docker-up docker-down docker-logs dev-up dev-down test-env alert-tests prod-config prod-up prod-down lint format test clean

help:
	@Write-Host "Targets: bootstrap, structure, lint, format, test, clean"

bootstrap:
	@Write-Host "Install project dependencies and prepare local environment"

structure:
	@Write-Host "Monorepo structure is defined under apps/, packages/, database/, infrastructure/, docs/, docker/"

COMPOSE_DEV     := docker compose -f docker-compose.yml -f docker/compose/docker-compose.dev.yml
COMPOSE_STAGING := docker compose --env-file .env.staging -f docker-compose.yml -f docker/compose/docker-compose.staging.yml
COMPOSE_PROD    := docker compose --env-file .env.prod -f docker-compose.yml -f docker/compose/docker-compose.prod.yml

docker-up:
	docker compose up -d

docker-down:
	docker compose down

# Development: hot reload, Prometheus + Grafana, pgAdmin/RedisInsight
dev-up:
	$(COMPOSE_DEV) up -d --build

dev-down:
	$(COMPOSE_DEV) down

# Test: isolated stack, runs pytest + health/metrics checks, writes ./test-results
test-env:
	bash infrastructure/scripts/test-env.sh

# Unit-test the Prometheus alert rules with promtool (regenerate with build_alert_tests.py after editing rules)
alert-tests:
	python docker/monitoring/prometheus/tests/build_alert_tests.py
	docker run --rm --entrypoint promtool -v "$(CURDIR)/docker/monitoring/prometheus:/p:ro" prom/prometheus:latest test rules /p/tests/alerts.test.yml

# Staging: requires .env.staging (see .env.staging.example)
staging-config:
	$(COMPOSE_STAGING) config --quiet

staging-up:
	$(COMPOSE_STAGING) up -d --build

staging-down:
	$(COMPOSE_STAGING) down

# Production: requires .env.prod (see .env.prod.example) and nginx certs/auth (see DEPLOYMENT.md)
prod-config:
	$(COMPOSE_PROD) config --quiet

prod-up:
	$(COMPOSE_PROD) up -d --build

prod-down:
	$(COMPOSE_PROD) down

validate-env:
	python infrastructure/scripts/validate-env.py --env development --file .env.example
	python infrastructure/scripts/validate-env.py --env staging --file .env.staging.example
	python infrastructure/scripts/validate-env.py --env production --file .env.prod.example

docker-logs:
	docker compose logs -f

lint:
	@Write-Host "Run linters for backend and frontend"

format:
	@Write-Host "Format codebase"

test:
	@Write-Host "Run tests"

clean:
	@Write-Host "Clean generated artifacts"
