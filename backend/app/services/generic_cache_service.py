"""범용 KV 캐시 서비스 (Supabase generic_kv_cache 테이블).

테마 트렌드·대시보드 등 다목적 JSON 캐시에 사용.
기존 analysis_cache 는 주식 분석 전용으로 유지.

Supabase 테이블 (사전 생성 필요):
    create table if not exists generic_kv_cache (
        cache_key  text primary key,
        data       jsonb        not null,
        expires_at timestamptz  not null,
        created_at timestamptz  default now()
    );
    create index if not exists idx_gkv_expires on generic_kv_cache(expires_at);
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Any

from app.utils.supabase_client import get_supabase

logger = logging.getLogger(__name__)


def get_generic_cache(cache_key: str) -> Any | None:
    """만료되지 않은 캐시 항목을 반환. 없거나 만료됐으면 None."""
    try:
        supabase = get_supabase()
        now_iso = datetime.now(timezone.utc).isoformat()
        r = (
            supabase.table("generic_kv_cache")
            .select("data")
            .eq("cache_key", cache_key)
            .gt("expires_at", now_iso)
            .limit(1)
            .execute()
        )
        if r.data:
            return r.data[0]["data"]
        return None
    except Exception as e:
        logger.warning("generic_cache GET 실패 [%s]: %s", cache_key, e)
        return None


def set_generic_cache(cache_key: str, data: Any, ttl_seconds: int) -> None:
    """캐시 항목을 upsert. ttl_seconds 후 만료."""
    try:
        supabase = get_supabase()
        now = datetime.now(timezone.utc)
        expires_at = (now + timedelta(seconds=ttl_seconds)).isoformat()
        supabase.table("generic_kv_cache").upsert(
            {
                "cache_key": cache_key,
                "data": data,
                "expires_at": expires_at,
            },
            on_conflict="cache_key",
        ).execute()
    except Exception as e:
        logger.warning("generic_cache SET 실패 [%s]: %s", cache_key, e)


def delete_generic_cache(cache_key: str) -> None:
    """특정 캐시 항목을 즉시 삭제."""
    try:
        supabase = get_supabase()
        supabase.table("generic_kv_cache").delete().eq("cache_key", cache_key).execute()
    except Exception as e:
        logger.warning("generic_cache DELETE 실패 [%s]: %s", cache_key, e)


def delete_expired_generic_cache(older_than_days: int = 7) -> int:
    """만료된 지 older_than_days 일 이상 지난 행 삭제. 삭제 건수 반환."""
    try:
        supabase = get_supabase()
        cutoff = (datetime.now(timezone.utc) - timedelta(days=older_than_days)).isoformat()
        r = (
            supabase.table("generic_kv_cache")
            .delete()
            .lt("expires_at", cutoff)
            .execute()
        )
        count = len(r.data) if r.data else 0
        logger.info("generic_cache 만료 행 삭제: %d건", count)
        return count
    except Exception as e:
        logger.warning("generic_cache 만료 삭제 실패: %s", e)
        return 0
