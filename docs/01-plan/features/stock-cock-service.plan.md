# Stock Cock (주식콕) 서비스 Planning Document

> **Summary**: 복잡한 주식 정보를 AI가 분석하여 쉽게 제공하는 웹 서비스
>
> **Project**: Stock Cock
> **Version**: 0.1.0
> **Author**: User
> **Date**: 2026-02-14
> **Status**: Draft

---

## 1. Overview

### 1.1 Purpose

주식 투자에 필요한 글로벌 이슈, 정부 정책, 종목 분석 정보를 AI(Gemini)를 활용해 분석하고 사용자에게 쉽고 직관적으로 전달한다.

### 1.2 Background

- 주식 정보가 너무 많고 복잡하여 초보 투자자가 핵심을 파악하기 어려움
- 글로벌 이슈, 정부 정책이 주가에 미치는 영향을 빠르게 파악할 필요성
- AI를 활용하면 대량의 정보를 요약/분석하여 "콕" 집어 알려줄 수 있음

### 1.3 Related Documents

- Design: `docs/02-design/features/stock-cock-service.design.md` (예정)

---

## 2. Scope

### 2.1 In Scope

- [ ] 사용자 인증 (Supabase Magic Link) - 기본 구현 완료
- [ ] 글로벌 이슈 뉴스 조회 및 AI 요약
- [ ] 정부 정책 분석 및 수혜주 추천
- [ ] 종목 시세/차트 조회 (finance-datareader)
- [ ] AI 기반 종목 분석 리포트 (Gemini)
- [ ] 대시보드 UI

### 2.2 Out of Scope

- 실시간 주가 스트리밍 (WebSocket)
- 자동 매매 / 주문 기능
- 모바일 앱 (1차 MVP는 웹만)
- 유료 결제 / 구독 시스템

---

## 3. Requirements

### 3.1 Functional Requirements

| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| FR-01 | Magic Link 이메일 로그인/회원가입 | High | Done |
| FR-02 | 글로벌 이슈 뉴스 목록 조회 | High | Pending |
| FR-03 | 뉴스별 AI 요약 및 관련 종목 추천 | High | Pending |
| FR-04 | 정부 정책 목록 조회 | High | Pending |
| FR-05 | 정책별 수혜주 AI 분석 | High | Pending |
| FR-06 | 종목 검색 및 시세 조회 | Medium | Pending |
| FR-07 | 종목 차트 표시 (일봉/주봉) | Medium | Pending |
| FR-08 | AI 종목 분석 리포트 생성 | Medium | Pending |
| FR-09 | 사용자 관심 종목 저장 | Low | Pending |
| FR-10 | 대시보드 (오늘의 요약) | Medium | Pending |

### 3.2 Non-Functional Requirements

| Category | Criteria | Measurement Method |
|----------|----------|-------------------|
| Performance | API 응답 시간 < 3초 (AI 분석 제외) | FastAPI 로깅 |
| Performance | AI 분석 응답 < 10초 | Gemini API 타임아웃 |
| Security | Supabase RLS로 사용자 데이터 격리 | RLS 정책 확인 |
| Usability | 모바일 반응형 UI | Chrome DevTools |

---

## 4. Success Criteria

### 4.1 Definition of Done

- [ ] 모든 FR-01 ~ FR-10 기능 구현
- [ ] Backend API 엔드포인트 동작 확인
- [ ] Frontend-Backend 연동 완료
- [ ] 기본 에러 처리 구현

### 4.2 Quality Criteria

- [ ] Lint 에러 없음
- [ ] 빌드 성공 (frontend + backend)
- [ ] 주요 API 응답 정상 확인

---

## 5. Risks and Mitigation

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Gemini API 비용 초과 | High | Medium | 일일 호출 제한 설정, 캐싱 적용 |
| finance-datareader 데이터 불안정 | Medium | Medium | 에러 시 fallback 메시지 표시 |
| 뉴스/정책 데이터 소스 확보 | High | High | 공공 API 또는 크롤링 방안 사전 조사 |
| Supabase 무료 tier 제한 | Low | Low | 초기 MVP는 무료 tier 충분 |

---

## 6. Architecture Considerations

### 6.1 Project Level Selection

| Level | Characteristics | Recommended For | Selected |
|-------|-----------------|-----------------|:--------:|
| **Starter** | Simple structure | Static sites | |
| **Dynamic** | Feature-based, BaaS integration | Web apps with backend | **V** |
| **Enterprise** | Microservices, DI | High-traffic systems | |

### 6.2 Key Architectural Decisions

| Decision | Options | Selected | Rationale |
|----------|---------|----------|-----------|
| Frontend | Next.js / React / Vue | **Next.js 16** | App Router, SSR, 이미 세팅됨 |
| Backend | FastAPI / Express / BaaS | **FastAPI** | Python 데이터 분석 생태계 활용 |
| AI | Gemini / OpenAI / Claude | **Gemini** | 비용 효율, 한국어 성능 |
| DB | Supabase / Firebase / Custom | **Supabase** | 인증+DB 통합, 이미 세팅됨 |
| 주식 데이터 | finance-datareader / yfinance | **finance-datareader** | 한국 주식 지원 |
| Styling | Tailwind / CSS Modules | **Tailwind CSS 4** | 이미 세팅됨 |
| 차트 | recharts / chart.js / lightweight-charts | 미정 | Design 단계에서 결정 |

### 6.3 시스템 구조

```
┌─────────────────────────────────────────────────────┐
│ Frontend (Next.js 16)                               │
│   /           - 랜딩 페이지 (Done)                   │
│   /login      - 로그인 (Done)                        │
│   /dashboard  - 대시보드                              │
│   /issues     - 글로벌 이슈                           │
│   /policy     - 정책 분석                             │
│   /stock/[id] - 종목 상세                             │
├─────────────────────────────────────────────────────┤
│ Backend (FastAPI)                                    │
│   /api/news       - 뉴스 조회/AI 요약                 │
│   /api/policy     - 정책 조회/수혜주 분석              │
│   /api/stock      - 종목 시세/차트 데이터              │
│   /api/analysis   - AI 종목 분석                      │
├─────────────────────────────────────────────────────┤
│ External Services                                    │
│   Supabase (Auth + DB)                               │
│   Google Gemini (AI 분석)                             │
│   finance-datareader (주식 데이터)                     │
│   뉴스/정책 데이터 소스 (TBD)                          │
└─────────────────────────────────────────────────────┘
```

---

## 7. Convention Prerequisites

### 7.1 Existing Project Conventions

- [ ] `CLAUDE.md` - 없음
- [x] ESLint configuration (`eslint.config.mjs`)
- [ ] Prettier configuration - 없음
- [x] TypeScript configuration (`tsconfig.json`)

### 7.2 Conventions to Define/Verify

| Category | Current State | To Define | Priority |
|----------|---------------|-----------|:--------:|
| **Naming** | 없음 | 컴포넌트 PascalCase, API camelCase | High |
| **Folder structure** | 기본만 존재 | feature 기반 구조 정의 | High |
| **Import order** | 없음 | React > Next > lib > components | Medium |
| **Environment variables** | 일부 존재 | 전체 목록 정리 | High |
| **Error handling** | 없음 | 공통 에러 패턴 정의 | Medium |

### 7.3 Environment Variables Needed

| Variable | Purpose | Scope | Status |
|----------|---------|-------|:------:|
| `NEXT_PUBLIC_SUPABASE_URL` | Supabase URL | Client | 존재 |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase Key | Client | 존재 |
| `NEXT_PUBLIC_API_URL` | FastAPI 서버 URL | Client | 미생성 |
| `GEMINI_API_KEY` | Google Gemini API Key | Server | 미생성 |

---

## 8. 개발 우선순위 (Feature Roadmap)

### Phase 1: 핵심 인프라 (현재)
1. ~~인증 (Magic Link)~~ - Done
2. Backend API 기본 구조 세팅
3. Frontend-Backend 연동 설정 (CORS 등)

### Phase 2: 글로벌 이슈 기능
4. 뉴스 데이터 소스 연동
5. Gemini AI 뉴스 요약 API
6. 글로벌 이슈 페이지 UI

### Phase 3: 정책 분석 기능
7. 정책 데이터 소스 연동
8. Gemini AI 수혜주 분석 API
9. 정책 분석 페이지 UI

### Phase 4: 종목 분석 기능
10. finance-datareader 종목 시세 API
11. 차트 컴포넌트
12. AI 종목 분석 리포트

### Phase 5: 대시보드 & 마무리
13. 대시보드 페이지
14. 관심 종목 기능
15. 전체 UI 폴리싱

---

## 9. Next Steps

1. [ ] Plan 문서 리뷰 및 확정
2. [ ] Design 문서 작성 (`/pdca design stock-cock-service`)
3. [ ] Phase 1 인프라 구현 시작

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 0.1 | 2026-02-14 | Initial draft | User |
