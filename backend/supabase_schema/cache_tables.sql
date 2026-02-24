-- Supabase SQL Editor에서 실행하세요.
-- 뉴스/정책/AI분석 캐시 테이블 → Gemini API 호출 절감
-- https://supabase.com/dashboard → SQL Editor → New Query

-- 1. 뉴스 AI 요약 캐시 (동일 뉴스 재요청 시 Gemini 호출 생략)
CREATE TABLE IF NOT EXISTS news_cache (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    source TEXT,
    url TEXT,
    published_at TIMESTAMPTZ,
    ai_summary TEXT,
    related_stocks JSONB DEFAULT '[]',
    category TEXT CHECK (category IN ('global', 'domestic', 'policy')),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_news_cache_created ON news_cache(created_at DESC);
-- 파급력 기반 TTL (매우높음/정책 72h, 보통이하 24h 후 아카이브)
ALTER TABLE news_cache ADD COLUMN IF NOT EXISTS impact_strength TEXT DEFAULT '';
ALTER TABLE news_cache ADD COLUMN IF NOT EXISTS is_archived BOOLEAN DEFAULT FALSE;
CREATE INDEX IF NOT EXISTS idx_news_cache_published ON news_cache(published_at DESC);

-- 2. 정책 AI 분석 캐시 (SAMPLE_POLICIES 폴백용, policy_news에 없는 정책 캐싱)
CREATE TABLE IF NOT EXISTS policy_cache (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    department TEXT,
    description TEXT,
    effective_date DATE,
    ai_analysis TEXT,
    beneficiary_stocks JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_policy_cache_created ON policy_cache(created_at DESC);

-- 3. AI 종목 분석 캐시 (24시간 유효, stock_service에서 사용)
CREATE TABLE IF NOT EXISTS analysis_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    stock_code TEXT NOT NULL,
    stock_name TEXT NOT NULL,
    ai_report TEXT,
    sentiment TEXT CHECK (sentiment IN ('bullish', 'bearish', 'neutral')),
    key_factors TEXT[] DEFAULT '{}',
    analyzed_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ DEFAULT (NOW() + INTERVAL '24 hours')
);

CREATE INDEX IF NOT EXISTS idx_analysis_cache_stock ON analysis_cache(stock_code);
CREATE INDEX IF NOT EXISTS idx_analysis_cache_expires ON analysis_cache(expires_at);

-- report_brief: 기본 탭용 한줄 요약 (수급|회사근황|사야하나?)
ALTER TABLE analysis_cache ADD COLUMN IF NOT EXISTS report_brief TEXT DEFAULT '';
