-- Indexes for fast lookups and ETL deduplication.

-- ETL dedup: each table has a UNIQUE constraint on natural_key (defined in
-- 003-schema.sql). Here we add supporting indexes for payload_hash and common
-- query predicates.

CREATE INDEX IF NOT EXISTS ix_tenders_external_id
    ON procurement.tenders (external_id);
CREATE INDEX IF NOT EXISTS ix_tenders_status
    ON procurement.tenders (status);
CREATE INDEX IF NOT EXISTS ix_tenders_published_at
    ON procurement.tenders (published_at);

CREATE INDEX IF NOT EXISTS ix_licitaciones_external_id
    ON procurement.licitaciones (external_id);
CREATE INDEX IF NOT EXISTS ix_licitaciones_payload_hash
    ON procurement.licitaciones (payload_hash);
CREATE INDEX IF NOT EXISTS ix_licitaciones_status
    ON procurement.licitaciones (status);
CREATE INDEX IF NOT EXISTS ix_licitaciones_published_at
    ON procurement.licitaciones (published_at);
CREATE INDEX IF NOT EXISTS ix_licitaciones_agency_code
    ON procurement.licitaciones (agency_code);

CREATE INDEX IF NOT EXISTS ix_ordenes_compra_external_id
    ON procurement.ordenes_compra (external_id);
CREATE INDEX IF NOT EXISTS ix_ordenes_compra_payload_hash
    ON procurement.ordenes_compra (payload_hash);
CREATE INDEX IF NOT EXISTS ix_ordenes_compra_status
    ON procurement.ordenes_compra (status);
CREATE INDEX IF NOT EXISTS ix_ordenes_compra_issued_at
    ON procurement.ordenes_compra (issued_at);
CREATE INDEX IF NOT EXISTS ix_ordenes_compra_provider_code
    ON procurement.ordenes_compra (provider_code);

CREATE INDEX IF NOT EXISTS ix_proveedores_external_id
    ON procurement.proveedores (external_id);
CREATE INDEX IF NOT EXISTS ix_proveedores_rut
    ON procurement.proveedores (rut);
CREATE INDEX IF NOT EXISTS ix_proveedores_payload_hash
    ON procurement.proveedores (payload_hash);
CREATE INDEX IF NOT EXISTS ix_proveedores_name_trgm
    ON procurement.proveedores USING GIN (name gin_trgm_ops);

CREATE INDEX IF NOT EXISTS ix_contratos_external_id
    ON procurement.contratos (external_id);
CREATE INDEX IF NOT EXISTS ix_contratos_payload_hash
    ON procurement.contratos (payload_hash);
CREATE INDEX IF NOT EXISTS ix_contratos_status
    ON procurement.contratos (status);
CREATE INDEX IF NOT EXISTS ix_contratos_start_at
    ON procurement.contratos (start_at);
CREATE INDEX IF NOT EXISTS ix_contratos_provider_code
    ON procurement.contratos (provider_code);

CREATE INDEX IF NOT EXISTS ix_convenios_marco_external_id
    ON procurement.convenios_marco (external_id);
CREATE INDEX IF NOT EXISTS ix_convenios_marco_payload_hash
    ON procurement.convenios_marco (payload_hash);
CREATE INDEX IF NOT EXISTS ix_convenios_marco_status
    ON procurement.convenios_marco (status);
CREATE INDEX IF NOT EXISTS ix_convenios_marco_start_at
    ON procurement.convenios_marco (start_at);

CREATE INDEX IF NOT EXISTS ix_adjudicaciones_external_id
    ON procurement.adjudicaciones (external_id);
CREATE INDEX IF NOT EXISTS ix_adjudicaciones_payload_hash
    ON procurement.adjudicaciones (payload_hash);
CREATE INDEX IF NOT EXISTS ix_adjudicaciones_status
    ON procurement.adjudicaciones (status);
CREATE INDEX IF NOT EXISTS ix_adjudicaciones_awarded_at
    ON procurement.adjudicaciones (awarded_at);
CREATE INDEX IF NOT EXISTS ix_adjudicaciones_provider_code
    ON procurement.adjudicaciones (provider_code);
CREATE INDEX IF NOT EXISTS ix_adjudicaciones_agency_code
    ON procurement.adjudicaciones (agency_code);

-- Documents
CREATE INDEX IF NOT EXISTS ix_document_metadata_bucket
    ON documents.document_metadata (bucket);
CREATE INDEX IF NOT EXISTS ix_document_metadata_is_public
    ON documents.document_metadata (is_public);
CREATE INDEX IF NOT EXISTS ix_document_metadata_checksum_sha256
    ON documents.document_metadata (checksum_sha256);
CREATE INDEX IF NOT EXISTS ix_document_metadata_original_filename_trgm
    ON documents.document_metadata USING GIN (original_filename gin_trgm_ops);

-- Staging (raw + quarantine)
CREATE INDEX IF NOT EXISTS ix_raw_ingestion_events_run_id
    ON staging.raw_ingestion_events (ingestion_run_id);
CREATE INDEX IF NOT EXISTS ix_raw_ingestion_events_source_resource
    ON staging.raw_ingestion_events (source, resource);
CREATE INDEX IF NOT EXISTS ix_raw_ingestion_events_source_id
    ON staging.raw_ingestion_events (source_id);
CREATE INDEX IF NOT EXISTS ix_raw_ingestion_events_payload_hash
    ON staging.raw_ingestion_events (payload_hash);
CREATE INDEX IF NOT EXISTS ix_quarantine_run_id
    ON staging.quarantine (ingestion_run_id);
CREATE INDEX IF NOT EXISTS ix_quarantine_error_type
    ON staging.quarantine (error_type);
