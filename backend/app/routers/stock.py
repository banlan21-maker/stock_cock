import asyncio
import json
from typing import AsyncGenerator

from fastapi import APIRouter, Query, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.services import stock_service, gemini_service
from app.services.analysis_cache_service import get_cached_analysis, set_cached_analysis, delete_cached_analysis
from app.services import naver_news_service
from app.services import newsapi_service
from app.limiter import limiter

router = APIRouter(prefix="/api/stock", tags=["stock"])


def _sse_event(event: str, data: dict) -> str:
    """SSE 이벤트 포맷 문자열 반환."""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.get("/search")
async def search(q: str = Query(..., min_length=1, description="종목명 또는 코드")):
    try:
        results = await asyncio.to_thread(stock_service.search_stocks, q)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"종목 검색 실패: {str(e)}")
    return {"results": results, "total": len(results)}


@router.get("/compare")
@limiter.limit("10/minute")
async def compare_stocks(
    request: Request,
    code_a: str = Query(..., description="첫 번째 종목 코드"),
    code_b: str = Query(..., description="두 번째 종목 코드"),
):
    """두 종목을 비교 분석한다."""
    if code_a.upper() == code_b.upper():
        raise HTTPException(status_code=400, detail="동일한 종목은 비교할 수 없습니다.")

    # 두 종목 데이터 병렬 수집
    structured_a, structured_b = await asyncio.gather(
        stock_service.get_structured_analysis_data(code_a),
        stock_service.get_structured_analysis_data(code_b),
        return_exceptions=True,
    )

    if isinstance(structured_a, Exception) or not structured_a:
        raise HTTPException(status_code=404, detail=f"종목을 찾을 수 없습니다: {code_a}")
    if isinstance(structured_b, Exception) or not structured_b:
        raise HTTPException(status_code=404, detail=f"종목을 찾을 수 없습니다: {code_b}")

    try:
        raw = await gemini_service.compare_stocks(structured_a, structured_b)
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0]
        parsed = json.loads(cleaned)

        return {
            "stock_a": {"code": code_a, "name": structured_a["종목명"]},
            "stock_b": {"code": code_b, "name": structured_b["종목명"]},
            "items": parsed.get("items", []),
            "overall_winner": parsed.get("overall_winner", "동점"),
            "a_score": parsed.get("a_score", 3),
            "b_score": parsed.get("b_score", 3),
            "verdict": parsed.get("verdict", ""),
            "caution": parsed.get("caution", ""),
        }
    except Exception as e:
        err_str = str(e)
        if "429" in err_str or "Resource exhausted" in err_str:
            raise HTTPException(status_code=429, detail="AI 분석 요청이 많습니다. 잠시 후 다시 시도해 주세요.")
        raise HTTPException(status_code=503, detail=f"비교 분석 중 오류: {err_str}")


@router.get("/{code}/price")
async def get_price(code: str):
    result = await stock_service.get_stock_price_async(code)
    if not result:
        # 종목 목록에는 있지만 가격 없음 → 상장폐지/거래정지 가능성
        stocks = stock_service.get_stock_list()
        if any(s["code"] == code for s in stocks):
            raise HTTPException(
                status_code=404,
                detail="현재 조회할 수 없는 종목입니다. 상장폐지 또는 거래정지 종목일 수 있습니다.",
            )
        raise HTTPException(status_code=404, detail="종목을 찾을 수 없습니다.")
    return result


@router.get("/{code}/chart")
async def get_chart(
    code: str,
    period: str = Query("3m", description="1m / 3m / 6m / 1y"),
    interval: str = Query("daily", description="daily / weekly"),
):
    result = await stock_service.get_chart_data_async(code, period=period, interval=interval)
    if not result:
        raise HTTPException(status_code=404, detail="차트 데이터를 가져올 수 없습니다.")
    return result


@router.get("/{code}/analysis/stream")
@limiter.limit("15/minute")
async def get_analysis_stream(request: Request, code: str):
    """SSE 스트리밍 분석 엔드포인트.

    이벤트 흐름:
      event: status → {"step": N, "message": "..."}   (캐시 미스 시만 전송)
      event: done   → {stock_code, stock_name, sentiment, items, ...}
      event: error  → {"message": "...", "code": "..."}
    """
    async def _stream() -> AsyncGenerator[str, None]:
        # 1) 기본 데이터 확인
        structured = await stock_service.get_structured_analysis_data(code)
        if not structured:
            yield _sse_event("error", {"message": "종목을 찾을 수 없습니다.", "code": "NOT_FOUND"})
            return

        # 2) 캐시 히트 → 즉시 done 반환
        cached = await asyncio.to_thread(get_cached_analysis, code)
        if cached:
            if gemini_service._is_old_report_format(cached):
                await asyncio.to_thread(delete_cached_analysis, code)
            else:
                ai_report = cached.get("ai_report", "{}")
                parsed_report = json.loads(ai_report) if isinstance(ai_report, str) else {}
                yield _sse_event("done", {
                    "stock_code": cached["stock_code"],
                    "stock_name": cached["stock_name"],
                    "sentiment": cached["sentiment"],
                    "items": parsed_report.get("items", []),
                    "overall_score": parsed_report.get("overall_score", 3),
                    "overall_comment": parsed_report.get("overall_comment", ""),
                    "analyzed_at": cached["analyzed_at"],
                    "expires_at": cached.get("expires_at"),
                })
                return

        stock_name = structured["종목명"]
        eng_name = structured.get("영문종목명")

        # 3) step 1: 주가 데이터 수집 (structured는 이미 완료)
        yield _sse_event("status", {"step": 1, "message": "주가 데이터 수집 중..."})

        # 4) step 2: 뉴스 병렬 수집
        yield _sse_event("status", {"step": 2, "message": "뉴스 분석 중..."})

        naver_task = naver_news_service.search_news(f"{stock_name} 주식", display=5)
        newsapi_query = f"{eng_name} stock" if eng_name else (
            f"{stock_name} stock" if len(stock_name) > 2 else "Korea stock"
        )
        newsapi_task = newsapi_service.search_news(newsapi_query, page_size=3)

        try:
            naver_articles, newsapi_articles = await asyncio.gather(
                naver_task, newsapi_task, return_exceptions=True
            )
        except Exception:
            naver_articles, newsapi_articles = [], []

        뉴스_목록 = []
        if isinstance(naver_articles, list):
            for a in naver_articles:
                뉴스_목록.append({"제목": a.get("title", ""), "출처": a.get("source", "네이버"), "분류": ""})
        if isinstance(newsapi_articles, list):
            for a in newsapi_articles:
                뉴스_목록.append({"제목": a.get("title", ""), "출처": a.get("source", "해외"), "분류": ""})
        structured["뉴스_정책"] = 뉴스_목록[:10]

        # 5) step 3: AI 분석
        yield _sse_event("status", {"step": 3, "message": "AI 분석 중..."})

        try:
            raw = await gemini_service.analyze_stock(stock_name, code, structured)
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0]
            parsed = json.loads(cleaned)

            raw_sentiment = (parsed.get("sentiment") or "neutral").strip().lower()
            sentiment = (
                "bullish" if raw_sentiment in ("bullish", "긍정") else
                "bearish" if raw_sentiment in ("bearish", "부정") else
                "neutral"
            )
            items = parsed.get("items", [])
            overall_score = parsed.get("overall_score", 3)
            overall_comment = parsed.get("overall_comment", "")

            cache_report = json.dumps(
                {"items": items, "overall_score": overall_score, "overall_comment": overall_comment},
                ensure_ascii=False,
            )
            await asyncio.to_thread(set_cached_analysis, code, stock_name, cache_report, sentiment, [], "")

            import datetime as dt
            yield _sse_event("done", {
                "stock_code": code,
                "stock_name": stock_name,
                "sentiment": sentiment,
                "items": items,
                "overall_score": overall_score,
                "overall_comment": overall_comment,
                "analyzed_at": dt.datetime.now().isoformat(),
            })

        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "Resource exhausted" in err_str:
                yield _sse_event("error", {
                    "message": "AI 분석 요청이 많습니다. 잠시 후 다시 시도해 주세요.",
                    "code": "RATE_LIMITED",
                })
            else:
                yield _sse_event("error", {"message": f"AI 분석 중 오류: {err_str}", "code": "ANALYSIS_ERROR"})

    return StreamingResponse(
        _stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.delete("/{code}/analysis/cache")
async def invalidate_analysis_cache(code: str):
    """분석 캐시를 강제 삭제한다 (재분석 트리거용)."""
    await asyncio.to_thread(delete_cached_analysis, code)
    return {"message": f"{code} 분석 캐시가 삭제되었습니다. 다음 분석 요청 시 재분석합니다."}


@router.get("/{code}/disclosures")
async def get_stock_disclosures(
    code: str,
    days: int = Query(30, ge=1, le=90, description="최근 N일 공시"),
):
    """특정 종목의 최근 공시 목록을 반환한다."""
    from app.services import dart_service
    try:
        items = await dart_service.get_disclosure_list(stock_code=code, days=days)
        return {"items": items, "total": len(items)}
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"공시 목록 조회 실패: {str(e)}")


@router.get("/{code}/analysis")
@limiter.limit("15/minute")
async def get_analysis(request: Request, code: str):
    # 1) 구조화된 분석 데이터 수집
    structured = await stock_service.get_structured_analysis_data(code)
    if not structured:
        raise HTTPException(status_code=404, detail="종목을 찾을 수 없습니다.")

    # 2) 캐시 확인 (24시간). 구 형식(items 없음)은 삭제 후 재분석
    cached = get_cached_analysis(code)
    if cached:
        if gemini_service._is_old_report_format(cached):
            delete_cached_analysis(code)
            cached = None
        else:
            return {
                "stock_code": cached["stock_code"],
                "stock_name": cached["stock_name"],
                "sentiment": cached["sentiment"],
                "items": json.loads(cached["ai_report"]).get("items", []) if isinstance(cached.get("ai_report"), str) else [],
                "overall_score": json.loads(cached["ai_report"]).get("overall_score", 3) if isinstance(cached.get("ai_report"), str) else 3,
                "overall_comment": json.loads(cached["ai_report"]).get("overall_comment", "") if isinstance(cached.get("ai_report"), str) else "",
                "analyzed_at": cached["analyzed_at"],
                "expires_at": cached.get("expires_at"),
            }

    # 3) 뉴스 데이터 병렬 수집
    stock_name = structured["종목명"]
    eng_name = structured.get("영문종목명")

    naver_task = naver_news_service.search_news(f"{stock_name} 주식", display=5)
    
    # 해외뉴스 검색어: 영문명 우선, 없으면 한글명+stock
    if eng_name:
        newsapi_query = f"{eng_name} stock"
    else:
        newsapi_query = f"{stock_name} stock" if len(stock_name) > 2 else "Korea stock"

    newsapi_task = newsapi_service.search_news(newsapi_query, page_size=3)
    try:
        naver_articles, newsapi_articles = await asyncio.gather(
            naver_task, newsapi_task, return_exceptions=True
        )
    except Exception:
        naver_articles, newsapi_articles = [], []

    뉴스_목록 = []
    if isinstance(naver_articles, list):
        for a in naver_articles:
            뉴스_목록.append({"제목": a.get("title", ""), "출처": a.get("source", "네이버"), "분류": ""})
    if isinstance(newsapi_articles, list):
        for a in newsapi_articles:
            뉴스_목록.append({"제목": a.get("title", ""), "출처": a.get("source", "해외"), "분류": ""})
    structured["뉴스_정책"] = 뉴스_목록[:10]

    # 4) Gemini 호출 - 항목별 카드 JSON 출력
    try:
        raw = await gemini_service.analyze_stock(stock_name, code, structured)
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0]
        parsed = json.loads(cleaned)

        raw_sentiment = (parsed.get("sentiment") or "neutral").strip().lower()
        sentiment = (
            "bullish" if raw_sentiment in ("bullish", "긍정") else
            "bearish" if raw_sentiment in ("bearish", "부정") else
            "neutral"
        )
        items = parsed.get("items", [])
        overall_score = parsed.get("overall_score", 3)
        overall_comment = parsed.get("overall_comment", "")

        # 캐시에 저장 (ai_report 필드에 JSON 문자열로)
        cache_report = json.dumps({"items": items, "overall_score": overall_score, "overall_comment": overall_comment}, ensure_ascii=False)
        set_cached_analysis(code, stock_name, cache_report, sentiment, [], "")

        return {
            "stock_code": code,
            "stock_name": stock_name,
            "sentiment": sentiment,
            "items": items,
            "overall_score": overall_score,
            "overall_comment": overall_comment,
            "analyzed_at": __import__("datetime").datetime.now().isoformat(),
        }
    except Exception as e:
        err_str = str(e)
        if "429" in err_str or "Resource exhausted" in err_str:
            raise HTTPException(status_code=429, detail="AI 분석 요청이 많습니다. 잠시 후 다시 시도해 주세요.")
        raise HTTPException(status_code=503, detail=f"AI 분석 중 오류: {err_str}")
