CREATE SCHEMA IF NOT EXISTS core;
CREATE SCHEMA IF NOT EXISTS market;
CREATE SCHEMA IF NOT EXISTS procurement;
CREATE SCHEMA IF NOT EXISTS documents;
CREATE SCHEMA IF NOT EXISTS analytics;
CREATE SCHEMA IF NOT EXISTS knowledge;
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS ai;

ALTER SCHEMA core OWNER TO market_insight_admin;
ALTER SCHEMA market OWNER TO market_insight_admin;
ALTER SCHEMA procurement OWNER TO market_insight_admin;
ALTER SCHEMA documents OWNER TO market_insight_admin;
ALTER SCHEMA analytics OWNER TO market_insight_admin;
ALTER SCHEMA knowledge OWNER TO market_insight_admin;
ALTER SCHEMA staging OWNER TO market_insight_admin;
ALTER SCHEMA ai OWNER TO market_insight_admin;

GRANT USAGE ON SCHEMA core, market, procurement, documents, analytics, knowledge, staging, ai TO market_insight_admin, market_insight_app, market_insight_readonly;

ALTER DEFAULT PRIVILEGES IN SCHEMA core GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO market_insight_admin;
ALTER DEFAULT PRIVILEGES IN SCHEMA core GRANT SELECT ON TABLES TO market_insight_app, market_insight_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA procurement GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO market_insight_admin;
ALTER DEFAULT PRIVILEGES IN SCHEMA procurement GRANT SELECT ON TABLES TO market_insight_app, market_insight_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA staging GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO market_insight_admin;
ALTER DEFAULT PRIVILEGES IN SCHEMA staging GRANT SELECT ON TABLES TO market_insight_app, market_insight_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA ai GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO market_insight_admin, market_insight_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA ai GRANT SELECT ON TABLES TO market_insight_readonly;

-- ---------------------------------------------------------------------------
-- core.catalog_values
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS core.catalog_values (
    catalog_name VARCHAR(64) NOT NULL,
    catalog_code VARCHAR(64) NOT NULL,
    catalog_label VARCHAR(256) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (catalog_name, catalog_code)
);

-- ---------------------------------------------------------------------------
-- procurement.*  ETL target tables (one per transformed entity)
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS procurement.tenders (
    id BIGSERIAL PRIMARY KEY,
    external_id VARCHAR(128) NOT NULL UNIQUE,
    title VARCHAR(512) NOT NULL,
    agency VARCHAR(256) NOT NULL,
    category VARCHAR(256) NOT NULL,
    status VARCHAR(64) NOT NULL DEFAULT 'open',
    source_url VARCHAR(1024) NOT NULL,
    estimated_amount DOUBLE PRECISION,
    published_at TIMESTAMPTZ,
    closing_date TIMESTAMPTZ,
    raw_payload TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS procurement.licitaciones (
    id BIGSERIAL PRIMARY KEY,
    external_id VARCHAR(128) NOT NULL,
    title VARCHAR(1024),
    status VARCHAR(64),
    published_at TIMESTAMPTZ,
    closing_at TIMESTAMPTZ,
    agency_code VARCHAR(64),
    agency_name VARCHAR(512),
    natural_key VARCHAR(256) NOT NULL,
    payload_hash VARCHAR(64) NOT NULL,
    source VARCHAR(64) NOT NULL DEFAULT 'chilecompra',
    raw_payload JSONB,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_licitaciones_natural_key UNIQUE (natural_key)
);

CREATE TABLE IF NOT EXISTS procurement.ordenes_compra (
    id BIGSERIAL PRIMARY KEY,
    external_id VARCHAR(128) NOT NULL,
    title VARCHAR(1024),
    status VARCHAR(64),
    created_at TIMESTAMPTZ,
    issued_at TIMESTAMPTZ,
    provider_code VARCHAR(64),
    provider_name VARCHAR(512),
    agency_code VARCHAR(64),
    agency_name VARCHAR(512),
    total_amount DOUBLE PRECISION,
    natural_key VARCHAR(256) NOT NULL,
    payload_hash VARCHAR(64) NOT NULL,
    source VARCHAR(64) NOT NULL DEFAULT 'chilecompra',
    raw_payload JSONB,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_ordenes_compra_natural_key UNIQUE (natural_key)
);

CREATE TABLE IF NOT EXISTS procurement.proveedores (
    id BIGSERIAL PRIMARY KEY,
    external_id VARCHAR(128) NOT NULL,
    rut VARCHAR(12),
    name VARCHAR(512) NOT NULL,
    legal_name VARCHAR(512),
    company_type VARCHAR(128),
    status VARCHAR(64),
    updated_at TIMESTAMPTZ,
    natural_key VARCHAR(256) NOT NULL,
    payload_hash VARCHAR(64) NOT NULL,
    source VARCHAR(64) NOT NULL DEFAULT 'chilecompra',
    raw_payload JSONB,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_proveedores_natural_key UNIQUE (natural_key)
);

CREATE TABLE IF NOT EXISTS procurement.contratos (
    id BIGSERIAL PRIMARY KEY,
    external_id VARCHAR(128) NOT NULL,
    title VARCHAR(1024),
    status VARCHAR(64),
    created_at TIMESTAMPTZ,
    start_at TIMESTAMPTZ,
    end_at TIMESTAMPTZ,
    provider_code VARCHAR(64),
    provider_name VARCHAR(512),
    agency_code VARCHAR(64),
    agency_name VARCHAR(512),
    total_amount DOUBLE PRECISION,
    natural_key VARCHAR(256) NOT NULL,
    payload_hash VARCHAR(64) NOT NULL,
    source VARCHAR(64) NOT NULL DEFAULT 'chilecompra',
    raw_payload JSONB,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_contratos_natural_key UNIQUE (natural_key)
);

CREATE TABLE IF NOT EXISTS procurement.convenios_marco (
    id BIGSERIAL PRIMARY KEY,
    external_id VARCHAR(128) NOT NULL,
    title VARCHAR(1024),
    status VARCHAR(64),
    created_at TIMESTAMPTZ,
    start_at TIMESTAMPTZ,
    end_at TIMESTAMPTZ,
    agency_code VARCHAR(64),
    agency_name VARCHAR(512),
    total_amount DOUBLE PRECISION,
    natural_key VARCHAR(256) NOT NULL,
    payload_hash VARCHAR(64) NOT NULL,
    source VARCHAR(64) NOT NULL DEFAULT 'chilecompra',
    raw_payload JSONB,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_convenios_marco_natural_key UNIQUE (natural_key)
);

CREATE TABLE IF NOT EXISTS procurement.adjudicaciones (
    id BIGSERIAL PRIMARY KEY,
    external_id VARCHAR(128) NOT NULL,
    title VARCHAR(1024),
    status VARCHAR(64),
    published_at TIMESTAMPTZ,
    awarded_at TIMESTAMPTZ,
    agency_code VARCHAR(64),
    agency_name VARCHAR(512),
    provider_code VARCHAR(64),
    provider_name VARCHAR(512),
    awarded_amount DOUBLE PRECISION,
    estimated_amount DOUBLE PRECISION,
    award_ratio DOUBLE PRECISION,
    offers_count INTEGER,
    quality_flags JSONB,
    natural_key VARCHAR(256) NOT NULL,
    payload_hash VARCHAR(64) NOT NULL,
    source VARCHAR(64) NOT NULL DEFAULT 'chilecompra',
    raw_payload JSONB,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_adjudicaciones_natural_key UNIQUE (natural_key)
);

-- ---------------------------------------------------------------------------
-- documents.document_metadata
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS documents.document_metadata (
    id BIGSERIAL PRIMARY KEY,
    bucket VARCHAR(128) NOT NULL,
    object_name VARCHAR(512) NOT NULL UNIQUE,
    uri VARCHAR(1024) NOT NULL,
    is_public BOOLEAN NOT NULL DEFAULT FALSE,
    content_type VARCHAR(255) NOT NULL,
    size_bytes INTEGER NOT NULL,
    checksum_sha256 VARCHAR(64) NOT NULL,
    original_filename VARCHAR(512),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ---------------------------------------------------------------------------
-- staging.*  Raw storage, ingestion runs and quarantine (Fase 3.3 / 3.4 / 3.12)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS staging.raw_ingestion_events (
    id BIGSERIAL PRIMARY KEY,
    ingestion_run_id VARCHAR(64) NOT NULL,
    source VARCHAR(64) NOT NULL,
    resource VARCHAR(64) NOT NULL,
    source_id VARCHAR(128) NOT NULL,
    payload JSONB NOT NULL,
    payload_hash VARCHAR(64) NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    received_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS staging.ingestion_runs (
    id BIGSERIAL PRIMARY KEY,
    ingestion_run_id VARCHAR(64) NOT NULL UNIQUE,
    source VARCHAR(64) NOT NULL,
    resource VARCHAR(64) NOT NULL,
    pipeline_version VARCHAR(64) NOT NULL,
    started_at TIMESTAMPTZ NOT NULL,
    finished_at TIMESTAMPTZ,
    params JSONB NOT NULL DEFAULT '{}'::jsonb,
    status VARCHAR(32) NOT NULL DEFAULT 'running',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS staging.quarantine (
    id BIGSERIAL PRIMARY KEY,
    ingestion_run_id VARCHAR(64) NOT NULL,
    source VARCHAR(64) NOT NULL,
    resource VARCHAR(64) NOT NULL,
    source_id VARCHAR(128),
    payload JSONB,
    error_type VARCHAR(128) NOT NULL,
    error_message TEXT,
    stack_trace TEXT,
    field VARCHAR(256),
    retry_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ---------------------------------------------------------------------------
-- Ownership
-- ---------------------------------------------------------------------------
ALTER TABLE core.catalog_values OWNER TO market_insight_admin;
ALTER TABLE procurement.tenders OWNER TO market_insight_admin;
ALTER TABLE procurement.licitaciones OWNER TO market_insight_admin;
ALTER TABLE procurement.ordenes_compra OWNER TO market_insight_admin;
ALTER TABLE procurement.proveedores OWNER TO market_insight_admin;
ALTER TABLE procurement.contratos OWNER TO market_insight_admin;
ALTER TABLE procurement.convenios_marco OWNER TO market_insight_admin;
ALTER TABLE procurement.adjudicaciones OWNER TO market_insight_admin;
ALTER TABLE documents.document_metadata OWNER TO market_insight_admin;
ALTER TABLE staging.raw_ingestion_events OWNER TO market_insight_admin;
ALTER TABLE staging.ingestion_runs OWNER TO market_insight_admin;
ALTER TABLE staging.quarantine OWNER TO market_insight_admin;

-- ---------------------------------------------------------------------------
-- Grants (application role writes, readonly role reads, admin owns)
-- ---------------------------------------------------------------------------
GRANT SELECT ON TABLE core.catalog_values TO market_insight_app, market_insight_readonly;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE procurement.tenders TO market_insight_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE procurement.licitaciones TO market_insight_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE procurement.ordenes_compra TO market_insight_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE procurement.proveedores TO market_insight_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE procurement.contratos TO market_insight_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE procurement.convenios_marco TO market_insight_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE procurement.adjudicaciones TO market_insight_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE documents.document_metadata TO market_insight_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE staging.raw_ingestion_events TO market_insight_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE staging.ingestion_runs TO market_insight_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE staging.quarantine TO market_insight_app;
GRANT SELECT ON TABLE procurement.licitaciones, procurement.ordenes_compra, procurement.proveedores,
    procurement.contratos, procurement.convenios_marco, procurement.adjudicaciones,
    staging.raw_ingestion_events, staging.ingestion_runs, staging.quarantine
    TO market_insight_readonly;

GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA core TO market_insight_admin, market_insight_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA procurement TO market_insight_admin, market_insight_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA documents TO market_insight_admin, market_insight_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA staging TO market_insight_admin, market_insight_app;

