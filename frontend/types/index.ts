// --- News ---
export interface StockMention {
  stock_code: string;
  stock_name: string;
  reason: string;
  /** 직접 수혜주(direct) / 낙수 효과주(indirect) */
  type?: "direct" | "indirect";
}

export interface NewsArticle {
  id: string;
  title: string;
  source: string;
  url: string | null;
  published_at: string;
  category: "global" | "domestic" | "policy";
  ai_summary: string | null;
  related_stocks: StockMention[];
  impact_strength?: string;
}

export interface NewsListResponse {
  items: NewsArticle[];
  total: number;
  page: number;
  limit: number;
}

// --- Policy ---
export interface StockRecommendation {
  stock_code: string;
  stock_name: string;
  reason: string;
  impact: "positive" | "negative" | "neutral";
}

export interface PolicyInfo {
  id: string;
  title: string;
  department: string;
  description: string;
  effective_date: string | null;
  link: string | null;
  image_url: string | null;
  ai_analysis: string | null;
  beneficiary_stocks: StockRecommendation[];
  created_at: string | null;
}

export interface PolicyListResponse {
  items: PolicyInfo[];
  total: number;
  page: number;
  limit: number;
}

// --- Stock ---
export interface StockPrice {
  code: string;
  name: string;
  current_price: number;
  change: number;
  change_rate: number;
  volume: number;
  high: number;
  low: number;
  pbr: number | null;
  roe: number | null;
  debt_ratio: number | null;
  revenue_growth: number | null;
  operating_margin: number | null;
  operating_cashflow: number | null;
}

export interface ChartDataPoint {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface ChartResponse {
  code: string;
  name: string;
  period: string;
  data: ChartDataPoint[];
}

export interface AnalysisItem {
  label: string;
  result: string;
  reason: string;
  description: string;
}

export interface StockAnalysis {
  stock_code: string;
  stock_name: string;
  sentiment: "bullish" | "bearish" | "neutral";
  items: AnalysisItem[];
  overall_score: number;
  overall_comment: string;
  analyzed_at: string;
  expires_at?: string;
}

export interface StockSearchResult {
  code: string;
  name: string;
  market: string;
}

// --- Dashboard ---
export interface MarketIndex {
  value: number;
  change_rate: number;
}

export interface DashboardResponse {
  top_news: NewsArticle[];
  hot_policies: PolicyInfo[];
  market_summary: Record<string, MarketIndex>;
}

// --- Theme Trend ---
export interface ThemeStock {
  code: string;
  name: string;
  change_rate: number;
  volume: number;
}

export interface ThemeGroup {
  theme: string;
  avg_change_rate: number;
  total_volume: number;
  stocks: ThemeStock[];
}

export interface ThemeTrendResponse {
  groups: ThemeGroup[];
  trade_date: string;   // "YYYY-MM-DD" (daily) 또는 "YYYY-MM-DD ~ YYYY-MM-DD" (weekly)
  period: "daily" | "weekly";
}

// --- Keyword Feed ---
export interface KeywordStock {
  code: string;
  name: string;
  market: string;
  current_price: number | null;
  change_rate: number | null;
  reason: string;
}

export interface KeywordFeedResponse {
  stocks: KeywordStock[];
  news: NewsArticle[];
  policies: PolicyInfo[];
}

// --- Stock Compare ---
export interface CompareItem {
  label: string;
  winner: "A" | "B" | "같음";
  a_result: string;
  b_result: string;
  reason: string;
}

export interface StockCompareResult {
  stock_a: { code: string; name: string };
  stock_b: { code: string; name: string };
  items: CompareItem[];
  overall_winner: "A" | "B" | "동점";
  a_score: number;
  b_score: number;
  verdict: string;
  caution: string;
}

export interface WatchlistItem {
  id: string;
  user_id: string;
  stock_code: string;
  stock_name: string;
  added_at: string;
}

// --- Portfolio ---
export interface PortfolioHolding {
  id: string;
  stock_code: string;
  stock_name: string;
  quantity: number;
  avg_price: number;
  current_price: number | null;
  profit_loss: number | null;
  profit_rate: number | null;
  eval_amount: number | null;
  bought_at: string | null;
}

export interface PortfolioSummary {
  total_invest: number;
  total_eval: number;
  total_profit_loss: number;
  total_profit_rate: number;
}

export interface PortfolioResponse {
  holdings: PortfolioHolding[];
  summary: PortfolioSummary;
}

export interface PortfolioAddRequest {
  stock_code: string;
  stock_name: string;
  quantity: number;
  avg_price: number;
  bought_at?: string;
}

export interface PortfolioPerformanceResponse {
  dates: string[];
  portfolio: number[];   // 수익률 % 배열
  kospi: number[];       // KOSPI 수익률 % 배열
  start_date: string | null;
  period: string;
}

// --- Investment Journal (투자일지) ---
export interface JournalEntry {
  id: string;
  stock_name: string;
  stock_code: string | null;
  action: "buy" | "sell";
  trade_date: string;
  price: number;
  quantity: number;
  memo: string | null;
  ai_feedback: string | null;
  created_at: string;
}

export interface JournalListResponse {
  items: JournalEntry[];
  total: number;
  page: number;
  page_size: number;
}

export interface JournalCreateRequest {
  stock_name: string;
  stock_code?: string;
  action: "buy" | "sell";
  trade_date: string;
  price: number;
  quantity: number;
  memo?: string;
}

// --- Disclosure (DART 공시) ---
export interface DisclosureItem {
  rcp_no: string;
  corp_name: string;
  stock_code: string;
  report_nm: string;
  rcept_dt: string;
  flr_nm: string;
  rm: string;
}

export interface DisclosureListResponse {
  items: DisclosureItem[];
  total: number;
}

export interface DisclosureAnalysis {
  rcp_no: string;
  summary: string;
  sentiment: "호재" | "악재" | "중립";
  insight: string;
  caution: string;
}

export interface SectorAnalysis {
  sector: string;
  ratio: number;
  comment: string;
}

export interface RebalancingItem {
  action: "reduce" | "increase" | "hold";
  stock_code: string;
  reason: string;
}

export interface PortfolioAIAnalysis {
  user_id: string;
  total_stocks: number;
  risk_level: "low" | "medium" | "high";
  sector_analysis: SectorAnalysis[];
  rebalancing: RebalancingItem[];
  overall_comment: string;
  overall_score: number;
  analyzed_at: string;
}
