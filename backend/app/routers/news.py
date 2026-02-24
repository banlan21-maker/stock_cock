from fastapi import APIRouter, Query, HTTPException, Request
from app.services import news_service
from app.limiter import limiter

router = APIRouter(prefix="/api/news", tags=["news"])


@router.get("")
async def list_news(
    category: str = Query("all", description="global / domestic / policy / all"),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
    keywords: str | None = Query(None, description="관심 키워드(쉼표 구분)"),
):
    return await news_service.get_news_list(category=category, page=page, limit=limit, keywords=keywords)


@router.get("/summary")
@limiter.limit("15/minute")
async def get_summary(request: Request, id: str = Query(..., description="뉴스 ID(URL)")):
    result = await news_service.get_news_summary(id)
    if not result:
        raise HTTPException(status_code=404, detail="뉴스를 찾을 수 없습니다.")
    return result
