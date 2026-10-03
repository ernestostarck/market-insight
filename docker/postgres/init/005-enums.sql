DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'estado_licitacion') THEN
        CREATE TYPE estado_licitacion AS ENUM ('PUBLICADA', 'CERRADA', 'ADJUDICADA', 'DESIERTA');
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'estado_orden_compra') THEN
        CREATE TYPE estado_orden_compra AS ENUM ('EMITIDA', 'ACEPTADA', 'RECHAZADA', 'ANULADA');
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'estado_contrato') THEN
        CREATE TYPE estado_contrato AS ENUM ('VIGENTE', 'CERRADO', 'ANULADO', 'RESCILIADO');
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'estado_adjudicacion') THEN
        CREATE TYPE estado_adjudicacion AS ENUM ('ADJUDICADA', 'DESIERTA', 'REVOCADA');
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'tipo_documento') THEN
        CREATE TYPE tipo_documento AS ENUM ('BASES', 'ANEXO', 'OFERTA', 'ADJUDICACION', 'ORDEN_COMPRA');
    END IF;
END
$$;
