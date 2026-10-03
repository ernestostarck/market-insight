-- Seed data for reference catalogs.

INSERT INTO core.catalog_values (catalog_name, catalog_code, catalog_label)
VALUES
    -- Estados de licitación
    ('tender_status', 'PUBLICADA', 'Licitación publicada'),
    ('tender_status', 'CERRADA', 'Licitación cerrada'),
    ('tender_status', 'ADJUDICADA', 'Licitación adjudicada'),
    ('tender_status', 'DESIERTA', 'Licitación desierta'),
    -- Estados de orden de compra
    ('oc_status', 'EMITIDA', 'Orden de compra emitida'),
    ('oc_status', 'ACEPTADA', 'Orden de compra aceptada'),
    ('oc_status', 'RECHAZADA', 'Orden de compra rechazada'),
    ('oc_status', 'ANULADA', 'Orden de compra anulada'),
    -- Estados de contrato
    ('contrato_status', 'VIGENTE', 'Contrato vigente'),
    ('contrato_status', 'CERRADO', 'Contrato cerrado'),
    ('contrato_status', 'ANULADO', 'Contrato anulado'),
    ('contrato_status', 'RESCILIADO', 'Contrato resciliado'),
    -- Estados de adjudicación
    ('adjudicacion_status', 'ADJUDICADA', 'Adjudicada'),
    ('adjudicacion_status', 'DESIERTA', 'Desierta'),
    ('adjudicacion_status', 'REVOCADA', 'Revocada'),
    -- Visibilidad de documentos
    ('document_visibility', 'PUBLIC', 'Documento público'),
    ('document_visibility', 'PRIVATE', 'Documento privado'),
    -- Tipos de proveedor
    ('provider_type', 'PERSONA_NATURAL', 'Persona natural'),
    ('provider_type', 'PERSONA_JURIDICA', 'Persona jurídica')
ON CONFLICT (catalog_name, catalog_code) DO NOTHING;

