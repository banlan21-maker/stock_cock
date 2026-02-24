"""news_cache Supabase 테이블 CRUD. AI 뉴스 요약 캐싱으로 Gemini 호출 절감.

공용 분석 창고: 동일 뉴스는 첫 요청 시 분석 후 1시간 캐시, 이후 요청은 캐시 반환.
"""

import logging
from datetime import datetime, timezone, timedelta

from app.utils.supabase_client import get_supabase

logger = logging.getLogger(__name__)

TABLE = "news_cache"
CACHE_TTL_HOURS = 1


def get_cached_summary(news_id: str) -> dict | None:
    """캐시된 AI 요약이 있고 유효기간(1시간) 내이면 반환, 없거나 만료면 None."""
    try:
        supabase = get_supabase()
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=CACHE_TTL_HOURS)).isoformat()
        r = (
            supabase.table(TABLE)
            .select("id, title, ai_summary, related_stocks, impact_strength, created_at")
            .eq("id", news_id)
            .gte("created_at", cutoff)
            .limit(1)
            .execute()
        )
        if r.data and len(r.data) > 0:
            row = r.data[0]
            return {
                "id": row["id"],
                "title": row["title"],
                "ai_summary": row.get("ai_summary") or "",
                "related_stocks": row.get("related_stocks") or [],
                "impact_strength": row.get("impact_strength") or "",
            }
        return None
    except Exception as e:
        logger.debug("news_cache 조회 실패: %s", e)
        return None


def upsert_summary(
    news_id: str,
    title: str,
    ai_summary: str,
    related_stocks: list[dict],
    source: str = "",
    url: str | None = None,
    published_at: str | None = None,
    category: str = "news",
    impact_strength: str = "",
) -> None:
    """AI 요약 결과를 캐시에 저장/갱신. impact_strength: 파급력 기반 TTL용."""
    try:
        supabase = get_supabase()
        row = {
            "id": news_id,
            "title": title,
            "ai_summary": ai_summary,
            "related_stocks": related_stocks,
            "source": source,
            "url": url,
            "published_at": published_at,
            "category": category,
        }
        if impact_strength:
            row["impact_strength"] = impact_strength
        supabase.table(TABLE).upsert(row, on_conflict="id").execute()
        logger.debug("news_cache 저장: %s", news_id[:50])
    except Exception as e:
        logger.warning("news_cache 저장 실패: %s", e)
