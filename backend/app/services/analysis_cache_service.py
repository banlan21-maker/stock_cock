"""AI 종목 분석 결과 캐시 (Supabase analysis_cache).

24시간 유효 캐시를 조회/저장하여 Gemini API 호출을 줄인다.
"""

from datetime import datetime, timezone, timedelta
from app.utils.supabase_client import get_supabase


def get_cached_analysis(stock_code: str) -> dict | None:
    """만료되지 않은 캐시가 있으면 반환, 없으면 None."""
    try:
        supabase = get_supabase()
        now_iso = datetime.now(timezone.utc).isoformat()
        r = (
            supabase.table("analysis_cache")
            .select("stock_code, stock_name, ai_report, sentiment, key_factors, analyzed_at, expires_at, report_brief")
            .eq("stock_code", stock_code)
            .gt("expires_at", now_iso)
            .limit(1)
            .execute()
        )
        if not r.data or len(r.data) == 0:
            return None
        row = r.data[0]
        return {
            "stock_code": row["stock_code"],
            "stock_name": row["stock_name"],
            "ai_report": row["ai_report"] or "",
            "report_brief": row.get("report_brief", ""),
            "sentiment": row["sentiment"] or "neutral",
            "key_factors": row["key_factors"] or [],
            "analyzed_at": row["analyzed_at"],
            "expires_at": row["expires_at"],
        }
    except Exception:
        return None


def delete_cached_analysis(stock_code: str) -> None:
    """캐시된 분석 결과를 삭제한다 (구 형식 무효화용)."""
    try:
        supabase = get_supabase()
        supabase.table("analysis_cache").delete().eq("stock_code", stock_code).execute()
    except Exception:
        pass


def set_cached_analysis(
    stock_code: str,
    stock_name: str,
    ai_report: str,
    sentiment: str,
    key_factors: list[str],
    report_brief: str = "",
) -> None:
    """분석 결과를 캐시에 저장. 기존 동일 종목 행은 삭제 후 삽입으로 갱신."""
    try:
        supabase = get_supabase()
        now = datetime.now(timezone.utc)
        expires_at = (now + timedelta(hours=24)).isoformat()
        analyzed_at = now.isoformat()
        row = {
            "stock_code": stock_code,
            "stock_name": stock_name,
            "ai_report": ai_report,
            "sentiment": sentiment,
            "key_factors": key_factors,
            "analyzed_at": analyzed_at,
            "expires_at": expires_at,
        }
        if report_brief:
            row["report_brief"] = report_brief
        supabase.table("analysis_cache").delete().eq("stock_code", stock_code).execute()
        try:
            supabase.table("analysis_cache").insert(row).execute()
        except Exception:
            if "report_brief" in row:
                del row["report_brief"]
                supabase.table("analysis_cache").insert(row).execute()
    except Exception:
        pass  # 캐시 실패해도 API 응답은 성공하도록 무시
