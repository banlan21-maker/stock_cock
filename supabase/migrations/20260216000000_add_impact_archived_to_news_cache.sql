-- 파급력 기반 TTL: impact_strength, is_archived
ALTER TABLE news_cache ADD COLUMN IF NOT EXISTS impact_strength TEXT DEFAULT '';
ALTER TABLE news_cache ADD COLUMN IF NOT EXISTS is_archived BOOLEAN DEFAULT FALSE;

CREATE INDEX IF NOT EXISTS idx_news_cache_published ON news_cache(published_at DESC);
