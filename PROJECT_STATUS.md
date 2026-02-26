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

## 현재 구현된 기능 상세

---

### 1. 홈 화면 (`/`)

| 항목 | 내용 |
|------|------|
| 역할 | 서비스 소개 및 메뉴 진입점 |
| NavBar | 상단 고정, 6개 메뉴: 시작하기 / 이슈 / 정책 / 종목분석 / 공시콕 / 포트폴리오 |

---

### 2. 대시보드 (`/dashboard`)

#### 테마 트렌드

| 항목 | 내용 |
|------|------|
| 기능 | KOSPI+KOSDAQ 상위 종목을 AI가 투자 테마(최대 30개)로 분류 |
| 표시 | 테마별 평균 등락률, 소속 종목 목록 |
| 전환 | 일간(오늘) / 주간(최근 5거래일), 정렬: 등락률 / 거래대금 |
| 데이터 출처 | pykrx (주말·공휴일 자동 최근 거래일 탐색) → FDR 폴백 |
| AI | Gemini 2.0 Flash (등락률·거래대금 상위 150+150 병합 후 테마 분류) |
| 캐시 | 일간 1시간 TTL / 주간 24시간 TTL (Supabase `generic_kv_cache`) |
| 성능 | 서버 시작 시 테마 트렌드·대시보드 선행 계산(warm-up) |

#### 시장 현황

| 항목 | 내용 |
|------|------|
| 기능 | KOSPI, KOSDAQ 지수 현재가·등락률 |
| 데이터 출처 | FinanceDataReader (`KS11`, `KQ11`) |
| 캐시 | 5분 TTL |

#### 내 관심 키워드 (키워드 피드)

| 항목 | 내용 |
|------|------|
| 기능 | 사용자 입력 키워드로 관련 종목·뉴스·정책 자동 검색 |
| 종목 | Gemini 지식 베이스 추출 → FDR로 실제 상장 여부·현재가 검증 (최대 10개) |
| 뉴스 | 네이버 뉴스 API + NewsAPI.org 5건 |
| 정책 | 정책브리핑 RSS 3건 |

#### 주요 뉴스 & 핫 정책 요약

| 항목 | 내용 |
|------|------|
| 기능 | 오늘의 주요 뉴스 3건 / 최신 정책 2건 |
| 데이터 출처 | 네이버 뉴스 API / 정책브리핑 RSS |

---

### 3. 국내외 이슈 (`/issues`)

#### 뉴스 목록

| 항목 | 내용 |
|------|------|
| 기능 | 국내+해외 최신 뉴스 목록, 카테고리 필터(전체/해외/국내), 키워드 검색 |
| 카테고리 태그 | 해외 / 국내 (GLOBAL/DOMESTIC 대신 한국어 표시) |
| 데이터 출처 | 국내: 네이버 뉴스 검색 API / 해외: NewsAPI.org |
| 신선도 | 국내 24시간, 해외 72시간 이내 기사만 표시 |
| 필터 | 광고·[포토]·[인사]·[부고] 자동 차단, 유사도 80% 중복 제거 |

#### 뉴스 상세 (`/issues/[id]`)

**탭 1 — AI 분석**

| 섹션 | 내용 |
|------|------|
| 📌 핵심 팩트 | 뉴스에서 가장 중요한 사실 3가지 (강조 박스) |
| 🔍 연관 분야 및 테마 | 산업군, 핵심 키워드 (카드) |
| ⚡ 시장 파급력 | 강도(매우 높음/높음/보통/낮음), 단기·장기 영향 (카드) |
| 💡 투자 인사이트 | 직접수혜주 / 낙수효과주 / 중소형 히든카드 **5~10개** |

**탭 2 — 관련 종목 보기**

| 섹션 | 내용 |
|------|------|
| 종목 목록 | 직접수혜주 / 낙수효과주 태그, 추천 이유 |
| AI의 한마디 | 파급력 강도 기반 상단 코멘트 박스 |
| 인라인 AI 분석 | 종목 클릭 시 해당 종목 AI 분석 결과 즉시 표시 |

| 항목 | 내용 |
|------|------|
| 데이터 출처 | 원문: 네이버/NewsAPI / AI: Gemini 2.0 Flash |
| 캐시 | Supabase `news_cache` (24시간 TTL 적용) |
| 해외 뉴스 | 번역+분석 통합 프롬프트 (별도 처리) |
| 원문 보기 | 분석 하단 '원문 보기' 버튼을 통해 원글로 즉시 이동 가능 (URL 전달 로직 보강) |
| 레이아웃 | 모든 섹션 간격(space-y-5) 및 카드 패딩 통일 |

---

### 4. 정책 돋보기 (`/policy`)

#### 정책 목록

| 항목 | 내용 |
|------|------|
| 기능 | 최신 정부 보도자료·정책 목록, 키워드 필터 |
| 데이터 출처 | 정책브리핑(korea.kr) RSS → 투자 관련 필터 → Supabase `policy_news` |
| 폴백 | RSS 수집 실패 시 샘플 정책 5건 표시 |

#### 정책 상세 (`/policy/[id]`)

**탭 1 — AI 분석**

| 섹션 | 내용 |
|------|------|
| 📌 핵심 팩트 | 가장 중요한 사실 3줄 (강조 박스) |
| 🔍 연관 분야 및 테마 | 산업군, 핵심 키워드 (카드) |
| ⚡ 시장 파급력 | 강도(상/중/하), 단기·장기 영향 (카드) |
| 💡 투자 인사이트 | 직접수혜주 / 낙수효과주 / 중소형 수혜주 **5~10개** |

**탭 2 — 관련 종목 보기**

| 섹션 | 내용 |
|------|------|
| 종목 목록 | 직접수혜주 / 피해주 / 관련주 태그 |
| AI의 한마디 | 정책 분석 첫 문장 기반 상단 코멘트 박스 |
| 인라인 AI 분석 | 종목 클릭 시 해당 종목 AI 분석 결과 즉시 표시 |

| 항목 | 내용 |
|------|------|
| 데이터 출처 | 정책브리핑 RSS + 첨부 PDF 내용 자동 추출 |
| AI | Gemini 2.0 Flash |
| 캐시 | Supabase `policy_news` 내 통합 저장 (유동적 갱신) |
| 레이아웃 | 뉴스 상세와 동일한 카드 스타일 및 간격(space-y-5) 적용 |
| 원문 보기 | 분석 하단 '원문 보기' 버튼을 통해 정책브리핑 사이트로 이동 |

---

### 5. 종목분석 (`/stock`)

#### 탭 1 — 종목검색

| 항목 | 내용 |
|------|------|
| 기능 | 종목명 또는 코드로 KRX 전체 종목 검색 (최대 20개) |
| 데이터 출처 | FinanceDataReader KRX 종목 목록 (서버 메모리 캐시) |

#### 탭 2 — 종목비교

| 항목 | 내용 |
|------|------|
| 기능 | A / B 종목 각각 검색 선택 → AI가 10개 항목 1:1 비교 |
| 비교 항목 | 부채 / 현금흐름 / 수급 / 차트 / 과열(RSI) / 가성비(PBR) / 성장성 / 수익성 / 거래량 / 날씨(시장) |
| 표시 | 항목별 A승/B승/동점, 최종 별점(1~5), 최종 결론 + 주의사항 |
| 언어 | 쉬운 말로 풀어서 설명 (전문 용어 최소화) |
| 데이터 출처 | 재무: FDR / 차트·RSI: FDR / 수급: pykrx / AI: Gemini 2.0 Flash |

#### 종목 상세 (`/stock/[code]`)

| 항목 | 내용 |
|------|------|
| 기능 | 종목명·현재가·등락률·거래량 표시 |
| 재무 지표 | PBR, ROE, 부채비율, 매출성장률, 영업이익률, 영업활동현금흐름 |
| 차트 | 캔들스틱 차트: 1개월/3개월/6개월/1년 (Recharts) |
| 공시 탭 | 종목 관련 최근 DART 공시 목록 (30일 이내) |
| 데이터 출처 | FinanceDataReader, DART API |

#### 종목 AI 분석 (`/stock/[code]/analysis`)

| 항목 | 내용 |
|------|------|
| 기능 | 10개 항목별 분석 카드 + 종합 별점 + 감성 판단 |
| 항목 | 부채 / 현금흐름 / 수급 / 차트 / 과열 / 가성비 / 성장성 / 수익성 / 거래량 / 날씨 |
| 표현 | 꼰대 말투 ("아직 빚에 허덕인다", "외쿸인·큰형님 싹 쓸어담는 중") |
| 스트리밍 | SSE 3단계 진행 표시: 주가수집 → 뉴스분석 → AI분석 |
| 데이터 출처 | FDR (재무) + pykrx (수급) + 네이버/NewsAPI (뉴스 5~8건) + Gemini 2.0 Flash |
| 캐시 | Supabase `analysis_cache` (24시간 TTL) |

---

### 6. 공시콕 (`/disclosure`)

| 항목 | 내용 |
|------|------|
| 기능 | 오늘 발표된 주요 DART 공시 목록 (최대 30건) |
| 표시 | 기업명, 종목코드, 공시명, 접수일, 제출인 |
| AI 분석 | 공시 클릭 시 꼰대아저씨 AI 분석 로드 (호재/악재/중립 판정) |
| 비즈니스 모델| **Reward Ads** 연동: 광고 시청 시 AI 분석 결과 잠금 해제 (UI 구현 완료) |
| 분석 내용 | 요약, 감성(호재/악재/중립), 투자 인사이트, 주의사항 |
| 데이터 출처 | DART 전자공시 API (OpenDartReader) |
| 캐시 | `generic_kv_cache` (공시 목록 30분, 분석 결과 24시간) |
| Rate Limit | 10/분 |

---

### 7. 내 포트폴리오 (`/portfolio`)

#### 보유 종목 탭

| 항목 | 내용 |
|------|------|
| 기능 | 보유 종목 추가·수정·삭제, 현재가·수익률 자동 계산 |
| 추가 | 종목 검색 → 수량·평균매수가·매수일 입력 |
| 수정 | 수량·평균매수가·매수일 변경 |
| 삭제 | 카드 호버 시 삭제 버튼 노출 |
| 요약 카드 | 총 투자금 / 총 평가금 / 총 수익률 |
| 데이터 출처 | 보유 종목 저장: Supabase `portfolio_holdings` (JWT 인증 필수) |
| 현재가 | FinanceDataReader 병렬 조회 |

#### 종목비중 파이차트

| 항목 | 내용 |
|------|------|
| 기능 | 평가금액 기준 비중 시각화 (상위 4개 + 기타) |
| 라이브러리 | Recharts PieChart |

#### 수익률 추이 차트 (신규)

| 항목 | 내용 |
|------|------|
| 기능 | 매수일 기준 누적 수익률 꺾은선 그래프 + KOSPI 비교선 |
| 기간 탭 | 1M / 3M / 6M / 1Y |
| 계산 기준 | 총매입금액(Σ avg_price × quantity) 대비 평가금액 변화율 |
| KOSPI 기준 | 시작일 가격 기준 정규화 (0%에서 출발) |
| 처리 | 주말·공휴일은 직전 거래일 가격 forward-fill |
| 데이터 출처 | FinanceDataReader (종목 차트 + KS11 KOSPI) |
| 캐시 | `generic_kv_cache` 5분 TTL (키: `portfolio:perf:{user_id}:{days}`) |
| 라이브러리 | Recharts LineChart |

#### 관심종목 탭

| 항목 | 내용 |
|------|------|
| 기능 | 관심종목 목록 + 실시간 현재가·등락률 표시 |
| 급등/급락 | ±5% 이상 변동 시 배지 표시 |
| 삭제 | 호버 시 별 아이콘 클릭으로 제거 |

#### AI 포트폴리오 진단 (`/portfolio/analysis`)

| 항목 | 내용 |
|------|------|
| 기능 | 전체 포트폴리오 AI 진단: 리스크·섹터 분석·리밸런싱 추천 |
| 표시 | 리스크 등급 / 섹터 비율 및 코멘트 / 줄여야 할·늘려야 할·유지할 종목 / 별점 |
| 스트리밍 | SSE 진행 표시 |
| 데이터 출처 | Supabase 보유 종목 + FDR 현재가 + Gemini 2.0 Flash |

---

## 기술적 특이사항

### 성능 최적화

| 항목 | 내용 |
|------|------|
| SSE 스트리밍 | 종목 분석·포트폴리오 진단 진행 상황 실시간 표시 |
| Supabase KV 캐시 | 테마 트렌드·대시보드·뉴스·정책·공시·수익률 분석 결과 DB 저장 → API 비용 절감 |
| **Warm-up 서비스** | 서버 시작 시 대시보드/테마 데이터 선행 계산 + 백그라운드 갱신 |
| **비동기/병렬 최적화** | `asyncio.gather` 및 `to_thread`를 적극 활용하여 외부 API(FDR, pykrx, NewsAPI) 대기 시간 최소화 |
| 이벤트 루프 비차단 | Gemini 동기 API를 `run_in_executor()`로 실행 → 다른 요청 블로킹 방지 |

### 타임아웃 설정

| 대상 | 설정값 |
|------|--------|
| 일반 API 요청 | 20초 |
| AI 분석 요청 (뉴스·정책·종목·비교) | 60초 |
| Gemini API 단일 호출 | 55초 (내부 타임아웃) |
| Gemini 재시도 | 최대 3회, 지수 백오프 (2s→4s→8s) |

### 안정성

| 항목 | 내용 |
|------|------|
| Supabase 재연결 | Windows WinError 10035 오류 시 `reset_supabase()` + 자동 재시도 |
| 폴백 체계 | RSS 실패 → 샘플 정책 / pykrx 실패 → FDR 폴백 / 차트 없는 날 → forward-fill |
| 광고·가짜 뉴스 차단 | 제목 패턴 기반 자동 필터 |

### 보안

| 항목 | 내용 |
|------|------|
| JWT 인증 | 포트폴리오 API는 Supabase JWT 검증 필수 |
| Rate Limiting | slowapi: 종목분석 15/분, 비교 10/분, 포트폴리오AI 10/분, 공시분석 10/분 |
| 키 분리 | 백엔드 서비스 롤 키(`sb_secret_*`) / 프론트 anon 키(`sb_publishable_*`) |

---

## API 엔드포인트 목록

| Method | Path | 설명 | Rate Limit |
|--------|------|------|-----------|
| GET | `/api/news` | 뉴스 목록 | - |
| GET | `/api/news/summary` | 뉴스 AI 요약 분석 | 15/분 |
| GET | `/api/policy` | 정책 목록 | - |
| GET | `/api/policy/{id}/analysis` | 정책 AI 분석 | 15/분 |
| GET | `/api/stock/search` | 종목 검색 | - |
| GET | `/api/stock/compare` | 두 종목 AI 비교 분석 | 10/분 |
| GET | `/api/stock/{code}/price` | 종목 시세·재무 | - |
| GET | `/api/stock/{code}/chart` | 종목 차트 | - |
| GET | `/api/stock/{code}/analysis` | 종목 AI 분석 (REST) | 15/분 |
| GET | `/api/stock/{code}/analysis/stream` | 종목 AI 분석 (SSE) | 15/분 |
| GET | `/api/stock/{code}/disclosures` | 종목별 공시 이력 | - |
| GET | `/api/disclosure` | 오늘 DART 공시 목록 | - |
| GET | `/api/disclosure/{rcp_no}/analysis` | 공시 AI 분석 | 10/분 |
| GET | `/api/dashboard` | 대시보드 기본 데이터 | - |
| GET | `/api/dashboard/theme-trend` | 테마 트렌드 | - |
| GET | `/api/dashboard/keyword-feed` | 키워드 피드 | - |
| GET | `/api/portfolio/holdings` | 보유 종목 목록 + 현재가 | 인증 필수 |
| POST | `/api/portfolio/holdings` | 종목 추가 | 인증 필수 |
| PUT | `/api/portfolio/holdings/{id}` | 종목 수정 | 인증 필수 |
| DELETE | `/api/portfolio/holdings/{id}` | 종목 삭제 | 인증 필수 |
| GET | `/api/portfolio/performance` | 포트폴리오 수익률 추이 vs KOSPI | 인증 필수 |
| GET | `/api/portfolio/analysis/stream` | AI 포트폴리오 진단 (SSE) | 10/분, 인증 필수 |
| POST | `/api/cron/cleanup` | news_cache, policy_cache 7일 경과 삭제 | - |
| POST | `/api/cron/archive` | news_cache 보통 이하 파급력 is_archived 처리 | - |
| POST | `/api/cron/cleanup-generic` | generic_kv_cache 만료(7일+) 삭제 | - |

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
