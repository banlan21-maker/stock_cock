"""FastAPI 의존성 — JWT 인증."""

from fastapi import Header, HTTPException

from app.utils.supabase_client import get_supabase


async def get_current_user(authorization: str = Header(...)) -> dict:
    """Authorization: Bearer {supabase_access_token} 헤더를 검증하고 user_id를 반환."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="인증 형식이 올바르지 않습니다.")
    token = authorization[len("Bearer "):].strip()
    supabase = get_supabase()
    try:
        result = supabase.auth.get_user(token)
        if not result.user:
            raise HTTPException(status_code=401, detail="인증이 필요합니다.")
        return {"user_id": result.user.id}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="인증이 필요합니다.")
