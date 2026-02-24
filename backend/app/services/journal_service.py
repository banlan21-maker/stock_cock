"""투자일지 CRUD 서비스."""

import logging
from typing import Optional

from app.config import get_settings

logger = logging.getLogger(__name__)


def _get_supabase():
    from supabase import create_client
    settings = get_settings()
    return create_client(settings.supabase_url, settings.supabase_service_key)


def get_user_journal(user_id: str, page: int = 1, page_size: int = 5, q: str = "") -> dict:
    """투자일지 목록 조회 (페이지네이션 + 검색).

    Returns:
        {"items": [...], "total": int, "page": int, "page_size": int}
    """
    client = _get_supabase()
    offset = (page - 1) * page_size

    query = (
        client.table("investment_journal")
        .select("*", count="exact")
        .eq("user_id", user_id)
    )

    if q and q.strip():
        q_stripped = q.strip()
        query = query.or_(f"stock_name.ilike.%{q_stripped}%,memo.ilike.%{q_stripped}%")

    result = (
        query
        .order("created_at", desc=True)
        .range(offset, offset + page_size - 1)
        .execute()
    )

    return {
        "items": result.data or [],
        "total": result.count or 0,
        "page": page,
        "page_size": page_size,
    }


def create_journal(user_id: str, data: dict) -> Optional[dict]:
    """투자일지 항목 생성."""
    client = _get_supabase()
    payload = {
        "user_id": user_id,
        "stock_name": data["stock_name"],
        "stock_code": data.get("stock_code"),
        "action": data["action"],
        "trade_date": data["trade_date"],
        "price": data["price"],
        "quantity": data["quantity"],
        "memo": data.get("memo"),
    }
    result = client.table("investment_journal").insert(payload).execute()
    return result.data[0] if result.data else None


def update_journal(entry_id: str, user_id: str, data: dict) -> Optional[dict]:
    """투자일지 항목 수정 (소유자 검증 포함)."""
    client = _get_supabase()
    payload = {k: v for k, v in data.items() if v is not None}
    result = (
        client.table("investment_journal")
        .update(payload)
        .eq("id", entry_id)
        .eq("user_id", user_id)
        .execute()
    )
    return result.data[0] if result.data else None


def update_journal_feedback(entry_id: str, ai_feedback: str) -> Optional[dict]:
    """AI 피드백만 업데이트한다."""
    client = _get_supabase()
    result = (
        client.table("investment_journal")
        .update({"ai_feedback": ai_feedback})
        .eq("id", entry_id)
        .execute()
    )
    return result.data[0] if result.data else None


def delete_journal(entry_id: str, user_id: str) -> bool:
    """투자일지 항목 삭제."""
    client = _get_supabase()
    result = (
        client.table("investment_journal")
        .delete()
        .eq("id", entry_id)
        .eq("user_id", user_id)
        .execute()
    )
    return bool(result.data)
