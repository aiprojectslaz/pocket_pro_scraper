-- =============================================================================
-- 006_fix_core_rls_policies.sql
-- Adds explicit write policies on core.acts and core.sections for service_role
-- so the transformer pipeline can INSERT via PostgREST.
--
-- Background: service_role does not have BYPASSRLS in this project, so RLS
-- policies fire even for service_role. Without an INSERT policy the transformer
-- hits "new row violates row-level security policy".
-- =============================================================================

-- core.acts
DROP POLICY IF EXISTS "acts: service role write" ON core.acts;

CREATE POLICY "acts: service role write"
    ON core.acts FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- core.sections
DROP POLICY IF EXISTS "sections: service role write" ON core.sections;

CREATE POLICY "sections: service role write"
    ON core.sections FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);
