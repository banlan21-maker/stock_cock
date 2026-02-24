from fastapi import APIRouter, Query, HTTPException, Request
from app.services import policy_service
from app.limiter import limiter

router = APIRouter(prefix="/api/policy", tags=["policy"])


@router.get("")
def list_policies(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
    keywords: str | None = Query(None, description="관심 키워드(쉼표 구분)"),
):
    return policy_service.get_policy_list(page=page, limit=limit, keywords=keywords)


@router.get("/{policy_id}/analysis")
@limiter.limit("15/minute")
async def get_analysis(request: Request, policy_id: str):
    result = await policy_service.get_policy_analysis(policy_id)
    if not result:
        raise HTTPException(status_code=404, detail="정책을 찾을 수 없습니다.")
    return result
