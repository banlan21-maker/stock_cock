-- Supabase SQL Editor에서 실행하세요.
-- watchlist: 사용자별 관심 종목
-- https://supabase.com/dashboard → SQL Editor → New Query

CREATE TABLE IF NOT EXISTS watchlist (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    stock_code TEXT NOT NULL,
    stock_name TEXT NOT NULL,
    added_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, stock_code)
);

CREATE INDEX IF NOT EXISTS idx_watchlist_user ON watchlist(user_id);

ALTER TABLE watchlist ENABLE ROW LEVEL SECURITY;

-- 이미 있으면 제거 후 재생성 (여러 번 실행해도 오류 없음)
DROP POLICY IF EXISTS "Users can manage own watchlist" ON watchlist;
CREATE POLICY "Users can manage own watchlist"
    ON watchlist FOR ALL
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);
