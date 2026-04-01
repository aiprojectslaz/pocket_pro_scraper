-- =============================================================================
-- 002_add_confirmed_flag.sql
-- Adds confirmed boolean to raw.source_documents.
-- Run this ONLY if you already ran 001_reset_schema.sql and need to patch
-- an existing database. Skip if running from scratch (001 already includes it).
-- =============================================================================

ALTER TABLE raw.source_documents
    ADD COLUMN IF NOT EXISTS confirmed boolean NOT NULL DEFAULT false;

COMMENT ON COLUMN raw.source_documents.confirmed IS
    'Set to true once the scrape output has been reviewed and is ready to promote into core.acts/sections. The transformer ignores rows where confirmed = false.';
