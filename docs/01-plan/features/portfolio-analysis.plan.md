# Portfolio Analysis (포트폴리오 분석) Planning Document

> **Summary**: 사용자가 보유한 주식 포트폴리오를 입력하고 수익률을 추적하며 AI 기반 진단을 받는 기능
>
> **Project**: Stock Cock
> **Feature**: portfolio-analysis
> **Version**: 0.1.0
> **Author**: User
> **Date**: 2026-02-18
> **Status**: Draft

---

## 1. Overview

### 1.1 Purpose

사용자가 보유 주식(종목, 매입가, 수량)을 등록하면 현재가 기준 수익률을 자동 계산하고,
AI(Gemini)가 포트폴리오 구성을 분석하여 리밸런싱 제안 및 리스크 진단을 제공한다.

### 1.2 Background

- 현재 관심종목(Watchlist) 기능은 종목 저장만 가능, 수익률 추적 불가
- 투자자는 여러 종목을 보유하며 전체 포트폴리오 성과를 한눈에 보고 싶어함
- AI를 통해 포트폴리오의 리스크/섹터 쏠림 등을 분석받고 싶어함

### 1.3 Related Documents

- Parent Plan: `docs/01-plan/features/stock-cock-service.plan.md`
- Design: `docs/02-design/features/portfolio-analysis.design.md` (예정)

---

## 2. Scope

### 2.1 In Scope

- [ ] 포트폴리오 보유 종목 CRUD (종목코드, 매입가, 수량, 매입일)
- [ ] 현재가 자동 조회 및 수익률 계산 (손익금액, 수익률%)
- [ ] 포트폴리오 요약 카드 (총 평가금액, 총 손익, 전체 수익률)
- [ ] 섹터/종목별 비중 시각화 (파이 차트)
- [ ] 수익률 순위 테이블 (보유 종목별)
- [ ] AI 포트폴리오 진단 (Gemini 기반, 리스크·리밸런싱 제안)

### 2.2 Out of Scope

- 실시간 주가 스트리밍 업데이트
- 매매 히스토리/거래 내역 관리
- 세금/수수료 계산
- 외국 주식 포트폴리오 (1차는 한국 주식만)
- 자동 증권사 연동 (MTS API)

---

## 3. Requirements

### 3.1 Functional Requirements

| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| FR-01 | 보유 종목 추가 (종목코드, 매입가, 수량, 매입일) | High | Pending |
| FR-02 | 보유 종목 수정/삭제 | High | Pending |
| FR-03 | 현재가 자동 조회 및 수익률 계산 | High | Pending |
| FR-04 | 포트폴리오 요약 카드 (총 평가금액, 총 손익, 수익률) | High | Pending |
| FR-05 | 종목별 수익률 테이블 | High | Pending |
| FR-06 | 섹터/종목 비중 파이 차트 | Medium | Pending |
| FR-07 | AI 포트폴리오 진단 리포트 (SSE 스트리밍) | Medium | Pending |
| FR-08 | 관심종목(Watchlist) → 포트폴리오 빠른 추가 | Low | Pending |

### 3.2 Non-Functional Requirements

| Category | Criteria | Measurement Method |
|----------|----------|-------------------|
| Performance | 현재가 조회 < 3초 (10종목 기준) | 브라우저 Network 탭 |
| Performance | AI 진단 시작 응답 < 2초 (SSE 첫 이벤트) | SSE 스트리밍 |
| Security | 타 사용자 포트폴리오 접근 불가 (Supabase RLS) | RLS 정책 |
| UX | 종목 추가 후 즉시 수익률 반영 | 낙관적 업데이트 |

---

## 4. Success Criteria

### 4.1 Definition of Done

- [ ] FR-01 ~ FR-07 기능 구현 완료
- [ ] Supabase RLS로 사용자 데이터 격리
- [ ] 프론트-백 연동 완료 (현재가, AI 진단)
- [ ] 모바일 반응형 UI

### 4.2 Quality Criteria

- [ ] Lint/TypeScript 에러 없음
- [ ] 현재가 조회 실패 시 에러 처리
- [ ] AI 진단 로딩 상태 표시

---

## 5. Risks and Mitigation

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| finance-datareader 현재가 조회 실패 | High | Medium | 에러 시 "-" 표시, 재시도 버튼 제공 |
| 보유 종목 많을 때 현재가 일괄 조회 느림 | Medium | Medium | 병렬 조회 + 캐시(5분 TTL) |
| Gemini AI 진단 비용 | Medium | Low | 1회/24h 캐시, 수동 요청만 허용 |
| Supabase 데이터 모델 변경 | Low | Low | 초기 설계 시 충분히 검토 |

---

## 6. Architecture Considerations

### 6.1 데이터 모델

```sql
-- 포트폴리오 보유 종목 테이블
CREATE TABLE portfolio_holdings (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid references auth.users(id) not null,
  stock_code  text not null,
  stock_name  text not null,
  quantity    numeric not null check (quantity > 0),
  avg_price   numeric not null check (avg_price > 0),  -- 평균 매입가
  bought_at   date,
  created_at  timestamptz default now(),
  updated_at  timestamptz default now()
);

-- RLS 정책
ALTER TABLE portfolio_holdings ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can manage own holdings"
  ON portfolio_holdings FOR ALL
  USING (auth.uid() = user_id);
```

### 6.2 API 설계 (Backend)

```
GET    /api/portfolio/holdings          - 보유 종목 목록 + 현재가
POST   /api/portfolio/holdings          - 종목 추가
PUT    /api/portfolio/holdings/{id}     - 종목 수정
DELETE /api/portfolio/holdings/{id}     - 종목 삭제
GET    /api/portfolio/analysis/stream   - AI 진단 (SSE)
GET    /api/portfolio/summary           - 포트폴리오 요약
```

### 6.3 프론트엔드 구조

```
frontend/app/(app)/portfolio/
  page.tsx                    - 포트폴리오 메인
  analysis/page.tsx           - AI 진단 페이지

frontend/components/portfolio/
  PortfolioSummaryCard.tsx    - 요약 카드 (총 평가금액, 손익)
  HoldingsTable.tsx           - 종목별 수익률 테이블
  PortfolioPieChart.tsx       - 비중 파이 차트
  AddHoldingModal.tsx         - 종목 추가 모달
  AIAnalysisReport.tsx        - AI 진단 결과 (SSE 소비)
```

### 6.4 기존 패턴 재사용

- **SSE 패턴**: `stock.py`의 `/analysis/stream` 패턴 그대로 적용
- **캐시 패턴**: `generic_cache_service.py` 활용 (AI 진단 24h TTL)
- **현재가 조회**: 기존 `stock.py`의 finance-datareader 로직 재사용
- **DB 접근**: Supabase Python client 패턴 유지

---

## 7. Development Roadmap

### Phase 1: 데이터 기반 (백엔드)
1. Supabase `portfolio_holdings` 테이블 생성 + RLS 설정
2. FastAPI `/api/portfolio` 라우터 구현 (CRUD + 현재가)
3. 포트폴리오 요약 API (`/api/portfolio/summary`)

### Phase 2: UI 기본 (프론트엔드)
4. 포트폴리오 페이지 레이아웃
5. 보유 종목 추가/수정/삭제 모달
6. 종목별 수익률 테이블

### Phase 3: 시각화 + AI
7. 섹터/비중 파이 차트
8. AI 진단 SSE 엔드포인트 + 프론트 연동
9. 관심종목 → 포트폴리오 빠른 추가

---

## 8. Next Steps

1. [ ] Plan 문서 리뷰 및 확정
2. [ ] Design 문서 작성 (`/pdca design portfolio-analysis`)
3. [ ] Supabase 테이블 생성

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 0.1 | 2026-02-18 | Initial draft | User |
