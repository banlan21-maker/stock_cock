# Portfolio Analysis Design Document

> **Feature**: portfolio-analysis
> **Status**: Draft
> **Date**: 2026-02-18
> **Ref**: `docs/01-plan/features/portfolio-analysis.plan.md`

---

## 1. 개요

보유 주식 포트폴리오를 입력하고 현재가 기준 수익률을 추적하며,
AI(Gemini) 기반 포트폴리오 진단을 SSE 스트리밍으로 제공하는 기능.

---

## 2. 데이터베이스 설계

### 2.1 Supabase 테이블: `portfolio_holdings`

```sql
CREATE TABLE portfolio_holdings (
  id          uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     uuid        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  stock_code  text        NOT NULL,
  stock_name  text        NOT NULL,
  quantity    numeric     NOT NULL CHECK (quantity > 0),
  avg_price   numeric     NOT NULL CHECK (avg_price > 0),
  bought_at   date,
  created_at  timestamptz DEFAULT now(),
  updated_at  timestamptz DEFAULT now()
);

-- RLS 활성화
ALTER TABLE portfolio_holdings ENABLE ROW LEVEL SECURITY;

CREATE POLICY "users_manage_own_holdings"
  ON portfolio_holdings
  FOR ALL
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

-- 인덱스
CREATE INDEX idx_ph_user ON portfolio_holdings(user_id);
```

### 2.2 캐시 테이블 (기존 `generic_kv_cache` 재사용)

- AI 진단 결과: `portfolio_analysis:{user_id}` — TTL 24h

---

## 3. 백엔드 API 설계

### 3.1 라우터 파일

`backend/app/routers/portfolio.py`

### 3.2 엔드포인트 명세

#### GET `/api/portfolio/holdings`
보유 종목 목록 + 현재가 병렬 조회

**Response**
```json
{
  "holdings": [
    {
      "id": "uuid",
      "stock_code": "005930",
      "stock_name": "삼성전자",
      "quantity": 10,
      "avg_price": 75000,
      "current_price": 80000,
      "profit_loss": 50000,
      "profit_rate": 6.67,
      "eval_amount": 800000,
      "bought_at": "2024-01-15"
    }
  ],
  "summary": {
    "total_invest": 750000,
    "total_eval": 800000,
    "total_profit_loss": 50000,
    "total_profit_rate": 6.67
  }
}
```

**구현 포인트**
- Supabase에서 보유 종목 조회 (user_id RLS 적용)
- `asyncio.gather()`로 현재가 병렬 조회
- 현재가 조회 실패 시 `current_price: null` 처리

#### POST `/api/portfolio/holdings`
종목 추가

**Request Body**
```json
{
  "stock_code": "005930",
  "stock_name": "삼성전자",
  "quantity": 10,
  "avg_price": 75000,
  "bought_at": "2024-01-15"
}
```

**Response**: 생성된 holding 객체

#### PUT `/api/portfolio/holdings/{id}`
종목 수정 (수량, 평균 매입가, 매입일)

**Request Body**
```json
{
  "quantity": 15,
  "avg_price": 73000,
  "bought_at": "2024-01-10"
}
```

#### DELETE `/api/portfolio/holdings/{id}`
종목 삭제

#### GET `/api/portfolio/analysis/stream`
AI 포트폴리오 진단 — SSE 스트리밍

**이벤트 흐름**
```
event: status  → {"step": 1, "message": "포트폴리오 데이터 수집 중..."}
event: status  → {"step": 2, "message": "AI 진단 중..."}
event: done    → { portfolio_ai_analysis 전체 결과 }
event: error   → {"message": "...", "code": "..."}
```

**done 이벤트 payload**
```json
{
  "user_id": "uuid",
  "total_stocks": 5,
  "risk_level": "medium",
  "sector_analysis": [
    { "sector": "반도체", "ratio": 45.2, "comment": "쏠림 위험" }
  ],
  "rebalancing": [
    { "action": "reduce", "stock_code": "005930", "reason": "비중 과다" }
  ],
  "overall_comment": "전반적으로 안정적이나...",
  "overall_score": 3,
  "analyzed_at": "2026-02-18T10:00:00Z"
}
```

---

## 4. 서비스 레이어 설계

### 4.1 `backend/app/services/portfolio_service.py`

```python
def get_user_holdings(user_id: str) -> list[dict]
    """Supabase에서 보유 종목 조회."""

def add_holding(user_id: str, data: dict) -> dict
    """Supabase에 보유 종목 삽입."""

def update_holding(holding_id: str, user_id: str, data: dict) -> dict
    """보유 종목 수정 (user_id 검증 포함)."""

def delete_holding(holding_id: str, user_id: str) -> None
    """보유 종목 삭제."""

async def get_holdings_with_price(user_id: str) -> dict
    """보유 종목 + 현재가 병렬 조회 + 수익률 계산."""

def calculate_profit(avg_price, current_price, quantity) -> dict
    """profit_loss, profit_rate, eval_amount 계산."""
```

### 4.2 `backend/app/services/portfolio_ai_service.py`

```python
async def analyze_portfolio_stream(user_id: str) -> AsyncGenerator[str, None]
    """포트폴리오 AI 진단 SSE 스트림 생성.
    캐시 히트 → 즉시 done 반환
    캐시 미스 → Gemini 분석 → 캐시 저장 → done 반환
    TTL: 24h (generic_kv_cache 재사용)
    """

def build_portfolio_prompt(holdings_with_price: list[dict]) -> str
    """Gemini 프롬프트 생성."""
```

---

## 5. 프론트엔드 설계

### 5.1 파일 구조

```
frontend/
├── app/(app)/portfolio/
│   ├── page.tsx                  # 포트폴리오 메인 페이지
│   └── analysis/
│       └── page.tsx              # AI 진단 페이지
├── components/portfolio/
│   ├── PortfolioSummaryCard.tsx  # 총 평가금액, 손익 카드
│   ├── HoldingsTable.tsx         # 종목별 수익률 테이블
│   ├── PortfolioPieChart.tsx     # 종목 비중 파이 차트
│   ├── AddHoldingModal.tsx       # 종목 추가/수정 모달
│   └── AIAnalysisReport.tsx      # AI 진단 결과 컴포넌트
├── lib/
│   └── portfolio.ts              # API 클라이언트 함수
└── types/
    └── index.ts                  # PortfolioHolding 등 타입 추가
```

### 5.2 TypeScript 타입 (`types/index.ts` 추가)

```typescript
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
```

### 5.3 API 클라이언트 (`lib/portfolio.ts`)

```typescript
// Supabase 직접 접근 (CRUD)
export async function getPortfolioHoldings(): Promise<PortfolioResponse>
export async function addHolding(data: PortfolioAddRequest): Promise<PortfolioHolding>
export async function updateHolding(id: string, data: Partial<PortfolioAddRequest>): Promise<PortfolioHolding>
export async function deleteHolding(id: string): Promise<void>

// FastAPI 접근 (현재가 포함 목록, AI 분석)
export async function fetchPortfolioWithPrice(): Promise<PortfolioResponse>
export async function* fetchPortfolioAnalysisStream(): AsyncGenerator<SSEEvent>
```

**인증 방식**: Supabase 세션의 `access_token`을 `Authorization: Bearer` 헤더로 전달

### 5.4 컴포넌트 상세

#### `PortfolioSummaryCard.tsx`
```
┌────────────────────────────────────────┐
│ 내 포트폴리오                           │
│                                        │
│ 총 평가금액        총 손익              │
│ ₩8,250,000        +₩320,000 (+4.04%)  │
└────────────────────────────────────────┘
```
- 손익 양수: 빨간색(red-400), 음수: 파란색(blue-400) (한국식)

#### `HoldingsTable.tsx`
```
종목명     코드    수량    매입가     현재가    손익     수익률   비중
삼성전자   005930  10      75,000    80,000  +50,000  +6.67%  48.5%
SK하이닉스 000660   5     120,000   135,000  +75,000  +12.5%  41.0%
[추가] 버튼
```
- 수정/삭제 버튼: 행 hover 시 표시
- 스켈레톤 로딩

#### `PortfolioPieChart.tsx`
- recharts `PieChart` 사용 (기존 chart 라이브러리와 통일)
- 종목별 비중 (eval_amount 기준)
- 5개 이상 → 상위 4개 + 기타

#### `AddHoldingModal.tsx`
- 종목 코드 검색 (기존 `fetchStockSearch` 활용)
- 수량, 평균매입가, 매입일 입력
- 실시간 예상 평가금액 미리보기

#### `AIAnalysisReport.tsx`
- SSE 스트리밍 소비 (기존 `StockAnalysisReport` 패턴 동일)
- 진행 상태 표시 (step 1, 2)
- 리스크 레벨 뱃지 (low/medium/high)
- 섹터 분석 테이블
- 리밸런싱 추천 리스트

### 5.5 라우팅 & 네비게이션

- NavBar에 포트폴리오 메뉴 추가: `/portfolio` (PieChart 아이콘)
- 포트폴리오 메인 페이지: `/portfolio`
- AI 진단 페이지: `/portfolio/analysis`

---

## 6. 인증/보안

### 6.1 백엔드 인증

FastAPI 엔드포인트에서 `Authorization: Bearer {supabase_access_token}` 헤더 검증:

```python
# backend/app/deps.py (신규)
from fastapi import Header, HTTPException
from app.supabase_client import supabase

async def get_current_user(authorization: str = Header(...)) -> dict:
    token = authorization.removeprefix("Bearer ").strip()
    result = supabase.auth.get_user(token)
    if not result.user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return {"user_id": result.user.id}
```

### 6.2 프론트엔드 인증

```typescript
// lib/portfolio.ts
import { createClient } from "@/lib/supabase/client";

async function getAuthHeaders() {
  const supabase = createClient();
  const { data: { session } } = await supabase.auth.getSession();
  return { Authorization: `Bearer ${session?.access_token}` };
}
```

---

## 7. 에러 처리

| 상황 | 처리 방법 |
|------|----------|
| 현재가 조회 실패 | `current_price: null` 반환, UI에 "-" 표시 |
| 보유 종목 없음 | 빈 상태 + "종목 추가" CTA |
| AI 진단 실패 | SSE `error` 이벤트 → Toast 에러 메시지 |
| 인증 만료 | 401 → 로그인 페이지 리다이렉트 |
| 타인 종목 수정 시도 | RLS에서 자동 차단 (403) |

---

## 8. 구현 순서 (Do Phase 가이드)

### Step 1: 백엔드 기반
1. Supabase `portfolio_holdings` 테이블 + RLS 생성
2. `backend/app/deps.py` — 인증 의존성
3. `backend/app/services/portfolio_service.py`
4. `backend/app/routers/portfolio.py` — CRUD + holdings with price
5. `main.py`에 portfolio 라우터 등록

### Step 2: 프론트 기본
6. `types/index.ts` — Portfolio 타입 추가
7. `lib/portfolio.ts` — API 클라이언트
8. `components/portfolio/PortfolioSummaryCard.tsx`
9. `components/portfolio/HoldingsTable.tsx`
10. `components/portfolio/AddHoldingModal.tsx`
11. `app/(app)/portfolio/page.tsx`

### Step 3: 시각화 + AI
12. `components/portfolio/PortfolioPieChart.tsx`
13. `backend/app/services/portfolio_ai_service.py`
14. `portfolio.py` — AI stream 엔드포인트 추가
15. `components/portfolio/AIAnalysisReport.tsx`
16. `app/(app)/portfolio/analysis/page.tsx`
17. NavBar 포트폴리오 메뉴 추가

---

## 9. 의존성

### 백엔드 (신규 없음, 기존 재사용)
- `supabase` (기존)
- `finance-datareader` (기존)
- `google-generativeai` (기존)

### 프론트엔드 (신규 추가 필요)
```bash
# recharts (파이 차트용, 이미 설치 여부 확인 필요)
npm install recharts
```

---

## 10. 체크리스트

### 백엔드
- [ ] Supabase 테이블 + RLS 생성
- [ ] `deps.py` 인증 의존성 구현
- [ ] `portfolio_service.py` CRUD + 병렬 현재가 조회
- [ ] `portfolio.py` 라우터 5개 엔드포인트
- [ ] `portfolio_ai_service.py` SSE 스트리밍
- [ ] `main.py` 라우터 등록

### 프론트엔드
- [ ] Portfolio 타입 추가 (`types/index.ts`)
- [ ] `lib/portfolio.ts` API 클라이언트
- [ ] `PortfolioSummaryCard` 컴포넌트
- [ ] `HoldingsTable` 컴포넌트 (수정/삭제 포함)
- [ ] `AddHoldingModal` 컴포넌트
- [ ] `PortfolioPieChart` 컴포넌트
- [ ] `AIAnalysisReport` 컴포넌트
- [ ] `/portfolio` 페이지
- [ ] `/portfolio/analysis` 페이지
- [ ] NavBar 메뉴 추가

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 0.1 | 2026-02-18 | Initial design |
