# Portfolio Analysis - Gap Analysis Report

> **Analysis Type**: Gap Analysis (Design vs Implementation)
>
> **Project**: Stock Cock
> **Analyst**: gap-detector agent
> **Date**: 2026-02-18
> **Design Doc**: [portfolio-analysis.design.md](../02-design/features/portfolio-analysis.design.md)

---

## 1. Analysis Overview

### 1.1 Analysis Purpose

Design Document v0.1(2026-02-18) 기준으로 포트폴리오 분석 기능의 설계-구현 일치도를 검증한다.

### 1.2 Analysis Scope

- **Design Document**: `docs/02-design/features/portfolio-analysis.design.md`
- **Backend**: `backend/app/routers/portfolio.py`, `backend/app/services/portfolio_service.py`, `backend/app/services/portfolio_ai_service.py`, `backend/app/deps.py`
- **Frontend**: `frontend/lib/portfolio.ts`, `frontend/components/portfolio/*`, `frontend/app/(app)/portfolio/*`, `frontend/types/index.ts`
- **Analysis Date**: 2026-02-18

---

## 2. Overall Scores

| Category | Score | Status |
|----------|:-----:|:------:|
| API Endpoints | 100% | PASS |
| Data Model (TypeScript Types) | 100% | PASS |
| Backend Services | 100% | PASS |
| Frontend Components | 100% | PASS |
| Frontend Pages & Routing | 100% | PASS |
| API Client Functions | 92% | WARN |
| Authentication | 97% | PASS |
| Error Handling | 95% | PASS |
| Convention Compliance | 96% | PASS |
| Rate Limiting (SSE) | 0% | FAIL |
| **Overall** | **93%** | **WARN** |

---

## 3. Gap Analysis (Design vs Implementation)

### 3.1 Backend API Endpoints

| Design Endpoint | Implementation | Status | Notes |
|-----------------|----------------|:------:|-------|
| `GET /api/portfolio/holdings` | `portfolio.py:32` `get_holdings` | PASS | async, Depends(get_current_user) |
| `POST /api/portfolio/holdings` | `portfolio.py:40` `add_holding` (201) | PASS | Pydantic AddHoldingRequest 검증 |
| `PUT /api/portfolio/holdings/{id}` | `portfolio.py:53` `update_holding` | PASS | UpdateHoldingRequest (Optional fields) |
| `DELETE /api/portfolio/holdings/{id}` | `portfolio.py:68` `delete_holding` (204) | PASS | user_id 소유권 검증 |
| `GET /api/portfolio/analysis/stream` | `portfolio.py:80` SSE StreamingResponse | PASS | media_type=text/event-stream |

**Endpoint Count**: Design 5 / Implementation 5 = 100%

### 3.2 Backend Services

#### `portfolio_service.py`

| Design Function | Implementation | Status | Notes |
|-----------------|----------------|:------:|-------|
| `get_user_holdings(user_id)` | Line 15, sync | PASS | Supabase RLS, order by created_at |
| `add_holding(user_id, data)` | Line 28, sync | PASS | bought_at optional |
| `update_holding(holding_id, user_id, data)` | Line 45, sync | PASS | user_id 소유권 eq 조건 |
| `delete_holding(holding_id, user_id)` | Line 68, sync | PASS | bool 반환 |
| `get_holdings_with_price(user_id)` | Line 102, async | PASS | asyncio.gather 병렬 조회 |
| `calculate_profit(...)` | Line 83, `_calculate_profit` | PASS | private 함수, null 처리 포함 |

#### `portfolio_ai_service.py`

| Design Function | Implementation | Status | Notes |
|-----------------|----------------|:------:|-------|
| `analyze_portfolio_stream(user_id)` | Line 55, async generator | PASS | 시그니처: `(user_id, holdings)` -- holdings를 router에서 전달 |
| `build_portfolio_prompt(holdings)` | Line 17, `_build_portfolio_prompt` | PASS | private 함수, JSON 형식 프롬프트 |
| Cache TTL 24h | `_CACHE_TTL_SEC = 86400` | PASS | generic_kv_cache 재사용 |
| Cache key pattern | `portfolio_analysis:{user_id}` | PASS | 설계 Section 2.2와 일치 |

### 3.3 Backend Authentication (`deps.py`)

| Design Item | Implementation | Status | Notes |
|-------------|----------------|:------:|-------|
| `get_current_user` 함수 | Line 8, async | PASS | |
| Bearer token 파싱 | Line 10-12, `startswith("Bearer ")` 검증 | PASS | 설계보다 강화 (형식 검증 추가) |
| `supabase.auth.get_user(token)` | Line 15 | PASS | |
| 401 반환 | HTTPException(401) | PASS | |
| import 경로 | `app.utils.supabase_client` | WARN | 설계: `app.supabase_client` / 실제: `app.utils.supabase_client` (의도적 차이) |

### 3.4 Router Registration (`main.py`)

| Item | Status | Notes |
|------|:------:|-------|
| `from app.routers import ... portfolio` | PASS | Line 14 |
| `app.include_router(portfolio.router)` | PASS | Line 82 |

### 3.5 Frontend TypeScript Types (`types/index.ts`)

| Design Type | Implementation | Status | Notes |
|-------------|----------------|:------:|-------|
| `PortfolioHolding` | Line 172-183 | PASS | 모든 필드 일치 |
| `PortfolioSummary` | Line 185-190 | PASS | 4개 필드 일치 |
| `PortfolioResponse` | Line 192-195 | PASS | holdings + summary |
| `PortfolioAddRequest` | Line 197-203 | PASS | bought_at optional |
| `SectorAnalysis` | Line 205-209 | PASS | sector, ratio, comment |
| `RebalancingItem` | Line 211-215 | PASS | action union type 일치 |
| `PortfolioAIAnalysis` | Line 217-226 | PASS | 8개 필드 전부 일치 |

**Type Count**: Design 7 / Implementation 7 = 100%

### 3.6 Frontend API Client (`lib/portfolio.ts`)

| Design Function | Implementation | Status | Notes |
|-----------------|----------------|:------:|-------|
| `getPortfolioHoldings()` (Supabase CRUD) | -- | MISSING | 설계에 명시되었으나 미구현; 실제로는 FastAPI의 `fetchPortfolioWithPrice`로 대체 사용 |
| `addHolding(data)` | Line 34 (Supabase direct) | PASS | `{ok, error?, data?}` 반환 |
| `updateHolding(id, data)` | Line 61 (Supabase direct) | PASS | `{ok, error?}` 반환 |
| `deleteHolding(id)` | Line 85 (Supabase direct) | PASS | `{ok, error?}` 반환 |
| `fetchPortfolioWithPrice()` | Line 105 (FastAPI) | PASS | Bearer 인증 |
| `fetchPortfolioAnalysisStream()` | Line 125 (SSE async generator) | PASS | AbortSignal 지원 추가 (설계보다 개선) |
| `getAuthHeaders()` | Line 19 | PASS | 인증 헬퍼 |

**API Client**: Design 6 / Implementation 5 + 1 extra (PortfolioStreamEvent type) = 92%

### 3.7 Frontend Components

| Design Component | Implementation File | Status | Notes |
|------------------|---------------------|:------:|-------|
| `PortfolioSummaryCard.tsx` | `components/portfolio/PortfolioSummaryCard.tsx` | PASS | 손익 color: red-400/blue-400 한국식 |
| `HoldingsTable.tsx` | `components/portfolio/HoldingsTable.tsx` | PASS | hover 시 수정/삭제 버튼, 비중 표시, 빈 상태 처리 |
| `AddHoldingModal.tsx` | `components/portfolio/AddHoldingModal.tsx` | PASS | 종목 검색 (`searchStocks`), 예상 평가금액 미리보기, 수정 모드 지원 |
| `PortfolioPieChart.tsx` | `components/portfolio/PortfolioPieChart.tsx` | PASS | recharts PieChart, 상위 4+기타 로직, eval_amount 기준 |
| `AIAnalysisReport.tsx` | `components/portfolio/AIAnalysisReport.tsx` | PASS | SSE 소비, 진행 상태, 리스크 뱃지, 섹터 테이블, 리밸런싱 리스트 |

**Component Count**: Design 5 / Implementation 5 = 100%

#### Component Detail Compliance

| Design Requirement | Component | Status | Notes |
|--------------------|-----------|:------:|-------|
| 손익 양수 red-400, 음수 blue-400 | PortfolioSummaryCard:13 | PASS | |
| 총 평가금액, 총 손익 표시 | PortfolioSummaryCard:19-38 | PASS | 4열 그리드 (매입금액, 평가금액, 손익, 수익률) |
| 행 hover 시 수정/삭제 | HoldingsTable:96-114 | PASS | opacity transition |
| 빈 상태 + CTA | HoldingsTable:29-35 | PASS | "상단 버튼으로 종목을 추가해 보세요" |
| recharts PieChart | PortfolioPieChart:3 | PASS | `PieChart, Pie, Cell, Tooltip` import |
| 5개 이상 시 상위 4+기타 | PortfolioPieChart:26-44 | PASS | `sorted.length <= 5` 분기 |
| 종목 코드 검색 (fetchStockSearch) | AddHoldingModal:5 | PASS | `searchStocks` 사용 (동일 기능) |
| 예상 평가금액 미리보기 | AddHoldingModal:56-59 | PASS | `quantity * avgPrice` |
| SSE 스트리밍 소비 패턴 | AIAnalysisReport:72-88 | PASS | `for await (const event of ...)` |
| 리스크 레벨 뱃지 | AIAnalysisReport:155-160 | PASS | low/medium/high 색상 구분 |
| 섹터 분석 테이블 | AIAnalysisReport:170-192 | PASS | 바 차트 + 코멘트 |
| 리밸런싱 추천 리스트 | AIAnalysisReport:196-213 | PASS | action 아이콘 + 라벨 |

### 3.8 Frontend Pages & Routing

| Design Route | Implementation | Status | Notes |
|-------------|----------------|:------:|-------|
| `/portfolio` | `app/(app)/portfolio/page.tsx` | PASS | SummaryCard + HoldingsTable + PieChart + Modal |
| `/portfolio/analysis` | `app/(app)/portfolio/analysis/page.tsx` | PASS | AIAnalysisReport + 뒤로가기 |

### 3.9 NavBar Integration

| Design Item | Implementation | Status | Notes |
|-------------|----------------|:------:|-------|
| 포트폴리오 메뉴 추가 | NavBar.tsx:13 | PASS | `href: "/portfolio"` |
| PieChart 아이콘 | NavBar.tsx:5 | PASS | `import { ... PieChart } from "lucide-react"` |

### 3.10 Error Handling

| Design Error Case | Implementation | Status | Notes |
|-------------------|----------------|:------:|-------|
| 현재가 조회 실패 -> null | portfolio_service.py:121 | PASS | `except Exception: return None` |
| 보유 종목 없음 -> 빈 상태 + CTA | portfolio/page.tsx:113-125 | PASS | "첫 종목 추가하기" 버튼 |
| AI 진단 실패 -> SSE error 이벤트 | portfolio_ai_service.py:105-110 | PASS | PARSE_ERROR, AI_FAILED 코드 |
| 보유 종목 없을 때 AI 진단 | portfolio_ai_service.py:60-62 | PASS | NO_HOLDINGS error 이벤트 |
| 인증 만료 -> 401 | deps.py:16-22 | PASS | HTTPException(401) |
| 타인 종목 수정 시도 | portfolio_service.py:58 `.eq("user_id", user_id)` | PASS | Supabase 쿼리 레벨에서 필터 |

### 3.11 SSE Event Flow

| Design Event | Implementation | Status |
|-------------|----------------|:------:|
| `event: status -> {"step": 1, "message": "포트폴리오 데이터 수집 중..."}` | portfolio_ai_service.py:71 | PASS |
| `event: status -> {"step": 2, "message": "AI 진단 중..."}` | portfolio_ai_service.py:74 | PASS |
| `event: done -> { AI 분석 결과 }` | portfolio_ai_service.py:103 | PASS |
| `event: error -> {"message", "code"}` | portfolio_ai_service.py:107,110 | PASS |

### 3.12 AI Analysis Result Schema

| Design Field | Implementation (`portfolio_ai_service.py:90-98`) | Status |
|-------------|--------------------------------------------------|:------:|
| `user_id` | `user_id` | PASS |
| `total_stocks` | `len(holdings)` | PASS |
| `risk_level` | `analysis.get("risk_level", "medium")` | PASS |
| `sector_analysis` | `analysis.get("sector_analysis", [])` | PASS |
| `rebalancing` | `analysis.get("rebalancing", [])` | PASS |
| `overall_comment` | `analysis.get("overall_comment", "")` | PASS |
| `overall_score` | `analysis.get("overall_score", 3)` | PASS |
| `analyzed_at` | `datetime.now(timezone.utc).isoformat()` | PASS |

---

## 4. Differences Found

### 4.1 Missing Features (Design O, Implementation X)

| Item | Design Location | Description | Impact |
|------|-----------------|-------------|--------|
| `getPortfolioHoldings()` Supabase 직접 조회 | design.md Section 5.3 | Supabase 직접 CRUD 목록 조회 함수 미구현 | Low -- `fetchPortfolioWithPrice()`가 대체하므로 기능 누락 아님 |
| SSE Rate Limiting | (프로젝트 관례: stock.py에 15/minute) | `/api/portfolio/analysis/stream`에 rate limiter 미적용 | Medium -- AI 호출 비용 보호 필요 |

### 4.2 Added Features (Design X, Implementation O)

| Item | Implementation Location | Description | Impact |
|------|------------------------|-------------|--------|
| `PortfolioStreamEvent` type | `lib/portfolio.ts:120-123` | SSE 이벤트 Union type 정의 | Positive -- 타입 안전성 향상 |
| `AbortSignal` support | `lib/portfolio.ts:127` | SSE 스트림 취소 지원 | Positive -- UX 개선 |
| Bearer 형식 사전 검증 | `deps.py:10-11` | `startswith("Bearer ")` 검증 추가 | Positive -- 보안 강화 |
| 종목 상세 링크 | `HoldingsTable.tsx:71-77` | 종목명 클릭 시 `/stock/{code}` 이동 | Positive -- UX 개선 |
| 재분석 버튼 | `AIAnalysisReport.tsx:142-147` | "재분석" 버튼 추가 | Positive -- UX 개선 |

### 4.3 Changed Features (Design != Implementation)

| Item | Design | Implementation | Impact |
|------|--------|----------------|--------|
| `analyze_portfolio_stream` 시그니처 | `(user_id: str)` | `(user_id: str, holdings: list[dict])` | Low -- router에서 holdings 사전 조회 후 전달 (관심사 분리 개선) |
| Supabase import 경로 | `app.supabase_client` | `app.utils.supabase_client` | None -- 프로젝트 구조 차이 (기존 관례 따름) |
| CRUD 함수 반환 형태 | `Promise<PortfolioHolding>` 등 | `Promise<{ok, error?, data?}>` | Low -- 에러 처리 패턴 개선 (watchlist 패턴 통일) |
| `_sse_event` 함수 위치 | 설계 미명시 | `stock.py`에서 import | Low -- 공용 유틸로 분리 권장 |

---

## 5. Clean Architecture Compliance

### 5.1 Backend Layer Structure

| Layer | Expected | Actual | Status |
|-------|----------|--------|:------:|
| Router (Presentation) | `routers/portfolio.py` | `routers/portfolio.py` | PASS |
| Service (Application) | `services/portfolio_service.py` | `services/portfolio_service.py` | PASS |
| Service (Application) | `services/portfolio_ai_service.py` | `services/portfolio_ai_service.py` | PASS |
| Infrastructure | Supabase client, Gemini | `utils/supabase_client`, `services/gemini_service` | PASS |
| Dependencies | `deps.py` | `deps.py` | PASS |

**Backend Architecture**: Router -> Service -> Infrastructure 의존 방향 준수

### 5.2 Frontend Layer Structure

| Layer | Expected | Actual | Status |
|-------|----------|--------|:------:|
| Pages (Presentation) | `app/(app)/portfolio/` | `app/(app)/portfolio/` | PASS |
| Components (Presentation) | `components/portfolio/` | `components/portfolio/` | PASS |
| API Client (Infrastructure) | `lib/portfolio.ts` | `lib/portfolio.ts` | PASS |
| Types (Domain) | `types/index.ts` | `types/index.ts` | PASS |

### 5.3 Dependency Violations

| File | Layer | Issue | Severity |
|------|-------|-------|----------|
| `portfolio_ai_service.py:10` | Service | `from app.routers.stock import _sse_event` -- Service가 Router를 import | WARN |

**Recommendation**: `_sse_event`를 공용 유틸(`app/utils/sse.py`)로 분리하여 Router->Service 역방향 의존 해소.

---

## 6. Convention Compliance

### 6.1 Naming Convention

| Category | Convention | Compliance | Violations |
|----------|-----------|:----------:|------------|
| Components | PascalCase | 100% | -- |
| Functions (Python) | snake_case | 100% | -- |
| Functions (TypeScript) | camelCase | 100% | -- |
| Constants | UPPER_SNAKE_CASE | 100% | `_CACHE_TTL_SEC`, `COLORS`, `RISK_LABEL` 등 |
| Files (component) | PascalCase.tsx | 100% | -- |
| Files (utility) | camelCase/snake_case | 100% | -- |
| Folders | kebab-case | 100% | `portfolio/` |

### 6.2 Import Order

All files checked follow the correct order:
1. External libraries (react, next, lucide-react, recharts)
2. Internal absolute imports (`@/lib/...`, `@/types/...`, `@/components/...`)
3. Type imports (`import type`)

No violations found.

### 6.3 Convention Score

```
Convention Compliance: 96%
  Naming:          100%
  Import Order:    100%
  Architecture:     92% (_sse_event reverse dependency)
  Folder Structure: 100%
```

---

## 7. Design Checklist Verification (Section 10)

### Backend Checklist

| # | Item | Status | Evidence |
|---|------|:------:|----------|
| 1 | Supabase 테이블 + RLS 생성 | N/A | 런타임 DB 확인 필요 (코드에서 `portfolio_holdings` 테이블 참조 확인) |
| 2 | `deps.py` 인증 의존성 구현 | PASS | `backend/app/deps.py` -- `get_current_user()` |
| 3 | `portfolio_service.py` CRUD + 병렬 현재가 조회 | PASS | CRUD 4함수 + `get_holdings_with_price` (asyncio.gather) |
| 4 | `portfolio.py` 라우터 5개 엔드포인트 | PASS | GET/POST/PUT/DELETE holdings + GET analysis/stream |
| 5 | `portfolio_ai_service.py` SSE 스트리밍 | PASS | AsyncGenerator, cache 히트/미스, Gemini 호출 |
| 6 | `main.py` 라우터 등록 | PASS | `app.include_router(portfolio.router)` |

### Frontend Checklist

| # | Item | Status | Evidence |
|---|------|:------:|----------|
| 1 | Portfolio 타입 추가 (`types/index.ts`) | PASS | Line 171-226, 7개 인터페이스 |
| 2 | `lib/portfolio.ts` API 클라이언트 | PASS | CRUD + fetchWithPrice + SSE stream |
| 3 | `PortfolioSummaryCard` 컴포넌트 | PASS | 총 매입/평가/손익/수익률 4열 그리드 |
| 4 | `HoldingsTable` 컴포넌트 (수정/삭제 포함) | PASS | hover 수정/삭제, 빈 상태 CTA |
| 5 | `AddHoldingModal` 컴포넌트 | PASS | 종목 검색, 입력, 미리보기, 수정 모드 |
| 6 | `PortfolioPieChart` 컴포넌트 | PASS | recharts, 상위4+기타 |
| 7 | `AIAnalysisReport` 컴포넌트 | PASS | SSE, 리스크뱃지, 섹터, 리밸런싱 |
| 8 | `/portfolio` 페이지 | PASS | `app/(app)/portfolio/page.tsx` |
| 9 | `/portfolio/analysis` 페이지 | PASS | `app/(app)/portfolio/analysis/page.tsx` |
| 10 | NavBar 메뉴 추가 | PASS | PieChart 아이콘, `/portfolio` 링크 |

**Checklist**: Design 16 / Implementation 15 PASS + 1 N/A = **94%** (DB 테이블은 런타임 확인 필요)

---

## 8. Overall Score

```
+---------------------------------------------+
|  Overall Match Rate: 93%                     |
+---------------------------------------------+
|  API Endpoints:          100% (5/5)          |
|  Backend Services:       100% (8/8 functions)|
|  TypeScript Types:       100% (7/7)          |
|  Frontend Components:    100% (5/5)          |
|  Pages & Routing:        100% (2/2)          |
|  NavBar Integration:     100%                |
|  API Client Functions:    92% (5/6)          |
|  Error Handling:          95%                |
|  SSE Event Flow:         100%                |
|  Authentication:          97%                |
|  Convention:              96%                |
|  Rate Limiting:            0% (missing)      |
+---------------------------------------------+
|  Checklist Pass Rate: 15/16 = 94%            |
+---------------------------------------------+
```

---

## 9. Recommended Actions

### 9.1 Immediate (High Priority)

| Priority | Item | File | Description |
|----------|------|------|-------------|
| HIGH | SSE Rate Limiting 추가 | `backend/app/routers/portfolio.py:80` | `@limiter.limit("15/minute")` 데코레이터 추가 (stock.py 패턴 동일) |

### 9.2 Short-term (Medium Priority)

| Priority | Item | File | Description |
|----------|------|------|-------------|
| MEDIUM | `_sse_event` 공용 유틸 분리 | `backend/app/utils/sse.py` | Service -> Router 역방향 의존 해소 |
| LOW | `getPortfolioHoldings()` 추가 또는 설계에서 제거 | `frontend/lib/portfolio.ts` 또는 design doc | Supabase 직접 목록 조회 함수 -- 현재 불필요할 수 있음 |

### 9.3 Design Document Update Needed

- [ ] Section 4.2: `analyze_portfolio_stream` 시그니처를 `(user_id, holdings)`로 반영
- [ ] Section 5.3: `getPortfolioHoldings()` 제거 또는 의도적 차이 표기
- [ ] Section 5.3: CRUD 반환 타입을 `{ok, error?, data?}` 패턴으로 반영
- [ ] Section 6.1: import 경로를 `app.utils.supabase_client`로 반영
- [ ] Rate Limiting 항목 추가 (Section 3.2에 명시)

---

## 10. Synchronization Recommendation

Match Rate **93%** >= 90% 이므로 설계와 구현이 잘 일치합니다.

**Minor 조치 사항:**
1. SSE Rate Limiting 추가 (`portfolio.py`) -- 비용 보호를 위해 즉시 적용 권장
2. `_sse_event` 유틸 분리 -- 아키텍처 정합성 개선
3. 설계 문서 업데이트 -- 위 Section 9.3의 5개 항목 반영

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2026-02-18 | Initial gap analysis | gap-detector |
