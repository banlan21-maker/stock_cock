"""Cron/백그라운드 작업용 엔드포인트."""

from fastapi import APIRouter

from app.services.cache_cleanup_service import run_cleanup, run_archive_low_impact
from app.services.generic_cache_service import delete_expired_generic_cache

router = APIRouter(prefix="/api/cron", tags=["cron"])


@router.post("/cleanup")
def cleanup_cache():
    """7일 경과 news_cache, policy_cache Hard Delete. cron에서 호출."""
    result = run_cleanup()
    return {"ok": True, "deleted": result}


@router.post("/archive")
def archive_low_impact():
    """보통 이하 파급력 + 24h 경과 → is_archived (news_cache)."""
    count = run_archive_low_impact()
    return {"ok": True, "archived": count}


@router.post("/cleanup-generic")
def cleanup_generic_cache():
    """7일 이상 만료된 generic_kv_cache 행 삭제. cron에서 호출."""
    count = delete_expired_generic_cache(older_than_days=7)
    return {"ok": True, "deleted": count}
