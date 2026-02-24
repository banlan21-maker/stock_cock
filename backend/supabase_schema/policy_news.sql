-- Supabase SQL Editor에서 실행하세요.
-- https://supabase.com/dashboard → SQL Editor → New Query

CREATE TABLE IF NOT EXISTS policy_news (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    link TEXT UNIQUE NOT NULL,
    description TEXT,
    image_url TEXT,
    published_at TIMESTAMPTZ,
    tags TEXT[],
    department TEXT,
    ai_summary TEXT,
    ai_stocks JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_policy_news_published ON policy_news(published_at DESC);

-- RLS 비활성화 (service_role key 사용 시 불필요)
ALTER TABLE policy_news ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Service role full access" ON policy_news
    FOR ALL USING (true) WITH CHECK (true);
