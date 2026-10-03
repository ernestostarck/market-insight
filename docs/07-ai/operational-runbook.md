# Operational Runbook & Production Deployment Guide: Conversational AI & RAG (Fase 9.30)

## 1. Overview & Architectural Principles

MercadoInsight Conversational AI (Fase 9) delivers natural-language intelligence over Chilean Public Procurement data (Mercado Público / ChileCompra). It operates on a strict zero-trust, privacy-first, anti-hallucination architecture:

- **Strict Read-Only Access**: AI execution against core procurement data (raw, marts, dimensions) executes strictly under read-only database credentials with query AST validation preventing DDL/DML.
- **Permanent State vs. Ephemeral Cache**: Long-term conversational history, messages, and offline human feedback persist permanently in PostgreSQL (`schema ai`). Distributed concurrency locks and fast session metadata live ephemerally in Redis with 24-hour TTL.
- **No Direct Model Retraining from Feedback**: User feedback (thumbs up/down) is captured exclusively for offline evaluation, quality regression tracking, and dataset annotation.
- **Provider-Agnostic LLM Gateway**: Standardized interface supporting Google Gemini, OpenAI, Anthropic, and local LLMs with circuit-breaker failovers and token rate limiting.

---

## 2. Environment Variables & Secret Configuration

Production secrets must **NEVER** be committed to source control. Inject secrets via environment files (`.env.production`), HashiCorp Vault, AWS Secrets Manager, or Kubernetes Secrets.

| Variable | Description | Example / Default |
|---|---|---|
| `DATABASE_URL_READONLY` | PostgreSQL connection pool for RAG query execution (read-only user) | `postgresql+asyncpg://mi_rag_ro:****@postgres:5432/market_insight` |
| `DATABASE_URL` | PostgreSQL connection pool for session/feedback persistence | `postgresql+asyncpg://mi_app:****@postgres:5432/market_insight` |
| `REDIS_URL` | Redis instance for session state and distributed locking | `redis://:****@redis:6379/1` |
| `LLM_DEFAULT_PROVIDER` | Primary LLM provider (`gemini`, `openai`, `anthropic`) | `gemini` |
| `LLM_DEFAULT_MODEL` | Default model identifier | `gemini-2.5-flash` |
| `GEMINI_API_KEY` | Google AI Studio / Vertex AI API key | `AIzaSy...` |
| `OPENAI_API_KEY` | OpenAI API key for embeddings or fallback LLM | `sk-proj-...` |
| `ANTHROPIC_API_KEY` | Anthropic Claude API key for high-reasoning fallback | `sk-ant-...` |
| `AI_MAX_CONTEXT_TOKENS` | Maximum context budget for retrieval synthesis | `4000` |
| `AI_RATE_LIMIT_PER_MINUTE` | Rate limit per user token on `/api/v1/chat` | `60` |

---

## 3. Database Security & PostgreSQL Read-Only Setup

To guarantee that the conversational AI layer cannot modify or drop transactional procurement records, configure a dedicated read-only database role:

```sql
-- 1. Create read-only role for RAG queries
CREATE ROLE mi_rag_readonly WITH LOGIN PASSWORD '${POSTGRES_RAG_RO_PASSWORD}';

-- 2. Grant connection and schema usage
GRANT CONNECT ON DATABASE market_insight TO mi_rag_readonly;
GRANT USAGE ON SCHEMA public, marts, raw TO mi_rag_readonly;

-- 3. Grant strictly SELECT permissions on data marts and dimensional models
GRANT SELECT ON ALL TABLES IN SCHEMA marts TO mi_rag_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO mi_rag_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA raw TO mi_rag_readonly;

-- 4. Set default privileges for newly created ingestion tables
ALTER DEFAULT PRIVILEGES IN SCHEMA marts GRANT SELECT ON TABLES TO mi_rag_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO mi_rag_readonly;

-- 5. Revoke write permissions explicitly
REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON ALL TABLES IN SCHEMA marts, public, raw FROM mi_rag_readonly;
```

For the `ai` schema (conversations, messages, feedback), the primary application role `mi_app` retains read-write access to persist turns atomically:

```sql
GRANT USAGE ON SCHEMA ai TO mi_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA ai TO mi_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA ai TO mi_app;
```

---

## 4. Docker & Container Deployment

The backend container exposes the FastAPI application with Server-Sent Events (SSE) streaming support.

### Docker Compose Service Definition

```yaml
  backend:
    build:
      context: .
      dockerfile: docker/backend/Dockerfile
    restart: always
    environment:
      - ENVIRONMENT=production
      - DATABASE_URL=postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}
      - DATABASE_URL_READONLY=postgresql+asyncpg://${POSTGRES_RO_USER}:${POSTGRES_RO_PASSWORD}@postgres:5432/${POSTGRES_DB}
      - REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/1
      - GEMINI_API_KEY=${GEMINI_API_KEY}
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
```

### Reverse Proxy & Nginx SSE Buffer Bypass

Streaming endpoints (`/api/v1/chat/stream`) require disabling proxy response buffering so tokens reach the client immediately without buffering lag:

```nginx
location /api/v1/chat/stream {
    proxy_pass http://backend:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;

    # Critical for SSE Streaming:
    proxy_buffering off;
    proxy_cache off;
    proxy_read_timeout 120s;
    proxy_http_version 1.1;
    proxy_set_header Connection '';
    chunked_transfer_encoding on;
}
```

---

## 5. Observability, Prometheus Metrics & Grafana Dashboards

The Conversational AI layer exposes full telemetry integrated with Fase 8 Observability:

### Core Prometheus Metrics
- `ai_rag_latency_seconds`: Histogram of total chat turn latencies partitioned by `intent`, `retrieval_strategy`, and `model`.
- `ai_retrieval_duration_seconds`: Latency of SQL queries vs. pgvector semantic scans.
- `ai_token_usage_total`: Counter of input and output tokens consumed per model and intent.
- `ai_cost_usd_total`: Calculated cost counter based on LLM vendor token tariffs.
- `ai_guardrail_blocks_total`: Counter of blocked queries partitioned by layer (`injection`, `scope`).
- `ai_feedback_total`: Counter of user ratings (`positive`, `negative`) and rejection reasons.
- `ai_grounding_score`: Gauge of factual coverage ratio (0.0 - 1.0).

### Grafana Dashboard
Dashboard configuration is deployed in:
`docker/monitoring/grafana/dashboards/rag-monitoring.json`

Key Panels:
1. **RAG Latency P95 / P99**
2. **Retrieval Strategy Distribution (SQL vs. Semantic vs. Hybrid)**
3. **Cumulative Cost USD by Model & Department**
4. **Factual Grounding Ratio & Hallucination Rate (< 2% target)**
5. **Prompt Injection & Scope Guardrail Blocks Rate**
6. **User Satisfaction Ratio (Thumbs Up / Total Feedback)**

---

## 6. Backup and Disaster Recovery

### Conversations & Feedback Backup
Conversations and human evaluations are stored durably in PostgreSQL schema `ai`. Schedule automated daily logical backups:

```bash
# Automated daily backup of the AI schema
pg_dump -h localhost -U postgres -d market_insight -n ai -F c -b -v -f /backups/postgres/ai_schema_$(date +%Y%m%d).dump
```

### Recovery Procedure
```bash
# Restore ai schema from backup archive
pg_restore -h localhost -U postgres -d market_insight --clean --if-exists /backups/postgres/ai_schema_20260921.dump
```

---

## 7. Incident Response Runbook

### Incident A: Sudden Spike in Hallucination Rate or Grounding Failures (> 5%)
1. **Symptom**: `ai_grounding_score` drops below 0.90, or user negative feedback reason `hallucination` spikes.
2. **Immediate Mitigation**:
   - Check if pgvector embeddings index is fragmented or out of sync with recent tender documents.
   - Trigger offline evaluation suite via `POST /api/v1/ai/evaluate` to identify specific failing categories.
   - Adjust `temperature` in `config/ai.json` to `0.1` (more conservative generation).
3. **Root Cause**: Check if context token budget was truncated or if tender attachments contained noisy unparsed OCR text.

### Incident B: Primary LLM Gateway Outage or Rate Limit (HTTP 429 / 503)
1. **Symptom**: `ai_rag_latency_seconds` timeout or LLM Gateway errors in Sentry.
2. **Immediate Mitigation**:
   - The LLM Gateway circuit-breaker automatically falls back from `gemini` to `openai` (`gpt-4o-mini`).
   - To force failover manually, update environment variable:
     ```bash
     export LLM_DEFAULT_PROVIDER=openai
     export LLM_DEFAULT_MODEL=gpt-4o-mini
     # Reload backend containers with zero downtime
     docker compose up -d --no-deps backend
     ```

### Incident C: Prompt Injection & Abuse Attacks Detected
1. **Symptom**: Spike in `ai_guardrail_blocks_total{layer="injection"}` and audit log warnings from `ai.security.audit`.
2. **Immediate Mitigation**:
   - Review top offending IP addresses or tokens in security audit logs (`SecurityAuditLogger`).
   - Temporarily blacklist suspicious tokens or enforce tighter rate limits via Redis rate-limiting keys.
   - Verify that all retrieved tender documents pass through `IndirectPromptInjectionDetector.scan_and_neutralize_document`.
