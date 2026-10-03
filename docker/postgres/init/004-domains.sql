DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'rut_chileno') THEN
        CREATE DOMAIN rut_chileno AS VARCHAR(12)
            CHECK (VALUE ~ '^[0-9]+-[0-9Kk]$');
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'codigo_licitacion') THEN
        CREATE DOMAIN codigo_licitacion AS VARCHAR(32)
            CHECK (VALUE ~ '^[0-9]+-[A-Z0-9]+$');
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'codigo_orden_compra') THEN
        CREATE DOMAIN codigo_orden_compra AS VARCHAR(32)
            CHECK (VALUE ~ '^[0-9]+-[A-Z0-9]+$');
    END IF;
END
$$;