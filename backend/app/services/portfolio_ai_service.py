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
    """Gemini 포트폴리오 진단 프롬프트를 생성한다."""
    lines = []
    for h in holdings:
        current = h.get("current_price")
        rate = h.get("profit_rate")
        lines.append(
            f"- {h['stock_name']}({h['stock_code']}): "
            f"수량 {h['quantity']}주, 매입가 {h['avg_price']:,.0f}원, "
            f"현재가 {current:,.0f}원 ({rate:+.1f}%)" if current else
            f"- {h['stock_name']}({h['stock_code']}): "
            f"수량 {h['quantity']}주, 매입가 {h['avg_price']:,.0f}원"
        )

    holdings_text = "\n".join(lines)
    return f"""당신은 한국 주식 포트폴리오 전문 분석가입니다.
아래 포트폴리오를 분석하고 JSON 형식으로 결과를 반환해주세요.

포트폴리오 보유 종목:
{holdings_text}

다음 JSON 형식으로 응답하세요 (한국어로):
{{
  "risk_level": "low|medium|high",
  "sector_analysis": [
    {{"sector": "섹터명", "ratio": 비중(%), "comment": "섹터 분석 코멘트"}}
  ],
  "rebalancing": [
    {{"action": "reduce|increase|hold", "stock_code": "종목코드", "reason": "추천 이유"}}
  ],
  "overall_comment": "전반적인 포트폴리오 평가 (3-5문장)",
  "overall_score": 1~5 (1=매우 나쁨, 5=매우 좋음)
}}

섹터는 실제 업종을 기반으로 분류하고, 비중은 평가금액 기준으로 추정하세요.
JSON만 반환하고 다른 텍스트는 포함하지 마세요."""


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
