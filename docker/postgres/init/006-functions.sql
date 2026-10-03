-- Utility functions. 'unaccent' is loaded from the 'public' schema via the
-- search_path, so we qualify the call explicitly to be robust regardless of
-- the caller's search_path.

CREATE OR REPLACE FUNCTION core.set_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION core.normalize_text(input_text TEXT)
RETURNS TEXT
LANGUAGE sql
IMMUTABLE
AS $$
    SELECT lower(trim(public.unaccent(coalesce(input_text, ''))));
$$;

