-- =============================================================================
-- 001_reset_schema.sql
-- Full schema reset: drops existing data and rebuilds core + public schemas
-- Run in Supabase SQL Editor (as postgres / service_role)
-- =============================================================================

-- ─────────────────────────────────────────────────────────────────────────────
-- 0. WIPE EXISTING SCHEMAS (order matters — public last so auth.users stays)
-- ─────────────────────────────────────────────────────────────────────────────

DROP SCHEMA IF EXISTS core    CASCADE;
DROP SCHEMA IF EXISTS raw     CASCADE;
DROP SCHEMA IF EXISTS app     CASCADE;
DROP SCHEMA IF EXISTS archive CASCADE;
DROP SCHEMA IF EXISTS analytics CASCADE;

-- Drop custom tables from public (keep Supabase internal tables)
DROP TABLE IF EXISTS public.procedures          CASCADE;
DROP TABLE IF EXISTS public.tenants             CASCADE;
DROP TABLE IF EXISTS public.user_subscriptions  CASCADE;
DROP TABLE IF EXISTS public.content_sources     CASCADE;
-- legacy tables (may not exist)
DROP TABLE IF EXISTS public.acts                CASCADE;
DROP TABLE IF EXISTS public.sections            CASCADE;
DROP TABLE IF EXISTS public.definitions         CASCADE;
DROP TABLE IF EXISTS public.source_documents    CASCADE;

-- Drop custom types
DROP TYPE IF EXISTS public.content_tier  CASCADE;
DROP TYPE IF EXISTS public.access_tier   CASCADE;
DROP TYPE IF EXISTS public.section_type  CASCADE;

-- ─────────────────────────────────────────────────────────────────────────────
-- 1. SCHEMAS
-- ─────────────────────────────────────────────────────────────────────────────

CREATE SCHEMA IF NOT EXISTS core;
CREATE SCHEMA IF NOT EXISTS raw;

-- ─────────────────────────────────────────────────────────────────────────────
-- 2. ENUMS
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TYPE public.content_tier AS ENUM ('free', 'registered', 'paid', 'org');
CREATE TYPE public.access_tier  AS ENUM ('free', 'registered', 'paid', 'org');
CREATE TYPE public.section_type AS ENUM (
    'definitions',
    'purpose',
    'powers',
    'offences',
    'procedure',
    'general',
    'other'
);

-- ─────────────────────────────────────────────────────────────────────────────
-- 3. PUBLIC SCHEMA — tables needed before raw/core (FK dependencies first)
-- ─────────────────────────────────────────────────────────────────────────────

-- 3a. public.tenants — organisations with branded/custom content
CREATE TABLE public.tenants (
    id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id         text UNIQUE NOT NULL,
    org_name       text NOT NULL,
    content_label  text NOT NULL DEFAULT 'Procedures',
    brand_primary  text NOT NULL DEFAULT '#0066CC',
    logo_url       text NOT NULL DEFAULT '',
    created_at     timestamptz NOT NULL DEFAULT now()
);

-- 3b. public.content_sources — registry of legal source documents
CREATE TABLE public.content_sources (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name          text NOT NULL,
    tier          public.content_tier NOT NULL DEFAULT 'free',
    jurisdiction  text NOT NULL DEFAULT 'ontario',
    licence       text NOT NULL DEFAULT '',
    source_url    text NOT NULL DEFAULT '',
    attribution   text NOT NULL DEFAULT '',
    tenant_id     uuid REFERENCES public.tenants(id) ON DELETE SET NULL,
    created_at    timestamptz NOT NULL DEFAULT now()
);

-- ─────────────────────────────────────────────────────────────────────────────
-- 4. CORE SCHEMA — raw staging (scraped data)
-- ─────────────────────────────────────────────────────────────────────────────

-- 4a. core.acts — one row per scraped statute
CREATE TABLE core.acts (
    id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    title        text NOT NULL,
    jurisdiction text NOT NULL DEFAULT 'ontario',
    content_tier public.content_tier NOT NULL DEFAULT 'free',
    source_url   text NOT NULL DEFAULT '',
    chapter      text NOT NULL DEFAULT '',
    short_title  text NOT NULL DEFAULT '',
    version_date text NOT NULL DEFAULT '',
    currency_date text NOT NULL DEFAULT '',
    last_amended text NOT NULL DEFAULT '',
    scraped_at   timestamptz NOT NULL DEFAULT now(),
    created_at   timestamptz NOT NULL DEFAULT now()
);

-- 4b. core.sections — individual sections within a scraped act
CREATE TABLE core.sections (
    id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    act_id       uuid NOT NULL REFERENCES core.acts(id) ON DELETE CASCADE,
    section_num  text NOT NULL DEFAULT '',
    heading      text NOT NULL DEFAULT '',
    raw_text     text NOT NULL DEFAULT '',
    section_type public.section_type NOT NULL DEFAULT 'general',
    promoted     boolean NOT NULL DEFAULT false,
    promoted_at  timestamptz,
    created_at   timestamptz NOT NULL DEFAULT now()
);

-- 4c. raw.source_documents — raw JSON blobs from scraper (pre-promotion)
CREATE TABLE raw.source_documents (
    id          bigserial PRIMARY KEY,
    title       text NOT NULL DEFAULT '',
    source_url  text NOT NULL DEFAULT '',
    source_type text NOT NULL CHECK (source_type IN ('html', 'pdf', 'xml')),
    domain      text NOT NULL DEFAULT '',
    content     jsonb NOT NULL,
    source_id   uuid REFERENCES public.content_sources(id) ON DELETE SET NULL,
    confirmed   boolean NOT NULL DEFAULT false,  -- must be true for transformer to promote
    scraped_at  timestamptz NOT NULL DEFAULT now(),
    status      text NOT NULL DEFAULT 'pending'
                CHECK (status IN ('pending', 'imported', 'error'))
);

-- ─────────────────────────────────────────────────────────────────────────────
-- 5. PUBLIC SCHEMA — remaining tables (depend on core.sections)
-- ─────────────────────────────────────────────────────────────────────────────

-- 5a. public.user_subscriptions — per-user access level
CREATE TABLE public.user_subscriptions (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    plan        public.access_tier NOT NULL DEFAULT 'free',
    tenant_id   uuid REFERENCES public.tenants(id) ON DELETE SET NULL,
    active      boolean NOT NULL DEFAULT true,
    expires_at  timestamptz,
    created_at  timestamptz NOT NULL DEFAULT now(),
    UNIQUE (user_id)
);

-- 5b. public.procedures — user-facing procedure content
CREATE TABLE public.procedures (
    id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    title            text NOT NULL,
    summary          text NOT NULL DEFAULT '',
    body             text NOT NULL DEFAULT '',
    jurisdiction     text NOT NULL DEFAULT 'ontario',
    access_tier      public.access_tier NOT NULL DEFAULT 'free',
    is_public        boolean NOT NULL DEFAULT true,
    tenant_id        uuid REFERENCES public.tenants(id) ON DELETE SET NULL,
    source_id        uuid REFERENCES public.content_sources(id) ON DELETE SET NULL,
    core_section_id  uuid REFERENCES core.sections(id) ON DELETE SET NULL,
    created_at       timestamptz NOT NULL DEFAULT now(),
    updated_at       timestamptz NOT NULL DEFAULT now()
);

-- ─────────────────────────────────────────────────────────────────────────────
-- 5. INDEXES
-- ─────────────────────────────────────────────────────────────────────────────

CREATE INDEX ON core.sections (act_id);
CREATE INDEX ON core.sections (section_type);
CREATE INDEX ON core.sections (promoted);
CREATE INDEX ON raw.source_documents (status);
CREATE INDEX ON raw.source_documents (source_id);
CREATE INDEX ON public.procedures (access_tier);
CREATE INDEX ON public.procedures (tenant_id);
CREATE INDEX ON public.procedures (is_public);
CREATE INDEX ON public.procedures (core_section_id);
CREATE INDEX ON public.user_subscriptions (user_id);

-- ─────────────────────────────────────────────────────────────────────────────
-- 6. RLS — enable row-level security
-- ─────────────────────────────────────────────────────────────────────────────

ALTER TABLE core.acts               ENABLE ROW LEVEL SECURITY;
ALTER TABLE core.sections           ENABLE ROW LEVEL SECURITY;
ALTER TABLE raw.source_documents    ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.procedures       ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.tenants          ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.content_sources  ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_subscriptions ENABLE ROW LEVEL SECURITY;

-- ─────────────────────────────────────────────────────────────────────────────
-- 7. HELPER — tier rank function for cross-enum comparison
-- ─────────────────────────────────────────────────────────────────────────────

-- Maps any tier enum value (cast to text) to an integer rank so we can
-- compare access_tier vs content_tier without a cross-type >= operator.
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

-- ─────────────────────────────────────────────────────────────────────────────
-- 8. RLS POLICIES
-- ─────────────────────────────────────────────────────────────────────────────

-- core.acts — public read (free tier is open); write only via service_role
CREATE POLICY "acts: public read"
    ON core.acts FOR SELECT
    USING (content_tier = 'free');

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

-- core.sections — mirrors act policy
CREATE POLICY "sections: public read free"
    ON core.sections FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM core.acts a
            WHERE a.id = act_id
              AND a.content_tier = 'free'
        )
    );

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

-- raw.source_documents — service_role only (no public/user access)
CREATE POLICY "raw docs: service role only"
    ON raw.source_documents FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- public.procedures — free/public rows visible to all; paid rows require subscription
CREATE POLICY "procedures: public read free"
    ON public.procedures FOR SELECT
    USING (is_public = true AND access_tier = 'free');

CREATE POLICY "procedures: registered read"
    ON public.procedures FOR SELECT
    TO authenticated
    USING (
        is_public = true
        AND access_tier IN ('free', 'registered')
    );

CREATE POLICY "procedures: paid read"
    ON public.procedures FOR SELECT
    TO authenticated
    USING (
        access_tier IN ('free', 'registered', 'paid')
        AND EXISTS (
            SELECT 1 FROM public.user_subscriptions us
            WHERE us.user_id = auth.uid()
              AND us.active = true
              AND us.plan IN ('paid', 'org')
        )
    );

CREATE POLICY "procedures: org read"
    ON public.procedures FOR SELECT
    TO authenticated
    USING (
        tenant_id IS NOT NULL
        AND EXISTS (
            SELECT 1 FROM public.user_subscriptions us
            WHERE us.user_id = auth.uid()
              AND us.active = true
              AND us.tenant_id = procedures.tenant_id
        )
    );

-- public.content_sources — public read
CREATE POLICY "content_sources: public read"
    ON public.content_sources FOR SELECT
    USING (true);

-- public.tenants — authenticated read
CREATE POLICY "tenants: authenticated read"
    ON public.tenants FOR SELECT
    TO authenticated
    USING (true);

-- public.user_subscriptions — users see only their own row
CREATE POLICY "subscriptions: owner read"
    ON public.user_subscriptions FOR SELECT
    TO authenticated
    USING (user_id = auth.uid());

CREATE POLICY "subscriptions: owner update"
    ON public.user_subscriptions FOR UPDATE
    TO authenticated
    USING (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());

-- ─────────────────────────────────────────────────────────────────────────────
-- 8. GRANTS
-- ─────────────────────────────────────────────────────────────────────────────

-- service_role: full access everywhere (needed by scraper + transformer)
GRANT USAGE ON SCHEMA core TO service_role;
GRANT USAGE ON SCHEMA raw  TO service_role;
GRANT ALL ON ALL TABLES IN SCHEMA core TO service_role;
GRANT ALL ON ALL TABLES IN SCHEMA raw  TO service_role;
GRANT ALL ON ALL SEQUENCES IN SCHEMA raw TO service_role;
GRANT ALL ON ALL TABLES IN SCHEMA public TO service_role;

-- anon: read public data
GRANT USAGE ON SCHEMA public TO anon;
GRANT SELECT ON public.procedures     TO anon;
GRANT SELECT ON public.content_sources TO anon;

-- authenticated: read public + own subscription
GRANT USAGE ON SCHEMA public TO authenticated;
GRANT SELECT ON public.procedures        TO authenticated;
GRANT SELECT ON public.content_sources   TO authenticated;
GRANT SELECT ON public.tenants           TO authenticated;
GRANT SELECT, UPDATE ON public.user_subscriptions TO authenticated;

-- also grant core.acts + core.sections reads via API (PostgREST)
GRANT USAGE ON SCHEMA core TO anon, authenticated;
GRANT SELECT ON core.acts     TO anon, authenticated;
GRANT SELECT ON core.sections TO anon, authenticated;

-- ─────────────────────────────────────────────────────────────────────────────
-- 9. SEED — public.content_sources
-- ─────────────────────────────────────────────────────────────────────────────

INSERT INTO public.content_sources (name, tier, jurisdiction, licence, source_url, attribution)
VALUES
    (
        'Health Protection and Promotion Act (Ontario)',
        'free', 'ontario',
        'Ontario e-Laws — Queen''s Printer for Ontario',
        'https://www.ontario.ca/laws/statute/90h07',
        'Copyright © Queen''s Printer for Ontario, 2021. Not an official version.'
    ),
    (
        'Personal Health Information Protection Act (Ontario)',
        'free', 'ontario',
        'Ontario e-Laws — Queen''s Printer for Ontario',
        'https://www.ontario.ca/laws/statute/04p03',
        'Copyright © Queen''s Printer for Ontario, 2021. Not an official version.'
    ),
    (
        'Independent Health Facilities Act (Ontario)',
        'free', 'ontario',
        'Ontario e-Laws — Queen''s Printer for Ontario',
        'https://www.ontario.ca/laws/statute/90i03',
        'Copyright © Queen''s Printer for Ontario, 2021. Not an official version.'
    ),
    (
        'Regulated Health Professions Act (Ontario)',
        'free', 'ontario',
        'Ontario e-Laws — Queen''s Printer for Ontario',
        'https://www.ontario.ca/laws/statute/91r18',
        'Copyright © Queen''s Printer for Ontario, 2021. Not an official version.'
    ),
    (
        'Mental Health Act (Ontario)',
        'free', 'ontario',
        'Ontario e-Laws — Queen''s Printer for Ontario',
        'https://www.ontario.ca/laws/statute/90m07',
        'Copyright © Queen''s Printer for Ontario, 2021. Not an official version.'
    ),
    (
        'Immunization of School Pupils Act (Ontario)',
        'free', 'ontario',
        'Ontario e-Laws — Queen''s Printer for Ontario',
        'https://www.ontario.ca/laws/statute/90i01',
        'Copyright © Queen''s Printer for Ontario, 2021. Not an official version.'
    );
