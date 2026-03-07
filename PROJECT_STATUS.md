# 주식콕 (Stock Cock) — 프로젝트 현황 문서

> 복잡한 주식 정보, **콕** 집어 알려드려요.
> 최종 업데이트: 2026-02-17

---

## 기술 스택

| 구분 | 기술 |
|------|------|
| **프론트엔드** | Next.js 14/15 (App Router, TypeScript), Tailwind CSS, Recharts |
| **백엔드** | FastAPI (Python), uvicorn, slowapi (Rate Limit) |
| **AI 분석** | Google Gemini 2.0 Flash (Streaming SSE 지원) |
| **데이터베이스** | Supabase (PostgreSQL, RLS 적용) |
| **주식 데이터** | pykrx (국내 수급/지표), FinanceDataReader (FDR 시세/차트) |
| **뉴스 데이터** | 네이버 뉴스 검색 API (국내), NewsAPI.org (해외) |
| **정책 데이터** | 정책브리핑(korea.kr) RSS + PDF 텍스트 추출 |
| **공시 데이터** | DART 전자공시 API (OpenDartReader) |
| **수익 구조** | Reward Ads (Google AdMob 스타일 UI) 연동 |
| **인증** | Supabase Auth (Email/Password, Social) |
| **캐시** | Supabase 전용 테이블 (`analysis_cache`, `generic_kv_cache`, `news_cache`, `policy_news`) |

---

## 실행 방법

```bash
# 동시 실행 (추천)
npm run dev

# 개별 실행
# Backend (포트 8000)
cd backend && python -m uvicorn app.main:app --reload --port 8000
# Frontend (포트 3000)
cd frontend && npm run dev
```

### 환경변수

**`backend/.env`**

| 변수 | 용도 |
|------|------|
| `SUPABASE_URL` | Supabase 연결 URL |
| `SUPABASE_SERVICE_KEY` | 서비스 롤 키 (`sb_secret_*`) — anon key 사용 금지 |
| `GEMINI_API_KEY` | Gemini AI |
| `NAVER_CLIENT_ID` / `NAVER_CLIENT_SECRET` | 네이버 뉴스 API |
| `NEWS_API_KEY` | NewsAPI.org |
| `DART_API_KEY` | DART 전자공시 API (opendart.fss.or.kr에서 발급) |
| `FRONTEND_URL` | CORS 허용 URL (기본 http://localhost:3000) |

**`frontend/.env.local`**

| 변수 | 용도 |
|------|------|
| `NEXT_PUBLIC_API_URL` | FastAPI URL (http://localhost:8000) |
| `NEXT_PUBLIC_SUPABASE_URL` | Supabase URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase Anon Key (`sb_publishable_*`) |

---

## Supabase 테이블 구조

| 테이블 | 용도 | TTL / 보존 |
|--------|------|-----------|
| `analysis_cache` | 종목 AI 분석 결과 | 24시간 |
| `generic_kv_cache` | 테마 트렌드·대시보드·공시 목록·수익률 캐시 | 5분 ~ 24시간 |
| `news_cache` | 뉴스 AI 요약 + 원문 URL | 24시간 (분석 갱신 주기) |
| `policy_news` | 정책 원문 + PDF 추출 텍스트 + AI 분석 결과 | 노출 기간(약 3일) 기반 |
| `portfolio_holdings` | 사용자 보유 종목 및 관심 종목 | 영구 |

```sql
-- generic_kv_cache 생성 SQL
create table if not exists generic_kv_cache (
  cache_key  text primary key,
  data       jsonb        not null,
  expires_at timestamptz  not null,
  created_at timestamptz  default now()
);
create index if not exists idx_gkv_expires on generic_kv_cache(expires_at);

-- portfolio_holdings 생성 SQL
create table if not exists portfolio_holdings (
  id         uuid primary key default gen_random_uuid(),
  user_id    text not null,
  stock_code text not null,
  stock_name text not null,
  quantity   numeric not null,
  avg_price  numeric not null,
  bought_at  date,
  created_at timestamptz default now()
);
```

---

## 디렉터리 구조

```
Stock_Cock/
├── backend/
│   └── app/
│       ├── main.py                  # FastAPI 앱, CORS, lifespan
│       ├── routers/
│       │   ├── news.py              # 뉴스 목록/요약
│       │   ├── policy.py            # 정책 목록/분석
│       │   ├── stock.py             # 종목 검색/시세/차트/분석/비교/공시목록
│       │   ├── dashboard.py         # 대시보드/테마트렌드/키워드피드
│       │   ├── disclosure.py        # DART 공시 목록 + AI 분석
│       │   ├── portfolio.py         # 포트폴리오 CRUD + 수익률차트 + AI 진단
│       │   └── cron.py              # 캐시 cleanup
│       └── services/
│           ├── gemini_service.py    # Gemini AI 호출 (뉴스/정책/종목/비교/테마/공시)
│           ├── stock_service.py     # 주식 시세·재무·차트 (FDR + pykrx), async 래퍼
│           ├── news_service.py      # 뉴스 수집·필터·캐시
│           ├── naver_news_service.py
│           ├── newsapi_service.py
│           ├── policy_service.py    # 정책 RSS 수집·AI 분석
│           ├── policy_rss_service.py
│           ├── policy_news_db.py    # 정책 캐시 DB
│           ├── dart_service.py      # DART 전자공시 수집·AI 분석
│           ├── portfolio_service.py # 포트폴리오 CRUD + 현재가
│           ├── portfolio_ai_service.py # 포트폴리오 AI 진단 SSE
│           ├── analysis_cache_service.py # 종목 분석 24h 캐시
│           ├── generic_cache_service.py  # 범용 KV 캐시
│           ├── news_cache_db.py     # 뉴스 캐시 DB
│           ├── cache_cleanup_service.py  # 캐시 만료 정리
│           └── warmup_service.py    # 서버 시작 선행 계산 + 백그라운드 갱신
├── frontend/
│   ├── app/
│   │   ├── page.tsx                 # 홈(랜딩)
│   │   └── (app)/
│   │       ├── dashboard/page.tsx   # 대시보드
│   │       ├── issues/              # 뉴스 목록 + 상세
│   │       ├── policy/              # 정책 목록 + 상세
│   │       ├── stock/               # 종목 검색·비교 + 상세 + AI 분석
│   │       ├── disclosure/page.tsx  # DART 공시 목록 + AI 분석
│   │       ├── watchlist/page.tsx   # /portfolio?tab=watchlist 리다이렉트
│   │       └── portfolio/           # 포트폴리오 + AI 진단
│   ├── components/
│   │   ├── layout/NavBar.tsx        # 상단 고정 6개 메뉴
│   │   ├── layout/Footer.tsx
│   │   ├── ui/                      # LoadingSpinner, ErrorMessage
│   │   ├── auth/                    # AuthForm, LogoutButton
│   │   ├── dashboard/               # MarketOverview, ThemeTrend, KeywordFeed, DashboardSummary
│   │   ├── news/                    # AiSummary, NewsCard, NewsList
│   │   ├── policy/                  # PolicyAnalysis, PolicyCard
│   │   ├── stock/                   # StockCompare, StockChart, StockInfo, StockAnalysisReport, StockSearchBar, StockSearchResultCard
│   │   └── portfolio/               # PortfolioPieChart, PortfolioReturnChart, PortfolioSummaryCard, HoldingsTable, AddHoldingModal, AIAnalysisReport
│   ├── lib/
│   │   ├── api.ts                   # 공개 API 클라이언트 (뉴스/정책/주식/공시/대시보드)
│   │   └── portfolio.ts             # 포트폴리오 API 클라이언트 (인증 필요)
│   └── types/index.ts               # 전체 TypeScript 타입
└── PROJECT_STATUS.md
```

---




---

## 개발 지침 (한 줄)

> **주식 데이터**: 국내 주식은 pykrx 최우선. **뉴스/정책 AI 분석**: Supabase 캐시 먼저 조회 → 없을 때만 Gemini 호출.

---

## 알려진 경고 및 마이그레이션 참고

| 항목 | 상태 | 비고 |
|------|------|------|
| `google.generativeai` | FutureWarning | 공식 지원 종료. 추후 `google.genai` 패키지로 전환 권장 |
| Next.js middleware | deprecation | `middleware` → `proxy` 컨벤션 전환 예정 (Next.js 문서 참고) |

---

## 앞으로 추가하면 좋은 기능 아이디어

### 우선순위 중간 — 서비스 차별화

#### 1. 섹터/조건 기반 종목 스크리너
- PBR 1 이하 + ROE 10% 이상 + 외국인 순매수 같은 복합 조건 필터
- 사용자가 조건을 직접 설정 → 해당 종목 리스트 출력


#### 2. 실시간 주가 알림 (Push Notification)
- 관심종목 목표가 도달 / ±N% 변동 시 브라우저 알림
- Web Push API 활용


---

### 우선순위 낮음 — 장기 로드맵

#### 3. 소셜 기능 — 공개 포트폴리오
- 익명으로 포트폴리오 수익률 공개·비교
- 고수익 포트폴리오 팔로우

#### 4. AI 챗봇 ("꼰대아저씨에게 물어보기")
- 종목·뉴스·정책에 대해 자유 형식으로 질문
- Gemini 기반 RAG (현재 뉴스·공시 데이터 참조)

#### 5. 세금 계산기
- 매도 시 양도소득세 자동 계산 (대주주 여부, 보유 기간 반영)
- 세후 수익률 계산

#### 6. 해외 주식 지원
- 미국 주식(NYSE, NASDAQ) 종목 검색·분석
- 환율 연동 원화 환산 수익률

#### 7. PWA (Progressive Web App) 전환
- 홈 화면 설치, 오프라인 기본 화면 지원
- 모바일 앱 수준 사용성

#### 8. 다크/라이트 테마 전환
- 현재 다크 모드 고정 → 라이트 모드 선택지 추가

---

## 배포 가이드 (Deployment Guide)

### 1. 파이어베이스 (Firebase) - **추천**
> **장점**: 프론트엔드와 백엔드를 Firebase App Hosting 및 Cloud Run을 통해 통합 관리할 수 있습니다.

1. **프론트엔드 (App Hosting)**:
   - Firebase Console에서 App Hosting 서비스를 생성하고 GitHub 저장소를 연결합니다.
   - 루트 디렉터리 기반으로 Next.js 앱(`frontend` 폴더)이 자동 빌드 및 배포됩니다.

2. **백엔드 (Cloud Run)**:
   - `backend` 폴더의 `Dockerfile`을 사용하여 Cloud Run에 배포합니다.
   - **중요**: Cloud Run은 `PORT` 환경변수(기본 8080)를 사용하므로, `main.py` 또는 `Dockerfile`에서 이를 처리해야 합니다.
   - 환경 변수(Secrets)는 Google Cloud Secret Manager에 등록하거나 Cloud Run 설정에서 직접 입력합니다.

3. **환경 변수 설정**:
   - `GEMINI_API_KEY`, `SUPABASE_URL`, `SUPABASE_SERVICE_KEY` 등 필수 키를 설정합니다.
   - 프론트엔드 `.env.production`의 `NEXT_PUBLIC_API_URL`을 배포된 백엔드 URL로 업데이트합니다.

4. **배포 실행**:
   ```bash
   # 백엔드 배포 (gcloud CLI 필요)
   cd backend
   gcloud run deploy stock-cock-backend --source . --region asia-east1 --allow-unauthenticated
   ```
.
