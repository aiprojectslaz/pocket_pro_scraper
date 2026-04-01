-- =============================================================================
-- 007_open_core_write_policies.sql
-- Opens INSERT on core.acts and core.sections to anon + authenticated,
-- matching the same open-pipeline pattern used for raw.source_documents
-- in migration 004.
-- =============================================================================

-- core.acts
DROP POLICY IF EXISTS "acts: pipeline insert" ON core.acts;

CREATE POLICY "acts: pipeline insert"
    ON core.acts FOR INSERT
    TO anon, authenticated
    WITH CHECK (true);

-- core.sections
DROP POLICY IF EXISTS "sections: pipeline insert" ON core.sections;

CREATE POLICY "sections: pipeline insert"
    ON core.sections FOR INSERT
    TO anon, authenticated
    WITH CHECK (true);
