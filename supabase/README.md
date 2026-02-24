# Supabase 마이그레이션

## 테이블 생성 (1순위)

`migrations/20260214000000_create_cache_tables.sql` 파일로 다음 4개 테이블을 생성합니다.

- **news_cache** – 뉴스 AI 요약 캐시
- **policy_cache** – 정책 AI 분석 캐시
- **analysis_cache** – 종목 AI 분석 캐시 (24시간 유효)
- **watchlist** – 관심 종목 (RLS 적용)

### 실행 방법

**방법 1: Supabase Dashboard**

1. [Supabase Dashboard](https://supabase.com/dashboard) → 프로젝트 선택
2. **SQL Editor** 메뉴 이동
3. `migrations/20260214000000_create_cache_tables.sql` 내용 전체 복사 후 붙여넣기
4. **Run** 실행

**방법 2: Supabase CLI**

```bash
# 프로젝트 루트에서
supabase link --project-ref <your-project-ref>
supabase db push
```

연결 후 `supabase db push` 시 `migrations/` 폴더의 SQL이 순서대로 적용됩니다.

### Backend 연동

Backend `.env`에 다음이 설정되어 있어야 합니다.

- `SUPABASE_URL` – Supabase 프로젝트 URL
- `SUPABASE_SERVICE_KEY` – Service Role Key (설정 → API)

종목 AI 분석(`GET /api/stock/{code}/analysis`)은 **analysis_cache**를 사용해 24시간 캐싱됩니다.
