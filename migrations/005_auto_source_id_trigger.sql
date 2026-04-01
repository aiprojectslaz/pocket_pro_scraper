-- =============================================================================
-- 005_auto_source_id_trigger.sql
-- Auto-populates raw.source_documents.source_id on INSERT by matching
-- source_url against public.content_sources.source_url.
-- If no match is found, source_id stays NULL (no error).
-- =============================================================================

CREATE OR REPLACE FUNCTION raw.set_source_id()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.source_id IS NULL AND NEW.source_url <> '' THEN
        SELECT id INTO NEW.source_id
        FROM public.content_sources
        WHERE source_url = NEW.source_url
        LIMIT 1;
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_set_source_id
    BEFORE INSERT ON raw.source_documents
    FOR EACH ROW
    EXECUTE FUNCTION raw.set_source_id();
