"""포트폴리오 AI 진단 서비스."""

import asyncio
import json
import logging
from datetime import datetime, timezone

from app.services.gemini_service import _call_with_retry
from app.services.generic_cache_service import get_generic_cache, set_generic_cache

logger = logging.getLogger(__name__)

_CACHE_TTL_SEC = 3600  # 1h (재무 데이터 포함 → 캐시 단축)


def _fmt(val, suffix="", default="데이터 없음"):
    if val is None or str(val).lower() in ("none", "n/a", "데이터 없음", ""):
        return default
    return f"{val}{suffix}"


def _build_portfolio_prompt(holdings: list[dict], stock_data: dict[str, dict]) -> str:
    """보유 종목별 실제 재무·차트 데이터를 포함한 포트폴리오 진단 프롬프트."""
    # 총 평가금액 / 매입금액 계산
    total_eval = sum(
        float(h.get("eval_amount") or 0) or
        (float(h.get("current_price") or h.get("avg_price", 0)) * float(h.get("quantity", 0)))
        for h in holdings
    )
    total_invest = sum(
        float(h.get("avg_price", 0)) * float(h.get("quantity", 0))
        for h in holdings
    )
    total_profit = total_eval - total_invest
    total_rate = (total_profit / total_invest * 100) if total_invest > 0 else 0

    sections = []
    for h in holdings:
        code = h["stock_code"]
        name = h["stock_name"]
        avg = float(h.get("avg_price", 0))
        qty = float(h.get("quantity", 0))
        current = h.get("current_price")
        rate = h.get("profit_rate") or 0
        eval_amt = float(h.get("eval_amount") or 0) or (float(current or avg) * qty)
        weight = (eval_amt / total_eval * 100) if total_eval > 0 else 0
        profit_loss = (float(current) - avg) * qty if current else 0

        sd = stock_data.get(code) or {}
        재무 = sd.get("재무") or {}
        수급 = sd.get("수급") or {}
        차트 = sd.get("차트") or {}

        lines = [
            f"## {name}({code}) — 비중 {weight:.1f}%",
            f"- 수량: {qty:,.0f}주 | 매입가: {avg:,.0f}원 | 현재가: {float(current):,.0f}원" if current else f"- 수량: {qty:,.0f}주 | 매입가: {avg:,.0f}원 | 현재가: 미조회",
            f"- 수익률: {rate:+.1f}% | 손익: {profit_loss:+,.0f}원 | 평가금액: {eval_amt:,.0f}원",
        ]

        # 실제 재무 데이터 (API에서 가져온 것)
        pbr = _fmt(재무.get("가성비_점수_PBR"))
        roe = _fmt(재무.get("장사_수완_ROE"), suffix="%")
        debt = _fmt(재무.get("빚쟁이_지수_부채비율"))
        rev_g = _fmt(재무.get("매출성장률_퍼센트"), suffix="%")
        op_m = _fmt(재무.get("영업이익률_퍼센트"), suffix="%")
        ocf = _fmt(재무.get("영업활동현금흐름"))
        lines.append(f"- [재무] PBR: {pbr} | ROE: {roe} | 부채비율: {debt} | 매출성장률: {rev_g} | 영업이익률: {op_m} | 영업현금흐름: {ocf}")

        # 차트/기술적 데이터
        rsi = 차트.get("RSI_14")
        chart_summary = 차트.get("요약") or "데이터 없음"
        rsi_str = f"RSI(14): {rsi:.1f}" if rsi is not None else "RSI: 데이터 없음"
        lines.append(f"- [차트] {chart_summary} | {rsi_str}")

        # 수급
        supply = 수급.get("최근10일_외국인_기관") or "데이터 없음"
        supply_pct = 수급.get("수급_시가총액비율_퍼센트")
        supply_pct_str = f" (시가총액 대비 {supply_pct:+.3f}%)" if supply_pct is not None else ""
        lines.append(f"- [수급] 외국인·기관: {supply}{supply_pct_str}")

        sections.append("\n".join(lines))

    holdings_text = "\n\n".join(sections)

    return f"""당신은 한국 주식 포트폴리오 전문 분석가입니다.
아래 포트폴리오의 실제 재무·차트·수급 데이터를 바탕으로 분석하고 JSON으로만 응답하세요.

[포트폴리오 요약]
- 총 매입금액: {total_invest:,.0f}원
- 총 평가금액: {total_eval:,.0f}원
- 총 손익: {total_profit:+,.0f}원 ({total_rate:+.1f}%)
- 보유 종목 수: {len(holdings)}개

[보유 종목 상세 — 실제 API 데이터 기반]
{holdings_text}

[분석 지침]
- 위에 제공된 수치만 사용하세요. "데이터 없음" 항목은 추측하지 마세요
- sector_analysis: 종목명·코드 기반으로 업종을 분류하되, 비중(ratio)은 위에 계산된 비중 그대로 사용
- rebalancing: 다음 경우에만 언급
  * 비중 40% 초과 → 집중 리스크
  * 수익률 -20% 이하 → 손절 검토
  * 부채비율 200% 초과 → 재무 리스크
  * RSI 70 이상 → 단기 과열
  * RSI 30 이하 → 단기 과매도
- overall_comment: 실제 수치(수익률·PBR·ROE·RSI 등)를 인용하여 3~5문장으로 작성
- overall_score: 총 수익률 + 분산도 + 재무 건전성 + 기술적 지표를 종합 평가 (1~5 정수)

응답은 반드시 JSON만 출력 (다른 텍스트 없이):
{{
  "risk_level": "low 또는 medium 또는 high",
  "sector_analysis": [
    {{"sector": "업종명", "ratio": 비중숫자, "comment": "이 섹터 평가 1줄"}}
  ],
  "rebalancing": [
    {{"action": "reduce 또는 increase 또는 hold", "stock_code": "종목코드", "reason": "실제 수치 기반 이유"}}
  ],
  "overall_comment": "실제 수치를 인용한 포트폴리오 전반 평가",
  "overall_score": 정수
}}

JSON만 반환하고 다른 텍스트는 포함하지 마세요."""


async def _fetch_stock_data(code: str) -> tuple[str, dict]:
    """단일 종목의 재무·차트·수급 데이터를 조회한다."""
    try:
        from app.services.stock_service import get_structured_analysis_data
        data = await get_structured_analysis_data(code)
        return code, data or {}
    except Exception as e:
        logger.warning("포트폴리오 종목 데이터 조회 실패 (%s): %s", code, e)
        return code, {}


async def analyze_portfolio(user_id: str, holdings: list[dict]) -> dict:
    """포트폴리오 AI 진단 — 실제 재무·차트 데이터 포함."""
    cache_key = f"portfolio_analysis_v2:{user_id}"

    try:
        cached = await asyncio.to_thread(get_generic_cache, cache_key)
    except Exception:
        cached = None

    if cached:
        return cached

    # 각 종목의 실제 재무·차트·수급 데이터를 병렬 조회
    codes = [h["stock_code"] for h in holdings]
    results = await asyncio.gather(*[_fetch_stock_data(code) for code in codes])
    stock_data = dict(results)

    prompt = _build_portfolio_prompt(holdings, stock_data)

    from google.genai import types
    config = types.GenerateContentConfig(temperature=0.3)
    raw = await _call_with_retry(prompt, config=config)

    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    analysis = json.loads(raw.strip())

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
