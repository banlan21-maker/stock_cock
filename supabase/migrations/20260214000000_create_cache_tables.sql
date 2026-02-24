-- Stock Cock: 캐시 및 관심 종목 테이블
-- 실행: Supabase Dashboard > SQL Editor에서 실행 또는 `supabase db push`

-- 1. 뉴스 캐시 테이블
CREATE TABLE IF NOT EXISTS news_cache (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title TEXT NOT NULL,
  source TEXT,
  url TEXT,
  published_at TIMESTAMPTZ,
  ai_summary TEXT,
  related_stocks TEXT[],
  category TEXT CHECK (category IN ('global', 'domestic', 'policy')),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_news_cache_category ON news_cache(category);
CREATE INDEX IF NOT EXISTS idx_news_cache_created ON news_cache(created_at DESC);

-- 2. 정책 정보 캐시 테이블
CREATE TABLE IF NOT EXISTS policy_cache (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title TEXT NOT NULL,
  department TEXT,
  description TEXT,
  effective_date DATE,
  ai_analysis TEXT,
  beneficiary_stocks JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_policy_cache_created ON policy_cache(created_at DESC);

-- 3. AI 종목 분석 캐시 테이블 (24시간 유효)
CREATE TABLE IF NOT EXISTS analysis_cache (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  stock_code TEXT NOT NULL,
  stock_name TEXT NOT NULL,
  ai_report TEXT,
  sentiment TEXT CHECK (sentiment IN ('bullish', 'bearish', 'neutral')),
  key_factors TEXT[],
  analyzed_at TIMESTAMPTZ DEFAULT NOW(),
  expires_at TIMESTAMPTZ DEFAULT (NOW() + INTERVAL '24 hours')
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_analysis_cache_stock ON analysis_cache(stock_code);
CREATE INDEX IF NOT EXISTS idx_analysis_cache_expires ON analysis_cache(expires_at);

-- 4. 관심 종목 테이블 (RLS 적용)
CREATE TABLE IF NOT EXISTS watchlist (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  stock_code TEXT NOT NULL,
  stock_name TEXT NOT NULL,
  added_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(user_id, stock_code)
);

CREATE INDEX IF NOT EXISTS idx_watchlist_user ON watchlist(user_id);

-- RLS: 사용자는 본인 관심 종목만 접근
ALTER TABLE watchlist ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can manage own watchlist" ON watchlist;
CREATE POLICY "Users can manage own watchlist"
  ON watchlist FOR ALL
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

-- 캐시 테이블은 서비스 역할(Backend)에서만 쓰이므로 RLS 비활성화 (기본)
-- 필요 시 service_role로만 접근하도록 제한됨
