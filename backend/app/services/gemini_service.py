import asyncio
import json
import logging
import re

from google import genai
from google.genai import types
from app.config import get_settings

logger = logging.getLogger(__name__)

_client_instance = None
_client_loop_id: int = -1  # asyncio.run()은 요청마다 새 루프를 생성/파괴하므로 추적 필요
_MODEL_NAME = "gemini-2.5-flash"


def _get_client() -> genai.Client:
    """genai.Client 싱글톤 — 이벤트 루프가 바뀌면 클라이언트를 재생성한다.

    Cloud Functions에서 asyncio.run()은 요청마다 새 이벤트 루프를 생성하고 파괴한다.
    genai.Client 내부의 비동기 HTTP 클라이언트는 생성 시점의 루프에 묶이므로,
    루프가 닫힌 뒤 재사용하면 'Event loop is closed' 오류가 발생한다.
    루프 ID가 변경될 때마다 새 클라이언트를 생성해 이 문제를 방지한다.
    """
    global _client_instance, _client_loop_id
    try:
        loop_id = id(asyncio.get_running_loop())
    except RuntimeError:
        loop_id = -1

    if _client_instance is None or _client_loop_id != loop_id:
        settings = get_settings()
        api_key = (settings.gemini_api_key or "").strip()
        if not api_key:
            raise ValueError(
                "Gemini API 키가 설정되지 않았습니다. backend/.env에 GEMINI_API_KEY를 넣어 주세요."
            )
        _client_instance = genai.Client(api_key=api_key)
        _client_loop_id = loop_id
    return _client_instance


async def _call_with_retry(prompt, config=None, max_retries: int = 3):
    """Gemini API 호출 + 429/5xx 시 지수 백오프 재시도 (네이티브 async)."""
    client = _get_client()
    last_error = None
    for attempt in range(max_retries):
        try:
            response = await client.aio.models.generate_content(
                model=_MODEL_NAME,
                contents=prompt,
                config=config,
            )
            return response.text
        except Exception as e:
            last_error = e
            err_str = str(e)
            is_retryable = "429" in err_str or "Resource exhausted" in err_str or "500" in err_str or "503" in err_str
            if is_retryable and attempt < max_retries - 1:
                wait = 2 ** attempt * 2  # 2초, 4초, 8초
                logger.warning("Gemini API %d번째 재시도 (%s초 후): %s", attempt + 1, wait, err_str[:100])
                await asyncio.sleep(wait)
            else:
                raise last_error


_NEWS_ANALYSIS_PROMPT = """# [주식콕] 뉴스 투자 분석 지침

당신은 한국 주식시장 전문 애널리스트입니다. 뉴스 본문에 있는 사실만 바탕으로 분석하세요.

## 핵심 원칙 (반드시 준수)
- **사실만 말하라**: 뉴스 본문에 없는 내용, 추측, 과장은 일절 금지
- **종목 코드 정확성**: 종목명과 6자리 코드가 100% 확실한 경우에만 related_stocks에 포함. 조금이라도 불확실하면 제외
- **관련 종목이 없으면**: related_stocks를 빈 배열([])로 반환. 억지로 채우지 마라
- **뉴스와 직접 연관된 종목만**: 해당 뉴스 본문에 언급되었거나, 명백히 영향을 받는 기업만 포함

## 분석 항목
1. **핵심 팩트**: 뉴스에서 가장 중요한 사실 3가지 (본문에 있는 내용만)
2. **연관 분야**: 이 뉴스가 영향을 주는 산업군과 핵심 키워드
3. **파급력**: 투자자 관점에서 단기/장기 영향 (매우 높음/높음/보통/낮음)
4. **관련 종목**: 뉴스와 직접 연관된 종목만 (없으면 없다고 함)
5. **투자자 주의사항**: 이 뉴스를 보고 투자 결정 시 반드시 알아야 할 리스크 1줄

## 출력 양식 (summary 필드에 넣을 텍스트)

📌 한눈에 보는 핵심 팩트
(뉴스 본문 기반 중요 사실 3줄 — 추측 금지)

🔍 연관 분야 및 테마
산업군: (예: 반도체 / 2차전지 / 에너지)
핵심 키워드: (뉴스에 실제 등장한 키워드)

⚡ 시장 파급력
강도: (매우 높음 / 높음 / 보통 / 낮음)
영향 범위: (단기/장기 구분, 근거 포함)

💡 관련 종목
(확실한 종목만 — 없으면 "이 뉴스와 직접 연관된 상장 종목을 특정하기 어렵습니다"라고 작성)

⚠️ 투자자 주의사항
(이 뉴스 하나만 보고 투자 결정하면 안 되는 이유 1줄)
"""


async def summarize_news(title: str, content: str) -> str:
    """뉴스를 투자 로직 분석(3단계)으로 심층 분석하고 관련 종목을 추천한다."""
    prompt = f"""{_NEWS_ANALYSIS_PROMPT}

---
[입력 뉴스]
제목: {title}
내용: {content}
---

응답은 반드시 JSON만 출력 (다른 텍스트 없이):
{{
  "summary": "위 양식을 모두 채워 넣은 전체 텍스트 (마크다운 형식, 줄바꿈은 \\n)",
  "related_stocks": [
    {{"stock_code": "6자리종목코드", "stock_name": "종목명", "reason": "이 뉴스와 직접 연관된 이유 1줄", "type": "direct 또는 indirect"}}
  ],
  "impact_strength": "매우 높음 또는 높음 또는 보통 또는 낮음"
}}

[종목 작성 규칙]
- 종목코드와 종목명이 100% 확실한 경우에만 포함
- 불확실하면 related_stocks를 빈 배열([])로 반환
- 뉴스 본문에 언급된 기업 또는 명백한 직접 영향 기업만 포함
"""
    return await _call_with_retry(prompt)


async def translate_and_summarize_news(title: str, content: str) -> str:
    """영문 해외뉴스를 한국어로 번역 후, 투자 로직 분석으로 심층 분석한다."""
    prompt = f"""먼저 아래 영어 뉴스를 한국어로 자연스럽게 번역한 뒤, {_NEWS_ANALYSIS_PROMPT}

---
[입력 뉴스 - 영문]
제목: {title}
내용: {content}
---

번역된 한국어 기준으로 위 양식을 작성하세요.
관련 종목은 한국 거래소(KRX) 상장 종목 중 종목코드와 종목명이 확실한 경우에만 포함하세요.

응답은 반드시 JSON만 출력 (다른 텍스트 없이):
{{
  "summary": "위 양식을 모두 채워 넣은 전체 텍스트 (한국어, 마크다운 형식, 줄바꿈은 \\n)",
  "related_stocks": [
    {{"stock_code": "6자리종목코드", "stock_name": "종목명", "reason": "이 뉴스와 직접 연관된 이유 1줄", "type": "direct 또는 indirect"}}
  ],
  "impact_strength": "매우 높음 또는 높음 또는 보통 또는 낮음"
}}

[종목 작성 규칙]
- 종목코드와 종목명이 100% 확실한 경우에만 포함
- 불확실하면 related_stocks를 빈 배열([])로 반환
- 해외 뉴스라도 한국 상장 종목과 직접 연관이 없으면 빈 배열
"""
    return await _call_with_retry(prompt)


_POLICY_ANALYSIS_PROMPT = """# [주식콕] 정책 투자 분석 지침

당신은 한국 산업·경제 정책 전문 애널리스트입니다. 정책 내용에 있는 사실만 바탕으로 분석하세요.

## 핵심 원칙 (반드시 준수)
- **사실만 말하라**: 정책 본문에 없는 내용, 추측, 과장 금지
- **종목 코드 정확성**: 종목명과 6자리 코드가 100% 확실한 경우에만 beneficiary_stocks에 포함. 조금이라도 불확실하면 제외
- **관련 종목이 없으면**: beneficiary_stocks를 빈 배열([])로 반환. 억지로 채우지 마라
- **정책과 직접 연관된 기업만**: 정책 수혜/피해가 명백한 기업만 포함

## 분석 항목
1. **핵심 팩트**: 정책에서 가장 중요한 사실 3가지 (본문 기반)
2. **연관 분야**: 영향받는 산업군과 핵심 키워드
3. **파급력**: 실제 기업 매출·비용에 미치는 영향 (상/중/하), 단기/장기 구분
4. **수혜/피해 기업**: 정책과 직접 연관된 기업만 (없으면 없다고 함)
5. **투자자 주의사항**: 정책 시행 불확실성, 시행 시기, 예산 확보 여부 등 리스크

## 출력 양식 (analysis 필드에 넣을 텍스트)

📌 정책 핵심 팩트
(정책 본문 기반 중요 사실 3줄 — 추측 금지)

🔍 연관 분야 및 테마
산업군: (영향받는 실제 산업)
핵심 키워드: (정책에 실제 등장한 키워드)

⚡ 시장 파급력
강도: (상 / 중 / 하)
영향 범위: (단기/장기, 실제 매출·비용 영향 근거 포함)

💡 수혜/피해 기업
(확실한 기업만 — 없으면 "이 정책과 직접 연관된 상장 종목을 특정하기 어렵습니다"라고 작성)

⚠️ 투자자 주의사항
(정책 시행 불확실성, 예산 확보 여부, 시행 시기 등 체크포인트 1줄)
"""


async def analyze_policy(title: str, description: str) -> str:
    """정책을 투자 분석으로 심층 분석하고 수혜주/피해주를 추천한다."""
    prompt = f"""{_POLICY_ANALYSIS_PROMPT}

---
[입력 정책]
정책명: {title}
정책 내용: {description}
---

응답은 반드시 JSON만 출력 (다른 텍스트 없이):
{{
  "analysis": "위 양식을 모두 채워 넣은 전체 텍스트 (마크다운, 줄바꿈 \\n)",
  "beneficiary_stocks": [
    {{"stock_code": "6자리종목코드", "stock_name": "종목명", "reason": "이 정책과 직접 연관된 이유 1줄", "impact": "positive 또는 negative"}}
  ],
  "impact_strength": "상 또는 중 또는 하"
}}

[종목 작성 규칙]
- 종목코드와 종목명이 100% 확실한 경우에만 포함
- 불확실하면 beneficiary_stocks를 빈 배열([])로 반환
- 정책 본문에 언급된 기업 또는 명백한 직접 영향 기업만 포함
"""
    return await _call_with_retry(prompt)


def _format_structured_input(data: dict) -> str:
    """구조화된 분석 데이터를 AI에 넘길 문자열로 변환한다."""
    lines = []
    lines.append(f"종목명: {data.get('종목명', '')} | 종목코드: {data.get('종목코드', '')}")
    lines.append(f"현재가: {data.get('현재가', 0):,.0f}원 (등락률 {data.get('등락률', 0)}%)")
    lines.append("")

    def _v(k, default="데이터 없음", suffix=""):
        v = 재무.get(k, default)
        if v is None or v in ("N/A", "데이터 없음") or str(v).lower() == "none":
            return default
        return f"{v}{suffix}" if suffix else str(v)

    재무 = data.get("재무", {})
    lines.append("[재무 팩트]")
    lines.append(f"- 가성비 점수(PBR): {_v('가성비_점수_PBR')}")
    lines.append(f"- 장사 수완(ROE): {_v('장사_수완_ROE', suffix='%')}")
    lines.append(f"- 빚쟁이 지수(부채비율): {_v('빚쟁이_지수_부채비율')} (100% 이상이면 '허덕인다')")
    lines.append(f"- 매출성장률: {_v('매출성장률_퍼센트', suffix='%')}")
    lines.append(f"- 영업이익률: {_v('영업이익률_퍼센트', suffix='%')}")
    ocf = 재무.get("영업활동현금흐름")
    lines.append(f"- 영업활동현금흐름: {ocf if ocf not in (None, 'N/A', '데이터 없음') else '데이터 없음'} (마이너스면 '장부만 이익')")
    lines.append("")

    수급 = data.get("수급", {})
    lines.append("[수급 팩트]")
    lines.append(f"- 최근 10일 외국인/기관: {수급.get('최근10일_외국인_기관', 수급.get('최근5일_외국인_기관', '정보 없음'))}")
    sp = 수급.get("수급_시가총액비율_퍼센트")
    if sp is not None:
        lines.append(f"- 시가총액 대비 순매수 비율: {sp}% (0.1% 이상이면 '싹 쓸어담는 중')")
    lines.append("")

    차트 = data.get("차트", {})
    lines.append("[차트 팩트]")
    lines.append(f"- 추세: {차트.get('요약', '정보 없음')}")
    rsi = 차트.get("RSI_14")
    if rsi is not None:
        lines.append(f"- RSI(14): {rsi} (70 이상=화상 주의, 30 이하=동상 주의)")
    if 차트.get("최근_일봉"):
        lines.append("- 최근 10일 일봉:")
        for d in 차트["최근_일봉"][-10:]:
            lines.append(f"  {d['date']}: 시가{d['open']:,.0f} 고가{d['high']:,.0f} 저가{d['low']:,.0f} 종가{d['close']:,.0f}")
    lines.append("")

    뉴스 = data.get("뉴스_정책", [])
    if 뉴스:
        lines.append("[뉴스/정책]")
        for n in 뉴스[:10]:
            lines.append(f"- {n.get('제목', '')} ({n.get('출처', '')})")
    else:
        lines.append("[뉴스/정책] (제공된 데이터 없음)")

    return "\n".join(lines)


ANALYSIS_PROMPT_TEMPLATE = """
너는 주식 분석 전문가 '꼰대아저씨'다.
입력된 데이터를 항목별로 분석하여 JSON으로만 응답하라.

[데이터 분석 규칙]
- 부채비율 > 100% → '아직 빚에 허덕인다'
- RSI > 70 → '너무 뜨겁다! 화상 주의'
- RSI < 30 → '꽁꽁 얼었다! 동상 주의'
- 영업현금흐름 마이너스 → '장부만 이익이다'
- 외국인/기관 순매수(시가총액 대비 0.1%↑) → '외쿸인·큰형님 싹 쓸어담는 중'

[선택지] 각 항목의 result는 반드시 아래 선택지 중 하나를 골라라.
부채: 빚 없이 깔끔하다 / 아직 빚에 허덕인다 / 이자 낼 돈도 없다
현금흐름: 현금 왕! 부도 걱정 없다 / 통장이 텅텅 비었다 / 장부만 이익이다
수급: 외쿸인·큰형님 싹 쓸어담는 중 / 개미들만 신났다 / 다들 눈치 보는 중
차트: 정배열! 로켓 발사 준비 중 / 꼬여있다! 혼란의 도가니 / 역배열! 지옥 가는 열차
과열: 너무 뜨겁다! 화상 주의 / 딱 좋다! 탑승 가능 / 꽁꽁 얼었다! 동상 주의
가성비: 이 가격이면 헐값이다 / 제값이다 / 거품 꼈으니 조심해라
성장성: 매출이 쑥쑥 자란다 / 제자리걸음이다 / 매출이 줄고 있다
수익성: 장사를 잘한다 / 그냥 그렇다 / 적자라 힘들다
거래량: 거래량 폭발! 찐이다 / 거래량 실종! 가짜다 / 개미들만 바글바글
날씨: 순풍! 돈이 몰린다 / 역풍! 지금은 피할 때 / 무풍지대! 소외됐다

[출력 규칙]
- items 배열에 위 10개 항목을 모두 포함해야 한다.
- 각 항목의 reason은 실제 데이터 수치를 인용하여 1줄로 작성한다.
  예: "최근 분기 기준 부채비율이 125%입니다"
  (몇 분기인지 특정하지 말고 "최근 분기 기준"으로 표현하라)
- 데이터가 "데이터 없음"·"N/A"·"정보 없음"인 경우: reason에 "해당 데이터가 제공되지 않아 이번에는 보수적으로 판단했습니다"라고 쓰고, result는 중립적 선택지를 골라라. "None"·"None%" 등 그대로 적지 마라.
- 각 항목의 description은 투자자가 알아야 할 해석을 1줄로 작성한다.
  예: "동종업계 기업들보다 높은 비율이니 주의가 필요합니다"
- overall_score는 1~5 정수 (1=매우 부정, 5=매우 긍정)
- overall_comment는 종합 한줄평
"""


def _is_old_report_format(cached_data: dict) -> bool:
    """캐시된 분석이 구 형식(items 없음)인지 여부."""
    if not cached_data:
        return True
    report = cached_data.get("ai_report", "")
    if not report:
        return True
    try:
        parsed = json.loads(report) if isinstance(report, str) else report
        return "items" not in parsed
    except Exception:
        return True


async def analyze_stock(stock_name: str, stock_code: str, structured_data: dict) -> str:
    """[주식콕 심장] 종목 분석 - 항목별 카드 JSON 출력."""
    data_str = _format_structured_input(structured_data)

    prompt = f"""{ANALYSIS_PROMPT_TEMPLATE}
---
[제공된 데이터]
{data_str}
---

응답은 반드시 JSON만 출력 (다른 텍스트 없이):
{{
  "sentiment": "긍정 또는 부정 또는 중립",
  "items": [
    {{
      "label": "항목명 (예: 부채)",
      "result": "선택지 중 하나",
      "reason": "실제 수치를 인용한 1줄 근거",
      "description": "투자자를 위한 1줄 해석"
    }}
  ],
  "overall_score": 1~5 정수,
  "overall_comment": "종합 한줄평"
}}
"""
    config = types.GenerateContentConfig(temperature=0.3)
    return await _call_with_retry(prompt, config=config)


async def compare_stocks(stock_a: dict, stock_b: dict) -> str:
    """두 종목의 투자가치를 비교 분석한다."""
    a_str = _format_structured_input(stock_a)
    b_str = _format_structured_input(stock_b)

    prompt = f"""너는 주식 분석 전문가 '꼰대아저씨'다.
두 종목의 데이터를 보고, 어느 종목이 투자 가치가 더 높은지 비교 분석하라.

아래 10개 항목을 기준으로, 각 항목에서 어느 종목이 유리한지 판정하고,
최종적으로 어느 종목에 투자할지 명확히 추천하라.

[비교 항목]
부채 / 현금흐름 / 수급 / 차트 / 과열(RSI) / 가성비(PBR) / 성장성 / 수익성 / 거래량 / 날씨(시장)

[표현 규칙]
- 어려운 금융 용어 금지. 초등학생도 알아들을 수 있게 쉬운 말로 풀어라.
- 각 항목에서 어느 종목이 이기는지 명확하게 'A 종목 우세', 'B 종목 우세', '비슷함' 중 하나로 표현하라.
- reason은 실제 수치를 넣어 1줄로 작성하라.
- winner는 반드시 "A", "B", "같음" 중 하나여야 한다.

---
[A 종목 데이터]
{a_str}

---
[B 종목 데이터]
{b_str}

---

응답은 반드시 JSON만 출력 (다른 텍스트 없이):
{{
  "items": [
    {{
      "label": "항목명",
      "winner": "A 또는 B 또는 같음",
      "a_result": "A 종목 평가 한 줄",
      "b_result": "B 종목 평가 한 줄",
      "reason": "왜 이 종목이 유리한지 쉬운 말로 1줄"
    }}
  ],
  "overall_winner": "A 또는 B 또는 동점",
  "a_score": 1~5 정수,
  "b_score": 1~5 정수,
  "verdict": "최종 결론: 어느 종목을 사야 하는지 2~3문장으로 쉽게 설명",
  "caution": "투자 시 주의사항 1줄"
}}
"""
    config = types.GenerateContentConfig(temperature=0.3)
    return await _call_with_retry(prompt, config=config)


async def analyze_disclosure(rcp_no: str, report_nm: str, corp_name: str, content: str) -> str:
    """DART 공시 내용을 꼰대아저씨 스타일로 분석한다."""
    prompt = f"""너는 30년 경력의 주식 고수 '꼰대아저씨'야. DART 공시 서류의 딱딱한 내용을 분석해서 초보자도 알기 쉽게 설명해줘.

[핵심 원칙]
- 공시 본문에 있는 내용만 분석해. 없는 내용 지어내지 마라
- 수치(금액, 비율, 날짜)는 공시에 나온 그대로 정확하게 인용해
- 모르면 모른다고 해라. 추측으로 채우지 마라

[페르소나 규칙]
- 유상증자 → "남의 돈 빌리는 거니 주주 입장에선 희석이야, 조심해"
- 무상증자 → "공짜로 주식 더 주는 건데, 주가는 그만큼 낮아지니 착각하지 마"
- 실적 서프라이즈 → "허허, 이놈들 장사 잘했네"
- 적자/손실 → "임마, 이거 적자라고. 왜 샀어"
- 전문 용어는 쉬운 말로 풀어서 설명해
- "임마", "허허", "이걸 몰랐어?", "아이고" 같은 표현 자연스럽게 섞어
- 말투는 무뚝뚝하지만 따뜻하게

[입력 공시]
기업명: {corp_name}
공시명: {report_nm}
공시번호: {rcp_no}

[공시 본문 (일부)]
{content}

결과는 반드시 JSON만 출력 (다른 텍스트 없이):
{{
  "summary": "공시 본문 기반 핵심 내용 3줄 (번호 매기기, 꼰대 말투, 수치 인용, 줄바꿈은 \\n)",
  "sentiment": "호재 또는 악재 또는 중립",
  "insight": "이 공시가 주주에게 실제로 의미하는 것 (2~3문장, 꼰대 말투, 본문 근거 기반)",
  "caution": "투자자가 반드시 확인해야 할 사항 1줄 (공시 내용 기반, 없으면 빈 문자열)"
}}"""
    config = types.GenerateContentConfig(temperature=0.3)
    return await _call_with_retry(prompt, config=config)


async def analyze_journal_entry(entry: dict) -> str:
    """투자일지 항목에 대해 꼰대아저씨 스타일 피드백을 한두 문장으로 반환한다."""
    action_kr = "매수" if entry.get("action") == "buy" else "매도"
    total = float(entry.get("price", 0)) * float(entry.get("quantity", 0))
    prompt = f"""너는 30년 경력의 주식 고수 '꼰대아저씨'야.
투자자가 방금 주식 거래를 기록했어. 그 결정에 대해 한두 문장으로 짧고 임팩트 있는 피드백을 줘.

[거래 기록]
- 종목: {entry.get('stock_name', '')} ({entry.get('stock_code', '') or '코드 없음'})
- 거래 유형: {action_kr}
- 날짜: {entry.get('trade_date', '')}
- 가격: {float(entry.get('price', 0)):,.0f}원
- 수량: {entry.get('quantity', 0)}주
- 총금액: {total:,.0f}원
- 메모: {entry.get('memo', '') or '(없음)'}

[규칙]
- 반드시 한두 문장만 (3문장 이상 금지)
- "임마", "허허", "그래서", "아이고" 같은 꼰대 표현 자연스럽게 섞기
- 칭찬이든 비판이든 날카롭게
- JSON이나 마크다운 없이 순수 텍스트만 출력

피드백:"""
    config = types.GenerateContentConfig(temperature=0.7)
    return await _call_with_retry(prompt, config=config)


async def extract_stocks_from_keyword(keyword: str) -> list[dict]:
    """키워드로부터 관련 한국 상장 기업명을 Gemini 지식 베이스로 추출한다.

    코드는 요청하지 않음 — 이름만 받아서 호출부에서 실제 KRX DB로 검증한다.
    """
    prompt = f"""당신은 한국 주식시장 전문가입니다.
키워드 "{keyword}"와 관련된 한국거래소(KRX) 상장 기업의 이름을 알려주세요.

[핵심 원칙]
- 회사 이름(종목명)만 출력하세요. 종목코드는 출력하지 마세요
- 해당 키워드 사업을 실제로 영위하는 기업만 포함하세요
- 이름이 불확실하면 제외하세요. 억지로 채우지 마세요
- 없으면 빈 배열([])을 반환하세요

응답은 반드시 JSON 배열만 출력 (다른 텍스트 없이):
[
  {{"name": "정확한 한국어 종목명", "reason": "이 키워드와 직접 연관된 이유 한 문장"}},
  ...
]"""
    try:
        raw = await _call_with_retry(prompt)
        match = re.search(r'\[.*\]', raw, re.DOTALL)
        if not match:
            return []
        return json.loads(match.group())
    except Exception as e:
        logger.warning("extract_stocks_from_keyword 실패 (%s): %s", keyword, e)
        return []
