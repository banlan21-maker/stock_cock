"""DART 공시 라우터.

엔드포인트:
  GET /api/disclosure               → 오늘의 주요 공시 목록 (전체 상장사)
  GET /api/disclosure/{rcp_no}/analysis → 특정 공시 AI 분석 (꼰대아저씨)
  GET /api/stock/{code}/disclosures → 특정 종목 공시 이력 (stock 라우터에 별도 등록)
"""
from fastapi import APIRouter, HTTPException, Query, Request

from app.services import dart_service
from app.limiter import limiter

router = APIRouter(prefix="/api/disclosure", tags=["disclosure"])


@router.get("")
async def get_today_disclosures(
    max_items: int = Query(30, ge=1, le=50, description="최대 공시 수"),
):
    """오늘 발표된 정기공시·주요사항보고 목록을 반환한다."""
    try:
        items = await dart_service.get_today_disclosures(max_items=max_items)
        return {"items": items, "total": len(items)}
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"공시 목록 조회 실패: {str(e)}")


@router.get("/{rcp_no}/analysis")
@limiter.limit("10/minute")
async def get_disclosure_analysis(
    request: Request,
    rcp_no: str,
    report_nm: str = Query("", description="공시명 (캐시 미스 시 컨텍스트로 활용)"),
    corp_name: str = Query("", description="기업명 (캐시 미스 시 컨텍스트로 활용)"),
):
    """특정 공시의 꼰대아저씨 AI 분석 결과를 반환한다."""
    try:
        result = await dart_service.get_disclosure_analysis(
            rcp_no=rcp_no,
            report_nm=report_nm,
            corp_name=corp_name,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        err = str(e)
        if "429" in err or "Resource exhausted" in err:
            raise HTTPException(
                status_code=429,
                detail="AI 분석 요청이 많습니다. 잠시 후 다시 시도해 주세요.",
            )
        raise HTTPException(status_code=503, detail=f"공시 분석 실패: {err}")
