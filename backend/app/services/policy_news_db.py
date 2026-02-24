"""policy_news Supabase 테이블 CRUD 서비스.

데이터 신선도: Asia/Seoul 타임윈도우 적용.
테이블 스키마 (Supabase에서 직접 생성 필요):
CREATE TABLE policy_news (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    link TEXT UNIQUE NOT NULL,
    description TEXT,
    image_url TEXT,
    published_at TIMESTAMPTZ,
    tags TEXT[],
    department TEXT,
    ai_summary TEXT,
    ai_stocks JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_policy_news_published ON policy_news(published_at DESC);
CREATE INDEX idx_policy_news_tags ON policy_news USING GIN(tags);
"""

import logging

from app.utils.supabase_client import get_supabase
from app.utils.freshness import get_time_window_cutoff

logger = logging.getLogger(__name__)

TABLE = "policy_news"


def get_existing_ids(ids: list[str]) -> set[str]:
    """주어진 ID 목록 중 이미 DB에 있는 ID들을 반환한다."""
    if not ids:
        return set()
    try:
        supabase = get_supabase()
        r = supabase.table(TABLE).select("id").in_("id", ids).execute()
        return {row["id"] for row in (r.data or [])}
    except Exception as e:
        logger.warning("policy_news ID 조회 실패: %s", e)
        return set()


def upsert_policies(items: list[dict]) -> int:
    """정책 뉴스 목록을 DB에 저장한다. 중복(link)은 스킵. 삽입된 건수를 반환."""
    if not items:
        return 0

    # 이미 있는 ID 확인
    existing = get_existing_ids([i["id"] for i in items])
    new_items = [i for i in items if i["id"] not in existing]
    if not new_items:
        return 0

    try:
        supabase = get_supabase()
        rows = []
        for item in new_items:
            rows.append({
                "id": item["id"],
                "title": item["title"],
                "link": item["link"],
                "description": item.get("description", ""),
                "image_url": item.get("image_url"),
                "published_at": item["published_at"],
                "tags": item.get("tags", []),
                "department": item.get("department", ""),
                "ai_summary": None,
                "ai_stocks": None,
            })
        supabase.table(TABLE).insert(rows).execute()
        logger.info("policy_news %d건 저장 완료", len(rows))
        return len(rows)
    except Exception as e:
        logger.error("policy_news 저장 실패: %s", e)
        return 0


def get_policy_list(
    page: int = 1,
    limit: int = 10,
    tags: list[str] | None = None,
) -> tuple[list[dict], int]:
    """정책 뉴스 목록을 반환한다. 타임윈도우(평일 24h/월요일 금18시~) 적용. (items, total)"""
    try:
        supabase = get_supabase()
        cutoff = get_time_window_cutoff(hours=72).isoformat()
        query = supabase.table(TABLE).select(
            "id, title, link, description, image_url, published_at, tags, department, ai_summary, ai_stocks, created_at",
            count="exact",
        )
        query = query.gte("published_at", cutoff)
        if tags:
            query = query.overlaps("tags", tags)
        query = query.order("published_at", desc=True)
        offset = (page - 1) * limit
        query = query.range(offset, offset + limit - 1)
        r = query.execute()
        return r.data or [], r.count or 0
    except Exception as e:
        logger.error("policy_news 조회 실패: %s", e)
        return [], 0


def get_policy_by_id(policy_id: str) -> dict | None:
    """ID로 정책 뉴스 1건을 반환한다."""
    try:
        supabase = get_supabase()
        r = supabase.table(TABLE).select("*").eq("id", policy_id).limit(1).execute()
        if r.data:
            return r.data[0]
        return None
    except Exception as e:
        logger.error("policy_news 단건 조회 실패: %s", e)
        return None


def update_ai_analysis(policy_id: str, ai_summary: str, ai_stocks: list[dict]) -> None:
    """AI 분석 결과를 업데이트한다."""
    try:
        supabase = get_supabase()
        supabase.table(TABLE).update({
            "ai_summary": ai_summary,
            "ai_stocks": ai_stocks,
        }).eq("id", policy_id).execute()
    except Exception as e:
        logger.error("policy_news AI 분석 업데이트 실패: %s", e)
