import asyncio
import json
import logging
import re

from google import genai
from google.genai import types
from app.config import get_settings

logger = logging.getLogger(__name__)

_client_instance = None
_MODEL_NAME = "gemini-2.5-flash"


def _get_client() -> genai.Client:
    global _client_instance
    if _client_instance is not None:
        return _client_instance
    settings = get_settings()
    api_key = (settings.gemini_api_key or "").strip()
    if not api_key:
        raise ValueError(
            "Gemini API 키가 설정되지 않았습니다. backend/.env에 GEMINI_API_KEY를 넣어 주세요."
        )
    _client_instance = genai.Client(api_key=api_key)
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


_NEWS_ANALYSIS_PROMPT = """# [주식콕] 뉴스 투자 로직 분석 지침

당신은 '주식투자 박사' 자료를 학습한 전문가입니다. 단순 요약이 아닌 **투자자가 즉각 판단할 수 있는 분석 보고서**를 작성하세요.

## 1. 분석의 3단계 로직 (반드시 거칠 것)
- **핵심 요약**: 뉴스 본문에서 가장 중요한 팩트 3가지를 추출
- **분야 및 테마 매칭**: 이 뉴스가 어느 산업(반도체, 2차전지 등)과 어떤 테마에 속하는지 명시
- **파급력 및 투자 판단**: 시장에 미칠 영향력(강도)과 구체적인 수혜 종목 연결

## 2. 단순 요약 금지
- 뉴스 내용을 줄이는 '요약' 수준을 넘어, '이 뉴스 보고 뭐 사야 해?'에 답할 수 있는 형태로 작성

## 3. 연관 관계 명시
- 해당 뉴스가 어느 [산업 분야]와 연관되는지 반드시 명시
- 파급력을 (매우 높음/높음/보통/낮음)으로 평가

## 4. 종목 연결 (Stock Tagging)
- **최소 5개 이상의 관련 종목**을 추천하세요. (대형주뿐만 아니라 실질적 수혜를 입는 **중소형주/코스닥 종목**도 반드시 포함)
- 직접 수혜주, 낙수 효과주, 테마 연관주를 다양하게 발굴
- 한국 거래소(KRX) 상장 종목 코드와 명칭 정확히 기재

## 5. 톤앤매너
- 전문가 어조를 유지하되, 초보자도 이해 가능하게
- "호황이다", "돈이 몰린다" 같은 직관적 표현 사용

## 6. 출력 양식 (절대 준수)
아래 양식을 그대로 따라 작성한 전체 텍스트를 summary에 넣으세요.

📌 한눈에 보는 핵심 팩트
(뉴스에서 가장 중요한 사실 3줄 요약)

🔍 연관 분야 및 테마
산업군: (예: 반도체 / 2차전지 / 에너지)
핵심 키워드: (예: HBM3E, 보조금 확정, 금리 인하)

⚡ 시장 파급력 (AI 판단)
강도: (매우 높음 / 높음 / 보통 / 낮음)
영향 범위: (단기 주가 반등용인지, 1년 이상 장기 호재인지 분석)

💡 그래서 어떤 종목? (투자 인사이트 - 5개 이상 추천)
직접 수혜주: (종목명 - 이유)
낙수 효과주: (종목명 - 이유)
중소형 히든카드: (종목명 - 이유)
AI의 한마디: "(투자자에게 전달할 핵심 조언 한 문장)"
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
    {{"stock_code": "종목코드", "stock_name": "종목명", "reason": "한 줄 관련 이유 (직접수혜/낙수효과 구분 가능)", "type": "direct 또는 indirect"}},
    ...
  ],
  "impact_strength": "매우 높음 또는 높음 또는 보통 또는 낮음"
}}
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

번역된 한국어 기준으로 위 양식을 작성하세요. 관련 종목은 한국 거래소(KRX) 상장 종목 위주로 추천하세요.

응답은 반드시 JSON만 출력 (다른 텍스트 없이):
{{
  "summary": "위 양식을 모두 채워 넣은 전체 텍스트 (한국어, 마크다운 형식, 줄바꿈은 \\n)",
  "related_stocks": [
    {{"stock_code": "종목코드", "stock_name": "종목명", "reason": "한 줄 관련 이유", "type": "direct 또는 indirect"}},
    ...
  ],
  "impact_strength": "매우 높음 또는 높음 또는 보통 또는 낮음"
}}
"""
    return await _call_with_retry(prompt)


_POLICY_ANALYSIS_PROMPT = """# [주식콕] 정책 투자 로직 분석 지침

당신은 '주식투자 박사' 자료를 학습한 전문가입니다. 정부 정책(korea.kr)을 **투자자가 즉각 판단할 수 있는 분석 보고서**로 작성하세요.

## 1. 분석의 3단계 로직 (반드시 거칠 것)
- **핵심 요약**: 정책에서 가장 중요한 팩트 3가지 추출
- **분야 및 테마 매칭**: 이 정책이 어느 산업/테마에 영향을 주는지 명시
- **파급력 및 투자 판단**: 실제 기업 매출·비용 절감에 기여할 정도를 (상/중/하)로 평가, 수혜/피해 종목 연결

## 2. 단순 요약 금지
- 정책 내용을 줄이는 게 아니라, '이 정책 때문에 뭐 사야 해?'에 답할 수 있게 작성

## 3. 파급력 평가
- 정책이 실제 기업 매출·비용 절감에 얼마나 기여할지 (상/중/하)로 평가

## 4. 종목 연결
- **최소 5개 이상의 관련 종목**을 추천 (대형주 위주 탈피, **중소형 실적 개선주** 적극 발굴)
- 수혜/피해 구분 (impact: positive/negative)
- 한국 거래소(KRX) 상장 종목 코드 확인

## 5. 톤앤매너
- 전문가 어조 + "호황이다", "돈이 몰린다" 같은 직관적 표현

## 6. 출력 양식 (절대 준수)
아래 양식을 그대로 따라 작성한 전체 텍스트를 analysis에 넣으세요.

📌 한눈에 보는 핵심 팩트
(정책에서 가장 중요한 사실 3줄 요약)

🔍 연관 분야 및 테마
산업군: (예: 반도체 / 2차전지 / 에너지)
핵심 키워드: (예: 세액공제, R&D 지원, 규제 완화)

⚡ 시장 파급력 (AI 판단)
강도: (상 / 중 / 하)
영향 범위: (단기/장기, 실제 매출·비용에 미치는 구체적 영향)

💡 투자 인사이트
💡 투자 인사이트 (5개 이상 추천)
직접 수혜주: (종목명 - 이유)
낙수 효과주: (종목명 - 이유)
중소형 수혜주: (종목명 - 이유)
AI의 한마디: "(투자자에게 전달할 핵심 조언 한 문장)"
"""


async def analyze_policy(title: str, description: str) -> str:
    """정책을 투자 로직 분석(3단계)으로 심층 분석하고 수혜주/피해주를 추천한다."""
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
    {{"stock_code": "종목코드", "stock_name": "종목명", "reason": "수혜/피해 이유 한 줄", "impact": "positive 또는 negative"}},
    ...
  ],
  "impact_strength": "상 또는 중 또는 하"
}}
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
    lines.append(f"- 최근 5일 외국인/기관: {수급.get('최근5일_외국인_기관', '정보 없음')}")
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

[페르소나 규칙]
- 유상증자면 "돈 빌리는 거니 조심해라", 실적 대박이면 "허허, 이놈들 장사 잘했네" 식으로 반응해
- 전문 용어는 최대한 쉬운 말로 풀어서 설명해
- "임마", "허허", "이걸 몰랐어?", "아이고" 같은 표현 자연스럽게 섞어
- 3줄 핵심 요약은 반드시 번호 매겨서 (1. 2. 3.) 작성
- 말투는 무뚝뚝하지만 따뜻하게. 초보 투자자를 아끼는 마음으로

[입력 공시]
기업명: {corp_name}
공시명: {report_nm}
공시번호: {rcp_no}

[공시 본문 (일부)]
{content}

결과는 반드시 JSON만 출력 (다른 텍스트 없이):
{{
  "summary": "핵심 내용 3줄 요약 (번호 매기기, 꼰대 말투로, 줄바꿈은 \\n)",
  "sentiment": "호재 또는 악재 또는 중립",
  "insight": "투자자에게 꼰대아저씨가 전하는 핵심 조언 (2~3문장, 꼰대 말투)",
  "caution": "주의사항 1줄 (없으면 빈 문자열)"
}}"""
    config = types.GenerateContentConfig(temperature=0.4)
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
    """키워드로부터 관련 한국 상장 종목 10개를 Gemini 지식 베이스로 추출한다."""
    prompt = f"""당신은 한국 주식시장 전문가입니다.
키워드 "{keyword}"와 관련된 한국거래소(KRX) 상장 종목을 최대 10개 추출해주세요.

조건:
1. 반드시 실제 KOSPI 또는 KOSDAQ 상장 종목이어야 합니다
2. 종목코드는 6자리 숫자여야 합니다
3. 각 종목을 추천하는 이유를 한 문장으로 설명해야 합니다
4. 대형주뿐만 아니라, 실질적 수혜를 입는 중소형주(Small/Mid Cap)도 반드시 포함하세요.
5. 직접 관련 기업을 우선 추출하고, 낙수 효과가 기대되는 기업도 포함하세요.

응답은 반드시 JSON 배열만 출력 (다른 텍스트 없이):
[
  {{"code": "종목코드", "name": "종목명", "reason": "추천 이유 한 문장"}},
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
