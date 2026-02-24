"""포트폴리오 보유 종목 CRUD + AI 진단 라우터."""

import asyncio
import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Depends, Request, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional

from app.deps import get_current_user
from app.limiter import limiter
from app.services import portfolio_service, portfolio_ai_service, stock_service
from app.services.generic_cache_service import get_generic_cache, set_generic_cache
from app.services import journal_service
from app.services import gemini_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])


# ── 요청 스키마 ──────────────────────────────────────────────────────────────

class AddHoldingRequest(BaseModel):
    stock_code: str
    stock_name: str
    quantity: float = Field(..., gt=0)
    avg_price: float = Field(..., gt=0)
    bought_at: Optional[str] = None  # "YYYY-MM-DD"


class UpdateHoldingRequest(BaseModel):
    quantity: Optional[float] = Field(None, gt=0)
    avg_price: Optional[float] = Field(None, gt=0)
    bought_at: Optional[str] = None


class JournalRequest(BaseModel):
    stock_name: str
    stock_code: Optional[str] = None
    action: str  # "buy" | "sell"
    trade_date: str  # "YYYY-MM-DD"
    price: float = Field(..., gt=0)
    quantity: float = Field(..., gt=0)
    memo: Optional[str] = None


# ── 엔드포인트 ───────────────────────────────────────────────────────────────

@router.get("/holdings")
async def get_holdings(current_user: dict = Depends(get_current_user)):
    """보유 종목 목록 + 현재가 + 수익률 반환."""
    user_id = current_user["user_id"]
    result = await portfolio_service.get_holdings_with_price(user_id)
    return result


@router.post("/holdings", status_code=201)
def add_holding(
    body: AddHoldingRequest,
    current_user: dict = Depends(get_current_user),
):
    """보유 종목 추가."""
    user_id = current_user["user_id"]
    holding = portfolio_service.add_holding(user_id, body.model_dump())
    if not holding:
        raise HTTPException(status_code=500, detail="종목 추가에 실패했습니다.")
    return holding


@router.put("/holdings/{holding_id}")
def update_holding(
    holding_id: str,
    body: UpdateHoldingRequest,
    current_user: dict = Depends(get_current_user),
):
    """보유 종목 수정."""
    user_id = current_user["user_id"]
    update_data = {k: v for k, v in body.model_dump().items() if v is not None}
    holding = portfolio_service.update_holding(holding_id, user_id, update_data)
    if not holding:
        raise HTTPException(status_code=404, detail="해당 종목을 찾을 수 없습니다.")
    return holding


@router.delete("/holdings/{holding_id}", status_code=204)
def delete_holding(
    holding_id: str,
    current_user: dict = Depends(get_current_user),
):
    """보유 종목 삭제."""
    user_id = current_user["user_id"]
    success = portfolio_service.delete_holding(holding_id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="해당 종목을 찾을 수 없습니다.")


@router.get("/performance")
async def get_portfolio_performance(
    days: int = Query(90, ge=30, le=365),
    current_user: dict = Depends(get_current_user),
):
    """포트폴리오 누적 수익률 vs KOSPI 비교 데이터 반환.

    - days: 30 / 90 / 180 / 365
    - 반환: dates, portfolio(%), kospi(%), start_date, period
    """
    user_id = current_user["user_id"]

    # 캐시 확인
    cache_key = f"portfolio:perf:{user_id}:{days}"
    cached = get_generic_cache(cache_key)
    if cached:
        return cached

    # 보유 종목 조회
    holdings = await asyncio.to_thread(portfolio_service.get_user_holdings, user_id)
    if not holdings:
        return {"dates": [], "portfolio": [], "kospi": [], "start_date": None, "period": _days_to_period(days)}

    # period 변환
    period = _days_to_period(days)

    # 시작일 결정: 가장 오래된 bought_at 기준 (없으면 days 전)
    bought_dates = [h["bought_at"] for h in holdings if h.get("bought_at")]
    if bought_dates:
        earliest = min(datetime.strptime(d, "%Y-%m-%d") for d in bought_dates)
        # days 범위보다 더 오래된 경우 days 범위로 제한
        cutoff = datetime.now() - timedelta(days=days)
        start_dt = max(earliest, cutoff)
    else:
        start_dt = datetime.now() - timedelta(days=days)

    # 각 종목 + KOSPI(KS11) 차트 데이터 병렬 조회
    codes = [h["stock_code"] for h in holdings]
    tasks = [stock_service.get_chart_data_async(code, period) for code in codes]
    tasks.append(stock_service.get_chart_data_async("KS11", period))  # KOSPI
    results = await asyncio.gather(*tasks, return_exceptions=True)

    stock_charts = results[:-1]
    kospi_chart = results[-1]

    # 날짜 집합 구성 (모든 종목의 공통 거래일)
    # 각 종목 dict: {date_str: close_price}
    stock_price_maps: list[dict[str, float]] = []
    all_dates: set[str] = set()

    for i, chart in enumerate(stock_charts):
        if isinstance(chart, Exception) or chart is None:
            stock_price_maps.append({})
            continue
        price_map: dict[str, float] = {}
        for pt in chart["data"]:
            d = pt["date"]
            if d >= start_dt.strftime("%Y-%m-%d"):
                price_map[d] = pt["close"]
                all_dates.add(d)
        stock_price_maps.append(price_map)

    # KOSPI 날짜 포함
    kospi_price_map: dict[str, float] = {}
    if not isinstance(kospi_chart, Exception) and kospi_chart is not None:
        for pt in kospi_chart["data"]:
            d = pt["date"]
            if d >= start_dt.strftime("%Y-%m-%d"):
                kospi_price_map[d] = pt["close"]
                all_dates.add(d)

    if not all_dates:
        return {"dates": [], "portfolio": [], "kospi": [], "start_date": None, "period": period}

    sorted_dates = sorted(all_dates)

    # Forward-fill: 각 종목의 가격이 없는 날은 직전 거래일 가격 사용
    def ffill(price_map: dict[str, float], dates: list[str]) -> list[float | None]:
        filled: list[float | None] = []
        last = None
        for d in dates:
            if d in price_map:
                last = price_map[d]
            filled.append(last)
        return filled

    # 총 매입금액 (상수)
    total_invest = sum(float(h["avg_price"]) * float(h["quantity"]) for h in holdings)
    quantities = [float(h["quantity"]) for h in holdings]

    if total_invest == 0:
        return {"dates": [], "portfolio": [], "kospi": [], "start_date": None, "period": period}

    # 종목별 ffill 가격
    filled_prices: list[list[float | None]] = [
        ffill(pm, sorted_dates) for pm in stock_price_maps
    ]

    # KOSPI ffill
    kospi_filled = ffill(kospi_price_map, sorted_dates)
    kospi_start = next((v for v in kospi_filled if v is not None), None)

    # 수익률 계산
    portfolio_returns: list[float] = []
    kospi_returns: list[float] = []

    for j, d in enumerate(sorted_dates):
        # 포트폴리오 평가금액
        eval_amount = 0.0
        valid = True
        for i, prices_list in enumerate(filled_prices):
            p = prices_list[j]
            if p is None:
                valid = False
                break
            eval_amount += p * quantities[i]

        if not valid:
            portfolio_returns.append(round((portfolio_returns[-1] if portfolio_returns else 0.0), 4))
        else:
            ret = (eval_amount - total_invest) / total_invest * 100
            portfolio_returns.append(round(ret, 4))

        # KOSPI 수익률
        kp = kospi_filled[j]
        if kp is not None and kospi_start is not None and kospi_start > 0:
            kospi_returns.append(round((kp / kospi_start - 1) * 100, 4))
        else:
            kospi_returns.append(kospi_returns[-1] if kospi_returns else 0.0)

    result = {
        "dates": sorted_dates,
        "portfolio": portfolio_returns,
        "kospi": kospi_returns,
        "start_date": sorted_dates[0] if sorted_dates else None,
        "period": period,
    }

    # 캐시 저장 (5분 TTL)
    set_generic_cache(cache_key, result, 300)
    return result


# ── 투자일지 엔드포인트 ─────────────────────────────────────────────────────────

@router.get("/journal")
async def get_journal(
    page: int = Query(1, ge=1),
    q: str = Query(""),
    current_user: dict = Depends(get_current_user),
):
    """투자일지 목록 (페이지네이션 5개 + 검색)."""
    user_id = current_user["user_id"]
    return await asyncio.to_thread(
        journal_service.get_user_journal, user_id, page, 5, q
    )


@router.post("/journal", status_code=201)
async def create_journal(
    body: JournalRequest,
    current_user: dict = Depends(get_current_user),
):
    """투자일지 항목 생성 → AI 피드백 생성 → 반환."""
    user_id = current_user["user_id"]

    # 1. DB에 항목 저장
    entry = await asyncio.to_thread(
        journal_service.create_journal, user_id, body.model_dump()
    )
    if not entry:
        raise HTTPException(status_code=500, detail="일지 저장에 실패했습니다.")

    # 2. AI 피드백 생성
    try:
        feedback = await gemini_service.analyze_journal_entry(entry)
        feedback = feedback.strip()
    except Exception as e:
        logger.warning("투자일지 AI 피드백 생성 실패: %s", e)
        feedback = None

    # 3. AI 피드백 업데이트
    if feedback:
        updated = await asyncio.to_thread(
            journal_service.update_journal_feedback, entry["id"], feedback
        )
        if updated:
            entry = updated

    return entry


@router.put("/journal/{entry_id}")
async def update_journal(
    entry_id: str,
    body: JournalRequest,
    current_user: dict = Depends(get_current_user),
):
    """투자일지 항목 수정 → AI 피드백 재생성 → 반환."""
    user_id = current_user["user_id"]

    # 1. DB 업데이트
    entry = await asyncio.to_thread(
        journal_service.update_journal, entry_id, user_id, body.model_dump()
    )
    if not entry:
        raise HTTPException(status_code=404, detail="해당 일지를 찾을 수 없습니다.")

    # 2. AI 피드백 재생성
    try:
        feedback = await gemini_service.analyze_journal_entry(entry)
        feedback = feedback.strip()
    except Exception as e:
        logger.warning("투자일지 AI 피드백 재생성 실패: %s", e)
        feedback = None

    # 3. AI 피드백 업데이트
    if feedback:
        updated = await asyncio.to_thread(
            journal_service.update_journal_feedback, entry_id, feedback
        )
        if updated:
            entry = updated

    return entry


@router.delete("/journal/{entry_id}", status_code=204)
async def delete_journal(
    entry_id: str,
    current_user: dict = Depends(get_current_user),
):
    """투자일지 항목 삭제."""
    user_id = current_user["user_id"]
    success = await asyncio.to_thread(
        journal_service.delete_journal, entry_id, user_id
    )
    if not success:
        raise HTTPException(status_code=404, detail="해당 일지를 찾을 수 없습니다.")


def _days_to_period(days: int) -> str:
    if days <= 30:
        return "1m"
    elif days <= 90:
        return "3m"
    elif days <= 180:
        return "6m"
    return "1y"


@router.get("/analysis/stream")
@limiter.limit("10/minute")
async def get_portfolio_analysis_stream(request: Request, current_user: dict = Depends(get_current_user)):
    """포트폴리오 AI 진단 — SSE 스트리밍.

    이벤트 흐름:
      event: status → {"step": N, "message": "..."}
      event: done   → { 포트폴리오 AI 진단 결과 }
      event: error  → {"message": "...", "code": "..."}
    """
    user_id = current_user["user_id"]

    # 현재가 포함 보유 종목 조회
    portfolio_data = await portfolio_service.get_holdings_with_price(user_id)
    holdings = portfolio_data["holdings"]

    return StreamingResponse(
        portfolio_ai_service.analyze_portfolio_stream(user_id, holdings),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
