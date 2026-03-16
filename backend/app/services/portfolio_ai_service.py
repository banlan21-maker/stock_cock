"""포트폴리오 AI 진단 서비스 (Gemini SSE 스트리밍)."""

import asyncio
import json
import logging
from typing import AsyncGenerator

from app.services.gemini_service import _call_with_retry
from app.services.generic_cache_service import get_generic_cache, set_generic_cache
from app.utils.sse import sse_event as _sse_event

logger = logging.getLogger(__name__)

_CACHE_TTL_SEC = 86400  # 24h


def _build_portfolio_prompt(holdings: list[dict]) -> str:
    """Gemini 포트폴리오 진단 프롬프트를 생성한다. 비중은 Python에서 직접 계산."""
    # 총 평가금액 계산
    total_eval = sum(
        float(h.get("eval_amount") or 0) or
        (float(h.get("current_price") or h.get("avg_price", 0)) * float(h.get("quantity", 0)))
        for h in holdings
    )

    lines = []
    for h in holdings:
        current = h.get("current_price")
        avg = float(h.get("avg_price", 0))
        qty = float(h.get("quantity", 0))
        rate = h.get("profit_rate")
        eval_amt = float(h.get("eval_amount") or 0) or (float(current or avg) * qty)
        weight = (eval_amt / total_eval * 100) if total_eval > 0 else 0

        if current:
            profit_loss = (float(current) - avg) * qty
            lines.append(
                f"- {h['stock_name']}({h['stock_code']}): "
                f"수량 {qty:,.0f}주, 매입가 {avg:,.0f}원, 현재가 {float(current):,.0f}원, "
                f"수익률 {rate:+.1f}%, 평가금액 {eval_amt:,.0f}원, 포트폴리오 비중 {weight:.1f}%"
                f", 손익 {profit_loss:+,.0f}원"
            )
        else:
            lines.append(
                f"- {h['stock_name']}({h['stock_code']}): "
                f"수량 {qty:,.0f}주, 매입가 {avg:,.0f}원, 현재가 미조회, 비중 {weight:.1f}%"
            )

    holdings_text = "\n".join(lines)
    total_invest = sum(float(h.get("avg_price", 0)) * float(h.get("quantity", 0)) for h in holdings)
    total_profit = total_eval - total_invest
    total_rate = (total_profit / total_invest * 100) if total_invest > 0 else 0

    return f"""당신은 한국 주식 포트폴리오 전문 분석가입니다.
아래 포트폴리오 데이터를 분석하고 JSON으로만 응답하세요.

[포트폴리오 요약]
- 총 매입금액: {total_invest:,.0f}원
- 총 평가금액: {total_eval:,.0f}원
- 총 손익: {total_profit:+,.0f}원 ({total_rate:+.1f}%)
- 보유 종목 수: {len(holdings)}개

[보유 종목 상세 — 비중은 평가금액 기준으로 이미 계산됨]
{holdings_text}

[분석 지침]
- 위 데이터에 있는 수치만 사용하세요. 없는 데이터를 추측하지 마세요
- sector_analysis의 ratio 합계가 100%에 가깝도록 실제 비중 기반으로 작성
- rebalancing은 비중이 50% 초과 종목(집중 리스크), 수익률이 -20% 이하 종목(손절 검토), 0% 비중 종목(현금)에 대해서만 언급
- overall_comment는 실제 수익률과 비중 데이터를 인용하여 구체적으로 작성
- overall_score는 총 수익률, 분산도, 리스크를 종합 평가

응답은 반드시 JSON만 출력 (다른 텍스트 없이):
{{
  "risk_level": "low 또는 medium 또는 high",
  "sector_analysis": [
    {{"sector": "실제업종명", "ratio": 실제비중숫자, "comment": "이 섹터 비중에 대한 평가 1줄"}}
  ],
  "rebalancing": [
    {{"action": "reduce 또는 increase 또는 hold", "stock_code": "종목코드", "reason": "데이터 기반 구체적 이유"}}
  ],
  "overall_comment": "실제 수치를 인용한 포트폴리오 전반 평가 (3~5문장)",
  "overall_score": 1~5정수
}}\n
JSON만 반환하고 다른 텍스트는 포함하지 마세요."""


async def analyze_portfolio(user_id: str, holdings: list[dict]) -> dict:
    """포트폴리오 AI 진단을 일반 JSON으로 반환한다."""
    cache_key = f"portfolio_analysis:{user_id}"

    try:
        cached = await asyncio.to_thread(get_generic_cache, cache_key)
    except Exception:
        cached = None

    if cached:
        return cached

    prompt = _build_portfolio_prompt(holdings)
    raw = await _call_with_retry(prompt)

    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    analysis = json.loads(raw.strip())

    from datetime import datetime, timezone
    result = {
        "user_id": user_id,
        "total_stocks": len(holdings),
        "risk_level": analysis.get("risk_level", "medium"),
        "sector_analysis": analysis.get("sector_analysis", []),
        "rebalancing": analysis.get("rebalancing", []),
        "overall_comment": analysis.get("overall_comment", ""),
        "overall_score": analysis.get("overall_score", 3),
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        await asyncio.to_thread(set_generic_cache, cache_key, result, _CACHE_TTL_SEC)
    except Exception:
        pass

    return result


async def analyze_portfolio_stream(user_id: str, holdings: list[dict]) -> AsyncGenerator[str, None]:
    """포트폴리오 AI 진단을 SSE 스트림으로 생성한다."""
    try:
        cache_key = f"portfolio_analysis:{user_id}"

        # 1) 보유 종목 없으면 에러
        if not holdings:
            yield _sse_event("error", {"message": "보유 종목이 없습니다.", "code": "NO_HOLDINGS"})
            return

        # 2) 캐시 확인
        try:
            cached = await asyncio.to_thread(get_generic_cache, cache_key)
        except Exception as cache_err:
            logger.warning("포트폴리오 AI 캐시 조회 실패 (무시): %s", cache_err)
            cached = None

        if cached:
            yield _sse_event("done", cached)
            return

        # 3) AI 분석
        yield _sse_event("status", {"step": 1, "message": "포트폴리오 데이터 수집 중..."})
        await asyncio.sleep(0)

        yield _sse_event("status", {"step": 2, "message": "AI 진단 중..."})

        try:
            prompt = _build_portfolio_prompt(holdings)
            raw = await _call_with_retry(prompt)

            # JSON 파싱
            raw = raw.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            analysis = json.loads(raw.strip())

            from datetime import datetime, timezone
            result = {
                "user_id": user_id,
                "total_stocks": len(holdings),
                "risk_level": analysis.get("risk_level", "medium"),
                "sector_analysis": analysis.get("sector_analysis", []),
                "rebalancing": analysis.get("rebalancing", []),
                "overall_comment": analysis.get("overall_comment", ""),
                "overall_score": analysis.get("overall_score", 3),
                "analyzed_at": datetime.now(timezone.utc).isoformat(),
            }

            # 캐시 저장 (24h)
            try:
                await asyncio.to_thread(set_generic_cache, cache_key, result, _CACHE_TTL_SEC)
            except Exception as cache_set_err:
                logger.warning("포트폴리오 AI 캐시 저장 실패 (무시): %s", cache_set_err)
            yield _sse_event("done", result)

        except json.JSONDecodeError as e:
            logger.error("포트폴리오 AI 분석 JSON 파싱 실패: %s", e)
            yield _sse_event("error", {"message": "AI 분석 결과를 처리할 수 없습니다.", "code": "PARSE_ERROR"})
        except Exception as e:
            logger.error("포트폴리오 AI 분석 실패: %s", e)
            yield _sse_event("error", {"message": f"AI 분석 중 오류: {str(e)[:100]}", "code": "AI_FAILED"})

    except Exception as top_err:
        logger.error("포트폴리오 AI SSE 최상위 오류: %s", top_err)
        yield _sse_event("error", {"message": "서비스 오류가 발생했습니다.", "code": "STREAM_ERROR"})
