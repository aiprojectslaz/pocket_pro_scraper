-- =============================================================================
-- 003_fix_tier_rank_policies.sql
-- Fixes the "operator does not exist: access_tier >= content_tier" error.
-- Run this if you already applied 001_reset_schema.sql and hit that error.
-- =============================================================================

-- 1. Helper function: maps any tier value (as text) to a comparable integer
CREATE OR REPLACE FUNCTION public.tier_rank(t text) RETURNS int
    LANGUAGE sql IMMUTABLE PARALLEL SAFE AS $$
        SELECT CASE t
            WHEN 'free'       THEN 1
            WHEN 'registered' THEN 2
            WHEN 'paid'       THEN 3
            WHEN 'org'        THEN 4
            ELSE 0
        END;
$$;

-- 2. Replace the broken policy on core.acts
DROP POLICY IF EXISTS "acts: authenticated read paid" ON core.acts;

CREATE POLICY "acts: authenticated read paid"
    ON core.acts FOR SELECT
    TO authenticated
    USING (
        content_tier IN ('free', 'registered')
        OR (
            content_tier IN ('paid', 'org')
            AND EXISTS (
                SELECT 1 FROM public.user_subscriptions us
                WHERE us.user_id = auth.uid()
                  AND us.active = true
                  AND public.tier_rank(us.plan::text) >= public.tier_rank(content_tier::text)
            )
        )
    );

-- 3. Replace the sections authenticated policy to also use tier_rank
DROP POLICY IF EXISTS "sections: authenticated read" ON core.sections;

CREATE POLICY "sections: authenticated read"
    ON core.sections FOR SELECT
    TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM core.acts a
            WHERE a.id = act_id
              AND (
                  a.content_tier IN ('free', 'registered')
                  OR EXISTS (
                      SELECT 1 FROM public.user_subscriptions us
                      WHERE us.user_id = auth.uid()
                        AND us.active = true
                        AND public.tier_rank(us.plan::text) >= public.tier_rank(a.content_tier::text)
                  )
              )
        )
    );
