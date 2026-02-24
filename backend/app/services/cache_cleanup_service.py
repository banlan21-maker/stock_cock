"""캐시 자동 청소. news_cache, policy_cache 7일 경과 데이터 Hard Delete.

백그라운드 작업 또는 cron 호출용.
"""

import logging
from datetime import datetime, timedelta, timezone

from app.utils.supabase_client import get_supabase
from app.utils.freshness import TZ

logger = logging.getLogger(__name__)

CUTOFF_DAYS = 7


def run_cleanup() -> dict[str, int]:
    """
    news_cache, policy_cache에서 발행일/생성일 기준 7일 경과 데이터 Hard Delete.
    Returns: {"news_cache": 삭제건수, "policy_cache": 삭제건수}
    """
    cutoff = datetime.now(TZ) - timedelta(days=CUTOFF_DAYS)
    cutoff_iso = cutoff.isoformat()
    result: dict[str, int] = {"news_cache": 0, "policy_cache": 0}

    try:
        supabase = get_supabase()

        # news_cache: published_at 기준
        r = supabase.table("news_cache").delete().lt("published_at", cutoff_iso).execute()
        result["news_cache"] = len(r.data) if r.data else 0
        if result["news_cache"]:
            logger.info("news_cache 7일+ %d건 삭제", result["news_cache"])

        # policy_cache: created_at 기준
        r = supabase.table("policy_cache").delete().lt("created_at", cutoff_iso).execute()
        result["policy_cache"] = len(r.data) if r.data else 0
        if result["policy_cache"]:
            logger.info("policy_cache 7일+ %d건 삭제", result["policy_cache"])

    except Exception as e:
        logger.error("캐시 청소 실패: %s", e)

    return result


def run_archive_low_impact() -> int:
    """impact_strength 보통 이하 + published_at 24시간 경과 → is_archived=True."""
    try:
        from app.utils.freshness import now_seoul
        cutoff = now_seoul() - timedelta(hours=24)
        cutoff_iso = cutoff.isoformat()
        supabase = get_supabase()

        # 보통/낮음/미설정만 아카이브 (매우 높음/높음은 72h 유지)
        r = (
            supabase.table("news_cache")
            .update({"is_archived": True})
            .lt("published_at", cutoff_iso)
            .or_("impact_strength.eq.보통,impact_strength.eq.낮음,impact_strength.is.null")
            .or_("is_archived.eq.false,is_archived.is.null")
            .execute()
        )
        return len(r.data) if r.data else 0
    except Exception as e:
        logger.debug("is_archived 업데이트 스킵 (컬럼 없을 수 있음): %s", e)
        return 0
