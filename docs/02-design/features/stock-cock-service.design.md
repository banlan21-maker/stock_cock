# Stock Cock (주식콕) Design Document

> **Summary**: 주식 정보를 AI로 분석하여 제공하는 풀스택 웹 서비스 설계
>
> **Project**: Stock Cock
> **Version**: 0.3.0
> **Author**: User
> **Date**: 2026-02-17
> **Status**: Active
> **Planning Doc**: [stock-cock-service.plan.md](../01-plan/features/stock-cock-service.plan.md)

---

## 1. Overview

### 1.1 Design Goals

- Frontend(Next.js)와 Backend(FastAPI)의 명확한 역할 분리
- Gemini AI를 활용한 뉴스 요약 및 종목 분석 파이프라인 구축
- finance-datareader를 통한 한국/글로벌 주식 데이터 수집
- Supabase 인증 + DB 통합 활용
- 모바일 반응형 UI (네이비 테마 일관성)
- SSE 스트리밍을 통한 AI 분석 실시간 진행 표시
- Supabase 영속적 캐시(generic_kv_cache)로 서버 재시작 시 캐시 유지

### 1.2 Design Principles

- **관심사 분리**: Frontend는 UI/UX, Backend는 데이터 수집/AI 분석
- **API 우선 설계**: Backend API를 먼저 정의하고 Frontend에서 소비
- **점진적 구현**: Phase별로 독립 기능 단위 개발
- **캐싱 활용**: AI 분석 결과는 Supabase에 캐싱하여 비용 절감
- **점진적 향상**: SSE 스트리밍 우선, REST 폴백으로 UX 최대화

---

## 2. Architecture

### 2.1 System Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                      Client (Browser)                         │
└──────────────┬───────────────────────────────┬───────────────┘
               │                               │
               ▼                               ▼
┌──────────────────────────┐   ┌──────────────────────────────┐
│  Next.js 16 (Frontend)   │   │  Supabase                    │
│  - App Router (SSR/CSR)  │   │  - Auth (Magic Link)         │
│  - Tailwind CSS 4        │   │  - PostgreSQL DB              │
│  - React 19              │   │  - RLS Policies               │
│  Port: 3000              │   └──────────────────────────────┘
└──────────────┬───────────┘
               │ HTTP (REST / SSE)
               ▼
┌──────────────────────────────────────────────────────────────┐
│  FastAPI (Backend)  Port: 8000                                │
│  ┌────────────┐  ┌────────────┐  ┌─────────────────────────┐│
│  │ /api/news  │  │ /api/policy│  │ /api/stock              ││
│  │ 뉴스 수집   │  │ 정책 분석   │  │ 시세/차트/SSE 분석       ││
│  └─────┬──────┘  └─────┬──────┘  └──────┬──────────────────┘│
│        │               │                │                    │
│  ┌─────┴───────────────┴────────────────┴──────────────────┐│
│  │              Core Services                               ││
│  │  gemini_service.py  │  stock_service.py  │  news_service ││
│  │  generic_cache_service.py  │  warmup_service.py          ││
│  └─────┬───────────────┬────────────────┬──────────────────┘│
└────────┼───────────────┼────────────────┼────────────────────┘
         │               │                │
         ▼               ▼                ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ Google       │ │ finance-     │ │ 뉴스/정책     │
│ Gemini API   │ │ datareader   │ │ 데이터 소스   │
└──────────────┘ └──────────────┘ └──────────────┘
```

### 2.2 Data Flow

```
[사용자 요청] → [Next.js 페이지] → [FastAPI 엔드포인트]
    → [데이터 소스 수집] → [Gemini AI 분석] → [Supabase 캐싱]
    → [JSON 응답 또는 SSE 스트림] → [React 컴포넌트 렌더링]

[서버 시작] → [warmup_service: 4개 테마 콤보 사전 계산]
    → [background tasks: 10분/4시간 주기 자동 갱신]
```

### 2.3 Dependencies

| Component | Depends On | Purpose |
|-----------|-----------|---------|
| Frontend | FastAPI Backend | 주식 데이터, AI 분석 결과, SSE 스트림 |
| Frontend | Supabase | 인증, 사용자 데이터 |
| Backend | Gemini API | AI 텍스트 분석/요약 |
| Backend | finance-datareader | 한국 주식 시세 데이터 |
| Backend | Supabase | 분석 결과 캐싱, 사용자 데이터, generic_kv_cache |

---

## 3. Data Model

### 3.1 Entity Definitions

```typescript
// 사용자 (Supabase Auth 관리)
interface User {
  id: string;              // Supabase auth.users.id
  email: string;
  created_at: string;
}

// 글로벌 이슈 뉴스
interface NewsArticle {
  id: string;
  title: string;           // 뉴스 제목
  source: string;          // 출처 (Reuters, Bloomberg 등)
  url: string;             // 원문 링크
  published_at: string;    // 발행일
  ai_summary: string;      // Gemini AI 요약
  related_stocks: string[];// 관련 종목 코드
  category: 'global' | 'domestic' | 'policy';
  created_at: string;
}

// 정책 정보
interface PolicyInfo {
  id: string;
  title: string;           // 정책명
  department: string;      // 관련 부처
  description: string;     // 정책 설명
  effective_date: string;  // 시행일
  ai_analysis: string;     // Gemini AI 분석 (수혜/피해 분석)
  beneficiary_stocks: StockRecommendation[];
  created_at: string;
}

// 종목 추천 (정책 수혜주)
interface StockRecommendation {
  stock_code: string;      // 종목 코드 (예: "005930")
  stock_name: string;      // 종목명 (예: "삼성전자")
  reason: string;          // 추천 사유
  impact: 'positive' | 'negative' | 'neutral';
}

// 종목 시세 데이터
interface StockPrice {
  code: string;            // 종목 코드
  name: string;            // 종목명
  date: string;            // 날짜
  open: number;            // 시가
  high: number;            // 고가
  low: number;             // 저가
  close: number;           // 종가
  volume: number;          // 거래량
  change_rate: number;     // 등락률 (%)
}

// AI 종목 분석 항목 (카드 기반)
interface AnalysisItem {
  label: string;           // 분석 항목명 (예: "재무 건전성")
  result: string;          // 평가 결과 (예: "양호")
  reason: string;          // 판단 근거 (1-2문장)
  description: string;     // 상세 설명
}

// AI 종목 분석 리포트 (구조화 카드 기반, v0.2+ 변경)
interface StockAnalysis {
  id: string;
  stock_code: string;
  stock_name: string;
  items: AnalysisItem[];   // 분석 항목 카드 배열 (마크다운 ai_report 대체)
  overall_score: number;   // 종합 평점 (1-5)
  overall_comment: string; // 종합 코멘트
  sentiment: 'bullish' | 'bearish' | 'neutral';
  analyzed_at: string;
  expires_at: string;      // 캐시 만료 (24시간)
}

// 관심 종목
interface Watchlist {
  id: string;
  user_id: string;
  stock_code: string;
  stock_name: string;
  added_at: string;
}

// 테마 종목 (dashboard/theme-trend)
interface ThemeStock {
  code: string;
  name: string;
  change_rate: number;
  volume: number;
}

// 테마 그룹
interface ThemeGroup {
  theme: string;
  stocks: ThemeStock[];
}

// 키워드 피드 종목
interface KeywordStock {
  code: string;
  name: string;
  change_rate: number;
  news_count: number;
  keyword_match: string[];
}
```

### 3.2 Entity Relationships

```
[User] 1 ──── N [Watchlist]
                    │
[NewsArticle] N ────┤ (related_stocks로 연결)
                    │
[PolicyInfo] 1 ── N [StockRecommendation]
                    │
[StockPrice] ───────┘ (stock_code로 연결)
     │
[StockAnalysis] 1 ── 1 [StockPrice] (stock_code)
     └── items: AnalysisItem[] (카드 배열)
```

### 3.3 Database Schema (Supabase PostgreSQL)

```sql
-- 뉴스 캐시 테이블
CREATE TABLE news_cache (
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

-- 정책 정보 테이블 (실제 구현: policy_news)
CREATE TABLE policy_news (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title TEXT NOT NULL,
  department TEXT,
  description TEXT,
  effective_date DATE,
  ai_analysis TEXT,
  beneficiary_stocks JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- AI 분석 캐시 테이블
CREATE TABLE analysis_cache (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  stock_code TEXT NOT NULL,
  stock_name TEXT NOT NULL,
  ai_report TEXT,
  sentiment TEXT CHECK (sentiment IN ('bullish', 'bearish', 'neutral')),
  key_factors TEXT[],
  analyzed_at TIMESTAMPTZ DEFAULT NOW(),
  expires_at TIMESTAMPTZ DEFAULT (NOW() + INTERVAL '24 hours')
);

CREATE INDEX idx_analysis_stock ON analysis_cache(stock_code);
CREATE INDEX idx_analysis_expires ON analysis_cache(expires_at);

-- 관심 종목 테이블
CREATE TABLE watchlist (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  stock_code TEXT NOT NULL,
  stock_name TEXT NOT NULL,
  added_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(user_id, stock_code)
);

-- RLS 정책
ALTER TABLE watchlist ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can manage own watchlist"
  ON watchlist FOR ALL
  USING (auth.uid() = user_id);

-- 범용 KV 캐시 테이블 (v0.3 신규)
-- 테마 트렌드, 대시보드 요약 등 다목적 Supabase 영속 캐시
CREATE TABLE generic_kv_cache (
  cache_key TEXT PRIMARY KEY,
  data JSONB NOT NULL,
  expires_at TIMESTAMPTZ NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_gkv_expires ON generic_kv_cache(expires_at);
-- 용도: theme_trend_{period}_{sort}, dashboard_summary
-- TTL: 테마트렌드 daily=30분/weekly=4시간, 대시보드=5분
```

---

## 4. API Specification

### 4.1 Backend API (FastAPI) Endpoint List

| Method | Path | Description | Auth | Version |
|--------|------|-------------|------|---------|
| GET | `/api/news` | 글로벌 이슈 뉴스 목록 | Optional | v0.1 |
| GET | `/api/news/summary` | 뉴스 AI 요약 + 관련 종목 (`?id=...`) | Optional | v0.1 |
| GET | `/api/policy` | 정부 정책 목록 | Optional | v0.1 |
| GET | `/api/policy/{id}/analysis` | 정책 수혜주 AI 분석 | Optional | v0.1 |
| GET | `/api/stock/search` | 종목 검색 | Optional | v0.1 |
| GET | `/api/stock/{code}/price` | 종목 시세 조회 | Optional | v0.1 |
| GET | `/api/stock/{code}/chart` | 종목 차트 데이터 | Optional | v0.1 |
| GET | `/api/stock/{code}/analysis` | AI 종목 분석 (REST, 24h 캐싱) | Optional | v0.1 |
| GET | `/api/stock/{code}/analysis/stream` | AI 종목 분석 SSE 스트리밍 | Optional | v0.3 NEW |
| GET | `/api/dashboard` | 대시보드 요약 데이터 (5분 캐싱) | Optional | v0.1 |
| GET | `/api/dashboard/theme-trend` | 테마별 종목 트렌드 | Optional | v0.2 NEW |
| GET | `/api/dashboard/keyword-feed` | 커스텀 키워드 피드 | Optional | v0.2 NEW |
| POST | `/api/cron/cleanup-generic` | generic_kv_cache 만료 데이터 정리 | Server | v0.3 NEW |

### 4.2 Detailed API Specifications

#### `GET /api/news`

뉴스 목록 조회 (최신순, 페이지네이션)

**Query Parameters:**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| category | string | all | global / domestic / policy |
| page | int | 1 | 페이지 번호 |
| limit | int | 10 | 페이지당 개수 |

**Response (200):**
```json
{
  "items": [
    {
      "id": "uuid",
      "title": "美 금리 인하 기대감 고조",
      "source": "Reuters",
      "published_at": "2026-02-14T09:00:00Z",
      "category": "global",
      "ai_summary": null,
      "related_stocks": []
    }
  ],
  "total": 50,
  "page": 1,
  "limit": 10
}
```

#### `GET /api/news/summary`

특정 뉴스의 AI 요약 및 관련 종목 조회 (Gemini 호출)

**Note**: URL이 `/api/news/{id}/summary` 경로 파라미터 방식에서 `/api/news/summary?id=...` 쿼리 파라미터 방식으로 변경됨. 뉴스 ID가 URL 문자열을 포함할 수 있어 라우팅 이슈 방지 목적.

**Query Parameters:**
| Param | Type | Description |
|-------|------|-------------|
| id | string | 뉴스 ID |

**Response (200):**
```json
{
  "id": "uuid",
  "title": "美 금리 인하 기대감 고조",
  "ai_summary": "미국 연준의 금리 인하 기대감이 ...",
  "related_stocks": [
    { "stock_code": "005930", "stock_name": "삼성전자", "reason": "수출 기업 수혜" }
  ]
}
```

#### `GET /api/stock/{code}/price`

종목 시세 조회

**Response (200):**
```json
{
  "code": "005930",
  "name": "삼성전자",
  "current_price": 72500,
  "change": 1500,
  "change_rate": 2.11,
  "volume": 15234567,
  "high": 73000,
  "low": 71000
}
```

#### `GET /api/stock/{code}/chart`

차트 데이터 조회

**Query Parameters:**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| period | string | 3m | 1m / 3m / 6m / 1y |
| interval | string | daily | daily / weekly |

**Response (200):**
```json
{
  "code": "005930",
  "name": "삼성전자",
  "period": "3m",
  "data": [
    { "date": "2026-02-14", "open": 71000, "high": 73000, "low": 70500, "close": 72500, "volume": 15234567 }
  ]
}
```

#### `GET /api/stock/{code}/analysis`

AI 종목 분석 리포트 (Gemini, 24시간 캐싱) - REST 방식

**Response (200):**
```json
{
  "stock_code": "005930",
  "stock_name": "삼성전자",
  "sentiment": "bullish",
  "items": [
    {
      "label": "재무 건전성",
      "result": "양호",
      "reason": "부채비율 30% 수준으로 안정적",
      "description": "자기자본비율이 업종 평균을 상회하며..."
    }
  ],
  "overall_score": 4,
  "overall_comment": "AI 반도체 수요 확대로 중장기 전망 긍정적",
  "analyzed_at": "2026-02-17T10:00:00Z"
}
```

**Note**: v0.2 변경 - `ai_report` (마크다운 문자열) 및 `key_factors` 제거, `items: AnalysisItem[]` + `overall_score` + `overall_comment` 구조로 대체. 카드 기반 UI에 최적화된 형식.

#### `GET /api/stock/{code}/analysis/stream` (v0.3 신규)

AI 종목 분석 SSE(Server-Sent Events) 스트리밍. 3단계 진행 이벤트 전송.

**Response**: `text/event-stream`

**SSE Events:**
```
event: status
data: {"step": 1, "message": "종목 데이터 수집 중..."}

event: status
data: {"step": 2, "message": "뉴스 수집 중..."}

event: status
data: {"step": 3, "message": "AI 분석 중..."}

event: done
data: { /* StockAnalysis 전체 응답 */ }

event: error
data: {"code": "RATE_LIMITED", "message": "요청이 너무 많습니다"}
```

**Cache hit**: 캐시 적중 시 즉시 `done` 이벤트 전송 (status 이벤트 없음)

**Headers:**
```
Content-Type: text/event-stream
Cache-Control: no-cache
X-Accel-Buffering: no
```

#### `GET /api/dashboard`

대시보드 요약 데이터 (5분 Supabase 캐싱)

**Response (200):**
```json
{
  "top_news": [{ "id": "uuid", "title": "...", "category": "global" }],
  "hot_policies": [{ "id": "uuid", "title": "...", "department": "기획재정부" }],
  "market_summary": {
    "kospi": { "value": 2650.32, "change_rate": 1.2 },
    "kosdaq": { "value": 870.15, "change_rate": 0.8 }
  }
}
```

**Note**: v0.2 변경 - `trending_stocks` 필드 제거. `/api/dashboard/theme-trend`로 대체됨.

#### `GET /api/dashboard/theme-trend` (v0.2 신규)

pykrx 테마별 종목 트렌드. Supabase 캐싱 (daily=30분, weekly=4시간).

**Query Parameters:**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| period | string | daily | daily / weekly |
| sort | string | change_rate | change_rate / volume |

**Response (200):**
```json
{
  "groups": [
    {
      "theme": "반도체",
      "stocks": [
        { "code": "005930", "name": "삼성전자", "change_rate": 2.11, "volume": 15234567 }
      ]
    }
  ],
  "trade_date": "2026-02-17",
  "period": "daily"
}
```

#### `GET /api/dashboard/keyword-feed` (v0.2 신규)

사용자 커스텀 키워드 기반 종목/뉴스/정책 피드.

**Query Parameters:**
| Param | Type | Description |
|-------|------|-------------|
| keywords | string | 쉼표 구분 키워드 (예: "반도체,AI,배터리") |

**Response (200):**
```json
{
  "stocks": [
    { "code": "005930", "name": "삼성전자", "change_rate": 2.11, "news_count": 5, "keyword_match": ["반도체"] }
  ],
  "news": [...],
  "policies": [...]
}
```

#### `POST /api/cron/cleanup-generic` (v0.3 신규)

`generic_kv_cache` 테이블의 만료 데이터 정리 (7일 이상 만료된 항목 삭제).

**Response (200):**
```json
{ "ok": true, "deleted": 12 }
```

---

## 5. UI/UX Design

### 5.1 Page Structure

```
┌──────────────────────────────────────────────────┐
│  Header (NavBar)                                  │
│  [주식콕 로고]  [이슈] [정책] [종목] [관심종목]    │
├──────────────────────────────────────────────────┤
│                                                    │
│  Page Content (각 라우트별)                         │
│                                                    │
├──────────────────────────────────────────────────┤
│  Footer (간단한 카피라이트)                          │
└──────────────────────────────────────────────────┘
```

### 5.2 Page List & User Flow

```
/ (랜딩) ──→ /login (로그인) ──→ /dashboard (대시보드)
                                      │
                          ┌───────────┼──────────────┐
                          ▼           ▼              ▼
                    /issues      /policy      /stock/search
                    (글로벌 이슈)  (정책 분석)   (종목 검색)
                          │           │              │
                          ▼           ▼              ▼
                  /issues/[id]  /policy/[id]  /stock/[code]
                  (뉴스 상세)    (정책 상세)    (종목 상세+차트)
                                                     │
                                                     ▼
                                          /stock/[code]/analysis
                                          (SSE 스트리밍 분석 페이지)
                                   /watchlist (관심 종목 관리)
```

### 5.3 Component List

| Component | Location | Responsibility |
|-----------|----------|----------------|
| `NavBar` | `components/layout/NavBar.tsx` | 상단 네비게이션 |
| `Footer` | `components/layout/Footer.tsx` | 하단 푸터 |
| `NewsCard` | `components/news/NewsCard.tsx` | 뉴스 카드 UI |
| `NewsList` | `components/news/NewsList.tsx` | 뉴스 목록 |
| `AiSummary` | `components/news/AiSummary.tsx` | AI 요약 표시 |
| `PolicyCard` | `components/policy/PolicyCard.tsx` | 정책 카드 UI |
| `PolicyAnalysis` | `components/policy/PolicyAnalysis.tsx` | 수혜주 분석 표시 |
| `StockSearchBar` | `components/stock/StockSearchBar.tsx` | 종목 검색 입력 |
| `StockChart` | `components/stock/StockChart.tsx` | 주가 차트 (lightweight-charts) |
| `StockInfo` | `components/stock/StockInfo.tsx` | 종목 기본 정보 |
| `StockAnalysisReport` | `components/stock/StockAnalysisReport.tsx` | AI 분석 리포트 (카드 기반) |
| `StockSearchResultCard` | `components/stock/StockSearchResultCard.tsx` | 검색 결과 카드 |
| `DashboardSummary` | `components/dashboard/DashboardSummary.tsx` | 대시보드 요약 |
| `MarketOverview` | `components/dashboard/MarketOverview.tsx` | 시장 개요 (KOSPI/KOSDAQ) |
| `ThemeTrend` | `components/dashboard/ThemeTrend.tsx` | Recharts 트리맵 테마 트렌드 |
| `KeywordFeed` | `components/dashboard/KeywordFeed.tsx` | 커스텀 키워드 피드 |
| `ThemeMap` | `components/dashboard/ThemeMap.tsx` | 테마맵 시각화 |
| `ThemeDetail` | `components/dashboard/ThemeDetail.tsx` | 테마 상세 정보 |
| `LoadingSpinner` | `components/ui/LoadingSpinner.tsx` | 로딩 스피너 |
| `ErrorMessage` | `components/ui/ErrorMessage.tsx` | 에러 메시지 |

### 5.4 Design Tokens (기존 테마 확장)

```css
/* globals.css - 확장 */
@theme inline {
  --color-navy: #001F3F;
  --color-skyblue: #0074D9;
  --color-navy-light: #003366;
  --color-positive: #22C55E;    /* 상승 (초록) */
  --color-negative: #EF4444;    /* 하락 (빨강) */
  --color-neutral: #6B7280;     /* 보합 (회색) */
  --color-card-bg: rgba(255, 255, 255, 0.1);
  --color-card-border: rgba(255, 255, 255, 0.2);
}
```

---

## 6. Error Handling

### 6.1 Backend Error Response Format

```json
{
  "error": {
    "code": "NEWS_FETCH_FAILED",
    "message": "뉴스 데이터를 가져올 수 없습니다.",
    "details": { "source": "reuters", "status": 503 }
  }
}
```

### 6.2 Error Codes

| Code | HTTP | Message | Handling |
|------|------|---------|----------|
| `AUTH_REQUIRED` | 401 | 로그인이 필요합니다 | 로그인 페이지 리다이렉트 |
| `NEWS_FETCH_FAILED` | 502 | 뉴스를 가져올 수 없습니다 | 캐시 데이터 표시 / 재시도 |
| `STOCK_NOT_FOUND` | 404 | 종목을 찾을 수 없습니다 | 검색 페이지로 안내 |
| `AI_ANALYSIS_FAILED` | 503 | AI 분석 중 오류 | 재시도 버튼 표시 |
| `RATE_LIMITED` | 429 | 요청이 너무 많습니다 | 잠시 후 재시도 안내 (30초) |

### 6.3 SSE Error Events

SSE 스트리밍 중 오류는 `event: error` 형식으로 전송:

| SSE Error Code | Trigger | Frontend Handling |
|----------------|---------|------------------|
| `NOT_FOUND` | 종목 코드 없음 | ErrorMessage 표시 |
| `RATE_LIMITED` | Gemini 429/Resource exhausted | "30초 후 재시도" 메시지 |
| `ANALYSIS_ERROR` | 기타 AI 분석 실패 | Retry 버튼 표시 |

---

## 7. Security Considerations

- [x] Supabase Auth (Magic Link) - 구현 완료
- [x] FastAPI CORS 설정 (프론트엔드 도메인만 허용)
- [x] Gemini API Key 서버사이드에서만 사용 (.env)
- [x] Supabase RLS로 watchlist 사용자 격리
- [x] API Rate Limiting (slowapi, 15/minute on AI endpoints)
- [ ] SSE 엔드포인트 Rate Limiting (미구현 - 개선 필요)
- [ ] 입력 유효성 검증 (종목 코드 형식 등)

---

## 8. Backend Project Structure

```
backend/
├── app/
│   ├── main.py                       # FastAPI 앱 엔트리 (lifespan 컨텍스트 포함)
│   ├── config.py                     # 설정 (환경변수 로드)
│   ├── errors.py                     # 구조화 에러 응답 시스템
│   ├── limiter.py                    # slowapi Rate Limiter 설정
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── news.py                   # /api/news 라우터
│   │   ├── policy.py                 # /api/policy 라우터
│   │   ├── stock.py                  # /api/stock 라우터 (REST + SSE 스트림)
│   │   ├── dashboard.py              # /api/dashboard 라우터 (theme-trend, keyword-feed 포함)
│   │   └── cron.py                   # /api/cron 라우터 (캐시 정리)
│   ├── services/
│   │   ├── __init__.py
│   │   ├── gemini_service.py         # Gemini AI 호출
│   │   ├── news_service.py           # 뉴스 수집/처리
│   │   ├── policy_service.py         # 정책 수집/처리
│   │   ├── stock_service.py          # 주식 데이터 (finance-datareader)
│   │   ├── generic_cache_service.py  # Supabase 범용 KV 캐시 (v0.3 신규)
│   │   └── warmup_service.py         # 서버 시작 시 캐시 워밍업 (v0.3 신규)
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py                # Pydantic 스키마
│   └── utils/
│       ├── __init__.py
│       └── supabase_client.py        # Supabase 클라이언트
├── requirements.txt
└── .env
```

### 8.1 Server Lifecycle (v0.3 신규)

```python
# main.py - lifespan 패턴
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: 비차단 워밍업 + 백그라운드 태스크 시작
    asyncio.create_task(warmup_all())     # 4개 테마 콤보 사전 계산
    bg_tasks = await start_background_tasks()  # 10분/4시간 자동 갱신
    yield
    # Shutdown: 모든 태스크 정상 종료
    for task in bg_tasks:
        task.cancel()
    await asyncio.gather(*bg_tasks, return_exceptions=True)
```

---

## 9. Frontend Project Structure

```
frontend/
├── app/
│   ├── layout.tsx                    # 루트 레이아웃 (NavBar, Footer)
│   ├── page.tsx                      # 랜딩 페이지 (Done)
│   ├── globals.css                   # 글로벌 스타일 (Done)
│   ├── login/
│   │   └── page.tsx                  # 로그인 (Done)
│   ├── auth/
│   │   └── callback/route.ts         # Auth 콜백 (Done)
│   └── (app)/                        # 인증 필요 라우트 그룹
│       ├── dashboard/
│       │   └── page.tsx              # 대시보드
│       ├── issues/
│       │   ├── page.tsx              # 글로벌 이슈 목록
│       │   └── [id]/page.tsx         # 뉴스 상세 + AI 요약
│       ├── policy/
│       │   ├── page.tsx              # 정책 목록
│       │   └── [id]/page.tsx         # 정책 상세 + 수혜주
│       ├── stock/
│       │   ├── page.tsx              # 종목 검색
│       │   └── [code]/
│       │       ├── page.tsx          # 종목 상세 + 차트
│       │       └── analysis/
│       │           └── page.tsx      # AI 분석 (SSE 스트리밍, v0.3 신규)
│       └── watchlist/
│           └── page.tsx              # 관심 종목 관리 (v0.2 신규)
├── components/
│   ├── layout/
│   │   ├── NavBar.tsx
│   │   └── Footer.tsx
│   ├── news/
│   │   ├── NewsCard.tsx
│   │   ├── NewsList.tsx
│   │   └── AiSummary.tsx
│   ├── policy/
│   │   ├── PolicyCard.tsx
│   │   └── PolicyAnalysis.tsx
│   ├── stock/
│   │   ├── StockSearchBar.tsx
│   │   ├── StockChart.tsx
│   │   ├── StockInfo.tsx
│   │   ├── StockAnalysisReport.tsx
│   │   └── StockSearchResultCard.tsx
│   ├── dashboard/
│   │   ├── DashboardSummary.tsx
│   │   ├── MarketOverview.tsx
│   │   ├── ThemeTrend.tsx            # Recharts 트리맵
│   │   ├── KeywordFeed.tsx           # 커스텀 키워드 피드
│   │   ├── ThemeMap.tsx              # 테마맵 시각화
│   │   └── ThemeDetail.tsx           # 테마 상세
│   └── ui/
│       ├── LoadingSpinner.tsx
│       └── ErrorMessage.tsx
├── lib/
│   ├── api.ts                        # FastAPI 호출 클라이언트 (SSE generator 포함)
│   └── customKeywords.ts             # 커스텀 키워드 관리 (v0.2 신규)
├── utils/
│   └── supabase/                     # (Done)
├── types/
│   └── index.ts                      # TypeScript 타입 정의
└── package.json
```

---

## 10. Coding Conventions

### 10.1 Naming Conventions

| Target | Rule | Example |
|--------|------|---------|
| Components | PascalCase | `NewsCard`, `StockChart` |
| Pages | page.tsx (Next.js convention) | `app/issues/page.tsx` |
| API Routes | snake_case (Python) | `news_service.py` |
| Functions (TS) | camelCase | `fetchNewsById()` |
| Functions (Python) | snake_case | `get_stock_price()` |
| Types | PascalCase | `NewsArticle`, `StockPrice` |
| CSS Variables | kebab-case | `--color-navy-light` |

### 10.2 Import Order (Frontend)

```typescript
// 1. React / Next.js
import { useState, useEffect } from 'react';
import Link from 'next/link';

// 2. External libraries
import { TrendingUp } from 'lucide-react';

// 3. Internal modules
import { fetchNews } from '@/lib/api';
import type { NewsArticle } from '@/types';

// 4. Components
import { NewsCard } from '@/components/news/NewsCard';

// 5. Styles (if any)
```

### 10.3 Environment Variables

| Variable | Purpose | Scope | Status |
|----------|---------|-------|:------:|
| `NEXT_PUBLIC_SUPABASE_URL` | Supabase URL | Client | Done |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase Key | Client | Done |
| `NEXT_PUBLIC_API_URL` | FastAPI URL (http://localhost:8000) | Client | Done |
| `GEMINI_API_KEY` | Google Gemini API Key | Server (Python) | Done |
| `SUPABASE_URL` | Supabase URL (Backend용) | Server (Python) | Done |
| `SUPABASE_SERVICE_KEY` | Supabase Service Role Key | Server (Python) | Done |

---

## 11. Implementation Order

### 11.1 Phase 1: 인프라 세팅 (완료)

1. [x] Frontend 초기 세팅 (Next.js + Tailwind)
2. [x] Supabase Auth (Magic Link)
3. [x] Backend 프로젝트 구조 세팅 (routers, services, models)
4. [x] FastAPI CORS 설정
5. [x] Frontend API 클라이언트 (`lib/api.ts`)
6. [x] 공통 레이아웃 (NavBar, Footer)
7. [x] TypeScript 타입 정의 (`types/index.ts`)

### 11.2 Phase 2: 글로벌 이슈 (완료)

8. [x] `news_service.py` - 뉴스 데이터 수집
9. [x] `gemini_service.py` - AI 요약 서비스
10. [x] `/api/news` 라우터
11. [x] `NewsCard`, `NewsList` 컴포넌트
12. [x] `/issues` 페이지
13. [x] `/issues/[id]` 페이지 (AI 요약)

### 11.3 Phase 3: 정책 분석 (완료)

14. [x] `policy_service.py` - 정책 데이터 수집
15. [x] `/api/policy` 라우터
16. [x] `PolicyCard`, `PolicyAnalysis` 컴포넌트
17. [x] `/policy` 페이지
18. [x] `/policy/[id]` 페이지 (수혜주)

### 11.4 Phase 4: 종목 분석 (완료)

19. [x] `stock_service.py` - finance-datareader 연동
20. [x] `/api/stock` 라우터
21. [x] `StockSearchBar`, `StockInfo` 컴포넌트
22. [x] `StockChart` 컴포넌트 (lightweight-charts)
23. [x] `/stock` 검색 페이지
24. [x] `/stock/[code]` 상세 페이지

### 11.5 Phase 5: 대시보드 (완료)

25. [x] `/api/dashboard` 라우터
26. [x] `DashboardSummary`, `MarketOverview` 컴포넌트
27. [x] `/dashboard` 페이지
28. [x] 관심 종목 (Watchlist) CRUD + `/watchlist` 페이지

### 11.6 Phase 6: 고급 기능 (완료, v0.2-v0.3)

29. [x] `generic_cache_service.py` - Supabase KV 캐시 서비스
30. [x] `warmup_service.py` - 서버 시작 캐시 워밍업 + 백그라운드 갱신
31. [x] `/api/dashboard/theme-trend` - pykrx 테마 트렌드
32. [x] `/api/dashboard/keyword-feed` - 커스텀 키워드 피드
33. [x] `ThemeTrend`, `KeywordFeed` 컴포넌트
34. [x] SSE 스트리밍 분석 (`/api/stock/{code}/analysis/stream`)
35. [x] SSE 클라이언트 (`fetchStockAnalysisStream` in `lib/api.ts`)
36. [x] `/stock/[code]/analysis` SSE 진행 표시 페이지
37. [x] `POST /api/cron/cleanup-generic` 만료 캐시 정리

### 11.7 Chart Library Decision

| Library | Pros | Cons | Selected |
|---------|------|------|:--------:|
| **lightweight-charts** | 금융 차트 전문, 캔들차트 지원, 경량 | 커스터마이징 제한적 | **V** |
| recharts | React 친화적, 범용 | 금융 차트 부족 | (테마 트리맵에 활용) |
| chart.js | 범용, 문서 풍부 | 금융 차트 직접 구현 필요 | |

---

## 12. Design Decisions & Intentional Divergences

실제 구현 과정에서 설계 대비 변경된 항목과 그 이유:

| # | Item | Original Design | Actual Implementation | Reason |
|---|------|-----------------|----------------------|--------|
| 1 | News summary URL | `GET /api/news/{id}/summary` | `GET /api/news/summary?id=...` | 뉴스 ID에 URL 특수문자 포함 가능, 라우팅 이슈 방지 |
| 2 | Stock analysis format | `ai_report` (마크다운) + `key_factors` | `items: AnalysisItem[]` + `overall_score` | 카드 기반 UI에 최적화, 구조화 데이터로 일관성 향상 |
| 3 | Dashboard `trending_stocks` | 포함 | 제거 | `/api/dashboard/theme-trend`로 대체, 더 풍부한 테마 데이터 제공 |
| 4 | Policy table name | `policy_cache` | `policy_news` | 실제 데이터 특성을 더 잘 반영하는 이름 |
| 5 | Cache storage | 인메모리 dict | Supabase `generic_kv_cache` | 서버 재시작 시 캐시 유지, 영속성 확보 |
| 6 | NavBar items | Login/Profile | Watchlist (관심종목) | 인증 후 사용자 핵심 기능 우선 표시 |
| 7 | Route group | 없음 | `(app)/` 그룹 | Next.js 레이아웃 격리, 인증 필요 페이지 구분 |

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 0.1 | 2026-02-14 | Initial draft | User |
| 0.3 | 2026-02-17 | Major update: new endpoints (theme-trend, keyword-feed, SSE stream, cron cleanup), updated response formats (StockAnalysis, Dashboard), generic_kv_cache table, warmup_service, backend/frontend structure, intentional divergences documented | User |
