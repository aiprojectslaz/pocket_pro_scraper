-- =============================================================================
-- 004_fix_raw_rls_policies.sql
-- Adds open INSERT/SELECT/UPDATE policies on raw.source_documents so the
-- scraper (importer.py) and transformer (transformer.py) can read and write
-- via the PostgREST API regardless of which key is used.
-- =============================================================================

DROP POLICY IF EXISTS "raw docs: service role only" ON raw.source_documents;
DROP POLICY IF EXISTS "raw: service role all"       ON raw.source_documents;
DROP POLICY IF EXISTS "raw: insert open"            ON raw.source_documents;
DROP POLICY IF EXISTS "raw: select open"            ON raw.source_documents;
DROP POLICY IF EXISTS "raw: update open"            ON raw.source_documents;

CREATE POLICY "raw: service role all"
    ON raw.source_documents FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

CREATE POLICY "raw: insert open"
    ON raw.source_documents FOR INSERT
    TO anon, authenticated
    WITH CHECK (true);

CREATE POLICY "raw: select open"
    ON raw.source_documents FOR SELECT
    TO anon, authenticated
    USING (true);

CREATE POLICY "raw: update open"
    ON raw.source_documents FOR UPDATE
    TO anon, authenticated
    USING (true)
    WITH CHECK (true);
