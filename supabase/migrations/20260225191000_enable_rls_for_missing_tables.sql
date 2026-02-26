-- 1. 범용 및 캐시 테이블 RLS 활성화
-- 이 테이블들은 백엔드(service_role)에서 관리하므로 RLS를 활성화하고,
-- 조회(SELECT)는 전체 허용하되 변경(INSERT/UPDATE/DELETE)은 차단하여 보안을 강화합니다.

-- 기존 경고 유발 정책 삭제 (policy_news의 Service role full access 등)
DROP POLICY IF EXISTS "Service role full access" ON public.policy_news;
DROP POLICY IF EXISTS "Public Read Access" ON public.policy_news;
DROP POLICY IF EXISTS "Public Read Access" ON public.generic_kv_cache;
DROP POLICY IF EXISTS "Public Read Access" ON public.news_cache;
DROP POLICY IF EXISTS "Public Read Access" ON public.policy_cache;
DROP POLICY IF EXISTS "Public Read Access" ON public.analysis_cache;

-- RLS 활성화
ALTER TABLE public.generic_kv_cache ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.news_cache ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.policy_cache ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.analysis_cache ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.policy_news ENABLE ROW LEVEL SECURITY;

-- 조회 정책: 누구나 읽기 가능 (앱에서 캐시 데이터를 보여주기 위함)
CREATE POLICY "Public Read Access" ON public.generic_kv_cache FOR SELECT USING (true);
CREATE POLICY "Public Read Access" ON public.news_cache FOR SELECT USING (true);
CREATE POLICY "Public Read Access" ON public.policy_cache FOR SELECT USING (true);
CREATE POLICY "Public Read Access" ON public.analysis_cache FOR SELECT USING (true);
CREATE POLICY "Public Read Access" ON public.policy_news FOR SELECT USING (true);

-- 2. investment_journal (투자 일지) RLS 설정
ALTER TABLE public.investment_journal ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can view their own journal entries" ON public.investment_journal;
DROP POLICY IF EXISTS "Users can insert their own journal entries" ON public.investment_journal;
DROP POLICY IF EXISTS "Users can update their own journal entries" ON public.investment_journal;
DROP POLICY IF EXISTS "Users can delete their own journal entries" ON public.investment_journal;

CREATE POLICY "Users can view their own journal entries" ON public.investment_journal FOR SELECT TO authenticated USING (auth.uid()::text = user_id::text);
CREATE POLICY "Users can insert their own journal entries" ON public.investment_journal FOR INSERT TO authenticated WITH CHECK (auth.uid()::text = user_id::text);
CREATE POLICY "Users can update their own journal entries" ON public.investment_journal FOR UPDATE TO authenticated USING (auth.uid()::text = user_id::text) WITH CHECK (auth.uid()::text = user_id::text);
CREATE POLICY "Users can delete their own journal entries" ON public.investment_journal FOR DELETE TO authenticated USING (auth.uid()::text = user_id::text);

-- 3. portfolio_holdings (포트폴리오 보유 종목) RLS 설정
ALTER TABLE public.portfolio_holdings ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can view their own holdings" ON public.portfolio_holdings;
DROP POLICY IF EXISTS "Users can insert their own holdings" ON public.portfolio_holdings;
DROP POLICY IF EXISTS "Users can update their own holdings" ON public.portfolio_holdings;
DROP POLICY IF EXISTS "Users can delete their own holdings" ON public.portfolio_holdings;

CREATE POLICY "Users can view their own holdings" ON public.portfolio_holdings FOR SELECT TO authenticated USING (auth.uid()::text = user_id::text);
CREATE POLICY "Users can insert their own holdings" ON public.portfolio_holdings FOR INSERT TO authenticated WITH CHECK (auth.uid()::text = user_id::text);
CREATE POLICY "Users can update their own holdings" ON public.portfolio_holdings FOR UPDATE TO authenticated USING (auth.uid()::text = user_id::text) WITH CHECK (auth.uid()::text = user_id::text);
CREATE POLICY "Users can delete their own holdings" ON public.portfolio_holdings FOR DELETE TO authenticated USING (auth.uid()::text = user_id::text);
