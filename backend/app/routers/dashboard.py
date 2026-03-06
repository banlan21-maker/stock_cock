import asyncio
import json
import logging
import re
from datetime import datetime, timedelta

from fastapi import APIRouter, Query
from app.services import news_service, policy_service, stock_service
from app.services import gemini_service
from app.services.generic_cache_service import get_generic_cache, set_generic_cache

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 테마 트렌드 TTL (Supabase generic_kv_cache 에 저장)
#   daily  → 1시간 TTL (자주 보지만 1시간이면 충분)
#   weekly → 24시간 TTL (주간 데이터는 하루 한 번이면 충분)
# ---------------------------------------------------------------------------
_CACHE_TTL_DAILY  = 60 * 60        # 1시간 (초)
_CACHE_TTL_WEEKLY = 24 * 60 * 60   # 24시간 (초)
_CACHE_TTL_DASHBOARD = 5 * 60     # 대시보드 5분 (초)


# ---------------------------------------------------------------------------
# pykrx 래퍼 — 최근 거래일 자동 탐색 (주말·공휴일 대응)
# ---------------------------------------------------------------------------
def _col_or_fallback(df_columns, *names: str):
    """DataFrame 컬럼에서 names 중 존재하는 첫 컬럼 반환."""
    cols = list(df_columns)
    for n in names:
        for c in cols:
            if n in str(c):
                return c
    return None


def _get_ohlcv_df(pykrx_stock, date_str: str, market: str):
    """pykrx로 특정일·시장의 전종목 OHLCV DataFrame 반환. API 호환성 대응."""
    # pykrx 버전별 API: get_market_ohlcv_by_ticker | get_market_ohlcv
    for fn_name in ("get_market_ohlcv_by_ticker", "get_market_ohlcv"):
        fn = getattr(pykrx_stock, fn_name, None)
        if fn is None:
            continue
        try:
            if fn_name == "get_market_ohlcv_by_ticker":
                df = fn(date_str, market=market)
            else:
                # get_market_ohlcv(date, market=) — 전종목 시세
                df = fn(date_str, market=market)
            if df is not None and not df.empty:
                return df
        except Exception as e:
            logger.debug("pykrx %s(%s, %s) 실패: %s", fn_name, date_str, market, e)
            continue
    return None


def _fetch_top_stocks_fdr_fallback(limit: int = 50) -> list[dict]:
    """pykrx 실패 시 FinanceDataReader로 주요 종목 등락률 조회 (폴백)."""
    try:
        import FinanceDataReader as fdr

        end = datetime.now()
        start = end - timedelta(days=7)
        start_str = start.strftime("%Y-%m-%d")
        end_str = end.strftime("%Y-%m-%d")

        code_to_name = {str(s["code"]).zfill(6): s["name"] for s in stock_service.get_stock_list()}

        sample_codes = [
            "005930", "000660", "035420", "051910", "006400", "035720", "000270",
            "068270", "207940", "003670", "005380", "012330", "066570", "051900",
            "028260", "009150", "032830", "017670", "086790", "105560", "003550",
            "018880", "000810", "096770", "034730", "033780", "316140", "247540",
        ]
        results = []
        for code in sample_codes:
            try:
                df = fdr.DataReader(code, start_str, end_str)
                if df is None or df.empty or len(df) < 2:
                    continue
                last = df.iloc[-1]
                prev = df.iloc[-2]
                close_curr = float(last.get("Close", last.get("종가", 0)))
                close_prev = float(prev.get("Close", prev.get("종가", 0)))
                if close_prev <= 0:
                    continue
                change_rate = round((close_curr - close_prev) / close_prev * 100, 2)
                vol_cnt = int(last.get("Volume", last.get("거래량", 0)) or 0)
                volume = vol_cnt * int(close_curr)
                name = code_to_name.get(code, code)
                results.append({"code": code, "change_rate": change_rate, "volume": volume, "name": name})
            except Exception:
                continue

        results.sort(key=lambda x: x["change_rate"], reverse=True)
        return results[:limit]
    except Exception as e:
        logger.warning("FDR 폴백도 실패: %s", e)
        return []


def _find_latest_trading_date(pykrx_stock) -> tuple[str, str] | None:
    """오늘부터 최대 7일 전까지 역순으로 실제 거래 데이터가 있는 날짜를 찾는다.

    Returns:
        (날짜문자열 "YYYYMMDD", 표시용 "YYYY-MM-DD") 또는 None
    """
    for days_back in range(0, 8):
        candidate = (datetime.now() - timedelta(days=days_back)).strftime("%Y%m%d")
        df = _get_ohlcv_df(pykrx_stock, candidate, "KOSPI")
        if df is not None and not df.empty:
            display = f"{candidate[:4]}-{candidate[4:6]}-{candidate[6:]}"
            logger.info("최근 거래일 탐색 완료: %s", candidate)
            return candidate, display
    return None


def _find_prev_trading_date(pykrx_stock, after_date_yyyymmdd: str) -> str | None:
    """after_date_yyyymmdd 이전의 가장 최근 거래일을 반환. 없으면 None."""
    after_dt = datetime.strptime(after_date_yyyymmdd, "%Y%m%d")
    for d in range(1, 10):
        candidate = (after_dt - timedelta(days=d)).strftime("%Y%m%d")
        df = _get_ohlcv_df(pykrx_stock, candidate, "KOSPI")
        if df is not None and not df.empty:
            return candidate
    return None


def _safe_float(v, default: float = 0.0) -> float:
    """numpy/판다스 스칼라를 float으로 안전 변환."""
    if v is None:
        return default
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _safe_int(v, default: int = 0) -> int:
    """numpy/판다스 스칼라를 int로 안전 변환."""
    if v is None:
        return default
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


def _fetch_daily_top_stocks(limit: int | None = 50, sort_key: str = "change_rate") -> tuple[list[dict], str]:
    """pykrx로 KOSPI+KOSDAQ 상위 종목을 가져온다. (등락률 or 거래대금)

    등락률 컬럼이 없으면 전일 종가 대비로 직접 계산한다.
    limit=None 이면 전체 반환(정렬만 적용, 이름 미보완). theme-trend 단일 fetch용.
    Returns:
        (종목 리스트, 기준날짜 표시문자열)
    """
    try:
        from pykrx import stock as pykrx_stock

        trading_date_info = _find_latest_trading_date(pykrx_stock)
        if not trading_date_info:
            logger.warning("최근 7일 내 거래 데이터 없음 → FDR 폴백")
            return _fetch_top_stocks_fdr_fallback(limit or 50), ""
        trade_date, display_date = trading_date_info

        # 전일 종가 맵 (등락률 컬럼 없을 때 사용)
        prev_close: dict[str, float] = {}
        change_col_available = False
        close_col_global = None

        for market in ("KOSPI", "KOSDAQ"):
            df = _get_ohlcv_df(pykrx_stock, trade_date, market)
            if df is not None and not df.empty:
                if _col_or_fallback(df.columns, "등락률", "등락", "Change"):
                    change_col_available = True
                close_col_global = _col_or_fallback(df.columns, "종가", "Close")
                break

        if not change_col_available and close_col_global:
            prev_date = _find_prev_trading_date(pykrx_stock, trade_date)
            if prev_date:
                for market in ("KOSPI", "KOSDAQ"):
                    df_prev = _get_ohlcv_df(pykrx_stock, prev_date, market)
                    if df_prev is not None and not df_prev.empty:
                        close_col = _col_or_fallback(df_prev.columns, "종가", "Close")
                        if not close_col:
                            continue
                        for ticker, row in df_prev.iterrows():
                            code = str(ticker).zfill(6)
                            prev_close[code] = _safe_float(row.get(close_col))

        results = []
        for market in ("KOSPI", "KOSDAQ"):
            df = _get_ohlcv_df(pykrx_stock, trade_date, market)
            if df is None or df.empty:
                continue
            change_col = _col_or_fallback(df.columns, "등락률", "등락", "Change")
            close_col = _col_or_fallback(df.columns, "종가", "Close")
            vol_col = _col_or_fallback(df.columns, "거래대금", "Amount", "거래량")
            for ticker, row in df.iterrows():
                code = str(ticker).zfill(6)
                close = _safe_float(row.get(close_col))
                vol_raw = row.get(vol_col, 0)
                # 거래대금 컬럼이 있으면 그대로, 거래량만 있으면 거래량*종가로 거래대금 추정
                if vol_col and ("거래대금" in str(vol_col) or "Amount" in str(vol_col)):
                    volume = _safe_int(vol_raw)
                else:
                    volume = _safe_int(vol_raw) * int(close) if close else 0
                if change_col:
                    cr = _safe_float(row.get(change_col))
                else:
                    pclose = prev_close.get(code)
                    if pclose and pclose > 0:
                        cr = round((close - pclose) / pclose * 100, 2)
                    else:
                        cr = 0.0
                results.append({
                    "code": code,
                    "change_rate": cr,
                    "volume": volume,
                })

        if not results:
            logger.warning("pykrx 데이터 비어있음 → FDR 폴백")
            return _fetch_top_stocks_fdr_fallback(limit or 50), display_date

        if sort_key == "volume":
            results.sort(key=lambda x: x["volume"], reverse=True)
        else:
            results.sort(key=lambda x: x["change_rate"], reverse=True)

        top = results if limit is None else results[:limit]

        if limit is not None:
            for item in top:
                try:
                    name = pykrx_stock.get_market_ticker_name(item["code"])
                    item["name"] = name or item["code"]
                except Exception:
                    item["name"] = item["code"]

        return top, display_date

    except ImportError:
        logger.error("pykrx가 설치되지 않았습니다. pip install pykrx")
        return _fetch_top_stocks_fdr_fallback(limit or 50), ""
    except Exception as e:
        logger.error("_fetch_daily_top_stocks 오류: %s", e)
        return _fetch_top_stocks_fdr_fallback(limit or 50), ""


def _fetch_weekly_top_stocks(limit: int | None = 50, sort_key: str = "change_rate") -> tuple[list[dict], str]:
    """최근 5거래일(주간) 기준 상위 종목을 가져온다.

    limit=None 이면 전체 반환(정렬만 적용, 이름 미보완). theme-trend 단일 fetch용.
    Returns:
        (종목 리스트, "YYYY-MM-DD ~ YYYY-MM-DD" 형식 기간 표시문자열)
    """
    try:
        from pykrx import stock as pykrx_stock

        end_info = _find_latest_trading_date(pykrx_stock)
        if not end_info:
            logger.warning("주간: 최근 거래일 탐색 실패 → FDR 폴백")
            return _fetch_top_stocks_fdr_fallback(limit or 50), ""
        end_date, end_display = end_info

        end_dt = datetime.strptime(end_date, "%Y%m%d")
        start_date, start_display = None, ""
        for days_back in range(7, 11):  # 최대 4번 시도 (기존 9번 → 속도 개선)
            candidate = (end_dt - timedelta(days=days_back)).strftime("%Y%m%d")
            df = _get_ohlcv_df(pykrx_stock, candidate, "KOSPI")
            if df is not None and not df.empty:
                start_date = candidate
                start_display = f"{candidate[:4]}-{candidate[4:6]}-{candidate[6:]}"
                break

        if not start_date:
            logger.warning("주간 시작 거래일 탐색 실패 — 일간 데이터로 대체")
            return _fetch_daily_top_stocks(limit, sort_key)

        start_close: dict[str, float] = {}
        end_close: dict[str, float] = {}
        weekly_volume: dict[str, int] = {}

        for market in ("KOSPI", "KOSDAQ"):
            df_s = _get_ohlcv_df(pykrx_stock, start_date, market)
            if df_s is not None and not df_s.empty:
                close_col = _col_or_fallback(df_s.columns, "종가", "Close", "close")
                if close_col:
                    for ticker, row in df_s.iterrows():
                        v = _safe_float(row.get(close_col))
                        if v > 0:
                            start_close[str(ticker).zfill(6)] = v

            df_e = _get_ohlcv_df(pykrx_stock, end_date, market)
            if df_e is not None and not df_e.empty:
                close_col = _col_or_fallback(df_e.columns, "종가", "Close", "close")
                vol_col = _col_or_fallback(df_e.columns, "거래대금", "Amount", "거래량")
                if close_col:
                    for ticker, row in df_e.iterrows():
                        code = str(ticker).zfill(6)
                        v = _safe_float(row.get(close_col))
                        vol_raw = row.get(vol_col, 0)
                        if vol_col and ("거래대금" in str(vol_col) or "Amount" in str(vol_col)):
                            vol = _safe_int(vol_raw)
                        else:
                            vol = _safe_int(vol_raw) * int(v) if v else 0
                        if v > 0:
                            end_close[code] = v
                            weekly_volume[code] = vol

        # start_close가 비어 있으면 주간 등락률 계산 불가 → 일간으로 대체
        if not start_close and end_close:
            logger.warning("주간 start_close 비어있음 — 일간 데이터로 대체")
            return _fetch_daily_top_stocks(limit, sort_key)

        results = []
        for code, e_close in end_close.items():
            s_close = start_close.get(code, 0)
            if s_close > 0:
                weekly_change = round((e_close - s_close) / s_close * 100, 2)
            else:
                weekly_change = 0.0
            results.append({
                "code": code,
                "change_rate": weekly_change,
                "volume": weekly_volume.get(code, 0),
            })

        if sort_key == "volume":
            results.sort(key=lambda x: x["volume"], reverse=True)
        else:
            results.sort(key=lambda x: x["change_rate"], reverse=True)

        top = results if limit is None else results[:limit]

        if limit is not None:
            for item in top:
                try:
                    name = pykrx_stock.get_market_ticker_name(item["code"])
                    item["name"] = name or item["code"]
                except Exception:
                    item["name"] = item["code"]

        display = f"{start_display} ~ {end_display}"
        return top, display

    except ImportError:
        logger.error("pykrx가 설치되지 않았습니다.")
        return _fetch_top_stocks_fdr_fallback(limit or 50), ""
    except Exception as e:
        logger.error("_fetch_weekly_top_stocks 오류: %s", e)
        return _fetch_top_stocks_fdr_fallback(limit or 50), ""


def _fallback_theme_from_name(name: str) -> str:
    """Gemini 실패 시 종목명 키워드로 테마를 추정한다. 한 그룹만 나오지 않도록 여러 테마로 나눈다."""
    if not name or not isinstance(name, str):
        return "기타"
    n = name.strip()
    # 키워드 매칭 (순서 유지, 먼저 매칭된 테마 사용)
    rules = [
        (["삼성전자", "SK하이닉스", "하이닉스", "메모리", "HBM", "반도체"], "반도체/메모리"),
        (["에코프로", "포스코퓨처엠", "엘앤에프", "양극재", "음극재", "배터리", "에너지솔루션"], "배터리/소재"),
        (["LG에너지", "삼성SDI", "SDI", "전지", "이차전지"], "전기차 배터리"),
        (["현대차", "기아", "현대모비스", "만도", "한온시스템", "자동차", "부품"], "자동차/부품"),
        (["NAVER", "네이버", "카카오", "크래프톤", "엔씨", "넥슨", "게임", "메타버스"], "IT/플랫폼·게임"),
        (["KB금융", "신한", "하나", "우리", "NH", "증권", "보험", "은행"], "금융"),
        (["삼성바이오", "셀트리온", "유한양행", "한미약품", "제넥신", "바이오", "제약", "의료"], "바이오/제약"),
        (["한화", "LIG넥스원", "LIG", "두산", "한화에어로", "방산", "항공", "우주"], "방산/항공우주"),
        (["삼성전기", "삼성엔지니어링", "에스엔에스", "반도체 장비", "에이피티씨"], "반도체 장비/소재"),
        (["LG전자", "LG디스플레이", "삼성디스플레이", "디스플레이", "OLED", "LCD"], "디스플레이"),
        (["포스코", "현대제철", "철강", "세아", "고려아연"], "철강/소재"),
        (["삼성물산", "현대건설", "GS건설", "대방", "건설"], "건설"),
        (["SK이노베이션", "S-Oil", "GS칼텍스", "정유", "석유", "화학"], "에너지/화학"),
        (["카카오페이", "토스", "핀테크", "페이"], "핀테크"),
        (["CJ", "롯데", "신세계", "이마트", "유통", "식품", "음료"], "유통/음식료"),
        (["LG화학", "롯데케미칼", "한화솔루션", "코스맥스", "화장품"], "화학/뷰티"),
        (["KT", "SK텔레콤", "LG유플러스", "통신"], "통신"),
        (["한국전력", "전력", "전기", "가스"], "전력/가스"),
        (["현대중공업", "삼성중공업", "대우조선", "조선", "해운"], "조선/해운"),
    ]
    for keywords, theme in rules:
        for kw in keywords:
            if kw in n:
                return theme
    return "기타"


async def _classify_themes(stocks: list[dict]) -> list[dict]:
    """Gemini 배치 콜로 종목 → 테마 분류 후 그룹핑된 ThemeGroup[] 반환."""
    if not stocks:
        return []

    # Gemini 프롬프트용 입력 (code, name, change_rate만)
    stock_input = [
        {"code": s["code"], "name": s["name"], "change_rate": s["change_rate"]}
        for s in stocks
    ]
    prompt = f"""아래 한국 주식 종목들을 투자 테마별로 **최대한 세부적인 Sub-theme**으로 분류해줘.

[분류 규칙]
1. 결과 테마 수는 반드시 최소 20개, 최대 30개 사이가 되도록 해줘.
2. 큰 카테고리(예: '반도체', 'AI')로 뭉뚱그리지 말고, 아래 예시처럼 세부 테마로 나눠줘.
3. 각 종목은 반드시 하나의 테마에만 배정해.

[세부 테마 예시 (이처럼 구체적으로 나눠야 함)]
- AI 서버/데이터센터, HBM/고대역폭메모리, 시스템반도체, 반도체 장비/소재, 반도체 후공정
- 전기차 배터리, ESS/에너지저장장치, 배터리 소재(양극재/음극재), 배터리 장비/검사
- 항공우주/위성, K-방산/무기체계, 드론/UAM
- 바이오시밀러/위탁생산, 신약개발/항암제, 의료기기/디지털헬스
- 태양광/풍력, 수소에너지, 원전/SMR
- 전기차/자율주행, 자동차 부품/경량화, 조선/해운, 철강/소재
- 금융/증권, 보험, 핀테크/인터넷은행
- 게임/메타버스, 엔터/K팝, OTT/미디어
- 건설/건자재, 리츠/부동산, 음식료/유통, 화장품/뷰티
- 디스플레이(OLED), 스마트폰 부품, 통신/네트워크, 로봇/자동화

종목 목록:
{json.dumps(stock_input, ensure_ascii=False)}

응답은 반드시 JSON 객체만 출력 (다른 텍스트 없이):
{{"종목코드": "테마명", ...}}
예: {{"005930": "HBM/고대역폭메모리", "000660": "AI 서버/데이터센터"}}"""

    try:
        raw = await gemini_service._call_with_retry(prompt)
        # JSON 추출
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if not match:
            raise ValueError("JSON 파싱 실패")
        parsed: dict = json.loads(match.group())
        # 키를 6자리 종목코드로 통일 (문자열/숫자 혼용 대응)
        theme_map = {}
        for k, v in parsed.items():
            code = str(k).strip()
            if not code.isdigit():
                continue
            code = code.zfill(6)
            theme_name = (v or "기타").strip() if isinstance(v, str) else "기타"
            theme_map[code] = theme_name
    except Exception as e:
        logger.warning("Gemini 테마 분류 실패, 이름 기반 폴백 사용: %s", e)
        # 폴백: 종목명 키워드로 여러 테마 그룹 생성 (전체 "기타" 하나만 나오지 않도록)
        theme_map = {
            str(s["code"]).strip().zfill(6): _fallback_theme_from_name(s.get("name") or s.get("code", ""))
            for s in stocks
        }

    # 종목 코드 → 원본 데이터 맵 (키는 6자리 문자열로 통일)
    stock_by_code = {str(s["code"]).strip().zfill(6): s for s in stocks}
    # Gemini가 일부 종목만 반환한 경우 나머지는 이름 기반 폴백으로 채움
    for code, s in stock_by_code.items():
        if code not in theme_map:
            theme_map[code] = _fallback_theme_from_name(s.get("name") or s.get("code", ""))

    # 테마별 그룹핑
    groups: dict[str, dict] = {}
    for code, theme in theme_map.items():
        s = stock_by_code.get(code)
        if not s:
            continue
        if theme not in groups:
            groups[theme] = {"theme": theme, "total_change": 0.0, "count": 0, "total_volume": 0, "stocks": []}
        g = groups[theme]
        g["total_change"] += s["change_rate"]
        g["count"] += 1
        g["total_volume"] += s["volume"]
        g["stocks"].append({
            "code": s["code"],
            "name": s["name"],
            "change_rate": s["change_rate"],
            "volume": s["volume"],
        })

    result = []
    for theme, g in groups.items():
        avg = round(g["total_change"] / g["count"], 2) if g["count"] else 0.0
        result.append({
            "theme": theme,
            "avg_change_rate": avg,
            "total_volume": g["total_volume"],
            "stocks": g["stocks"],
        })

    # 등락률 기준 내림차순 정렬
    result.sort(key=lambda x: x["avg_change_rate"], reverse=True)
    return result


# ---------------------------------------------------------------------------
# 엔드포인트
# ---------------------------------------------------------------------------

@router.get("/theme-trend")
async def get_theme_trend(
    sort: str = Query("change_rate", description="change_rate | volume"),
    period: str = Query("daily", description="daily | weekly"),
):
    """KOSPI+KOSDAQ 상위 종목을 테마별로 분류하여 treemap 데이터로 반환한다.

    - period=daily  : 최근 거래일 등락률 기준 (30분 캐시)
    - period=weekly : 최근 5거래일 기준 누적 등락률 (4시간 캐시)
    주말·공휴일에도 최근 거래일 데이터를 자동 탐색한다.
    """
    is_weekly = (period == "weekly")
    cache_key = f"theme_trend_{period}_{sort}"
    ttl = _CACHE_TTL_WEEKLY if is_weekly else _CACHE_TTL_DAILY

    # Supabase 영속 캐시 확인
    cached = get_generic_cache(cache_key)
    if cached:
        return cached

    fetch_fn = _fetch_weekly_top_stocks if is_weekly else _fetch_daily_top_stocks
    all_stocks, trade_date = await asyncio.to_thread(fetch_fn, None, "change_rate")
    if not all_stocks:
        return {"groups": [], "trade_date": trade_date or "", "period": period}
    # 주간 기준인데 등락률이 전부 0이면 데이터 오류 → 일간으로 재요청
    if is_weekly and all(s.get("change_rate", 0) == 0 for s in all_stocks):
        logger.warning("주간 데이터 등락률 전부 0 — 일간으로 대체")
        all_stocks, trade_date = await asyncio.to_thread(_fetch_daily_top_stocks, None, "change_rate")
        if not all_stocks:
            return {"groups": [], "trade_date": trade_date or "", "period": period}

    by_cr = sorted(all_stocks, key=lambda x: x["change_rate"], reverse=True)[:150]
    by_vol = sorted(all_stocks, key=lambda x: x["volume"], reverse=True)[:150]
    seen: dict[str, dict] = {}
    for s in by_cr + by_vol:
        code = str(s.get("code", "")).strip().zfill(6)
        if not code.isdigit() or len(code) != 6:
            continue
        if code not in seen:
            s["code"] = code
            seen[code] = s
    stocks = list(seen.values())

    if sort == "volume":
        stocks.sort(key=lambda x: x["volume"], reverse=True)
    else:
        stocks.sort(key=lambda x: x["change_rate"], reverse=True)

    # 종목명 보완: stock_list 캐시를 dict로 변환해 O(1) 조회 (개별 pykrx API 호출 제거)
    stock_name_map = {s["code"]: s["name"] for s in stock_service.get_stock_list()}
    for item in stocks:
        if "name" not in item or not item.get("name") or item.get("name") == item.get("code"):
            item["name"] = stock_name_map.get(item["code"], item.get("name", item["code"]))

    theme_groups = await _classify_themes(stocks)

    # 모바일 가독성: 상위 20개 테마만 노출 (정렬 기준에 따라 선택)
    if sort == "volume":
        theme_groups.sort(key=lambda x: x["total_volume"], reverse=True)
    else:
        theme_groups.sort(key=lambda x: x["avg_change_rate"], reverse=True)
    theme_groups = theme_groups[:20]

    response = {"groups": theme_groups, "trade_date": trade_date, "period": period}
    set_generic_cache(cache_key, response, ttl)
    return response


@router.get("/keyword-feed")
async def get_keyword_feed(keywords: str = Query(..., description="쉼표 구분 키워드 (예: AI,반도체)")):
    """커스텀 키워드로 관련 종목/뉴스/정책을 반환한다.

    종목 추출: Gemini 지식 베이스 → FinanceDataReader 상장 여부 + 현재가 검증
    """
    kw_list = [k.strip() for k in keywords.split(",") if k.strip()]
    if not kw_list:
        return {"stocks": [], "news": [], "policies": []}

    kw_str = " ".join(kw_list)

    # ── 1. Gemini 지식 베이스로 관련 상장사 추출 (키워드 통합) ──
    raw_stocks = await gemini_service.extract_stocks_from_keyword(kw_str)

    # ── 2. FinanceDataReader로 실제 상장 여부 + 현재가 검증 ──
    async def verify_stock(s: dict) -> dict | None:
        """종목코드가 실제 상장 중이고 현재가를 조회할 수 있으면 enriched dict 반환.
        개별 타임아웃 8초 — 상폐/데이터없음 종목이 전체 응답을 막지 않도록."""
        code = str(s.get("code", "")).strip().zfill(6)
        if not code.isdigit() or len(code) != 6:
            return None
        try:
            price = await asyncio.wait_for(
                stock_service.get_stock_price_async(code, False),
                timeout=8.0,
            )
        except asyncio.TimeoutError:
            logger.warning("verify_stock timeout [%s]", code)
            return None
        if not price:
            return None
        return {
            "code": code,
            "name": price.get("name") or s.get("name", ""),
            "market": "KRX",
            "current_price": price.get("current_price"),
            "change_rate": price.get("change_rate"),
            "reason": s.get("reason", ""),
        }

    verify_tasks = [verify_stock(s) for s in raw_stocks[:12]]  # 최대 15→12개로 축소
    verified_results = await asyncio.gather(*verify_tasks)
    verified_stocks = [r for r in verified_results if r is not None][:10]

    # ── 3. 뉴스 + 정책 병렬 조회 ──
    news_result, policy_result = await asyncio.gather(
        news_service.get_news_list(limit=5, keywords=kw_str),
        asyncio.to_thread(policy_service.get_policy_list, limit=3, keywords=kw_str),
    )

    return {
        "stocks": verified_stocks,
        "news": news_result["items"],
        "policies": policy_result["items"],
    }


def _fetch_market_index() -> dict:
    """yfinance로 KOSPI/KOSDAQ 최근 거래일 지수를 직접 조회한다.

    장 마감·공휴일에도 마지막 거래일 값을 반환.
    Returns: {"kospi": {"value": float, "change_rate": float}, "kosdaq": {...}}
    """
    result = {}
    try:
        import yfinance as yf
        # Yahoo Finance 지수 심볼: ^KS11=KOSPI, ^KQ11=KOSDAQ
        index_map = {"kospi": "^KS11", "kosdaq": "^KQ11"}
        for name, symbol in index_map.items():
            try:
                hist = yf.Ticker(symbol).history(period="5d")
                if hist.empty:
                    continue
                last = hist.iloc[-1]
                prev = hist.iloc[-2] if len(hist) > 1 else hist.iloc[-1]
                close_v = float(last.get("Close", 0))
                prev_v  = float(prev.get("Close", close_v))
                if close_v <= 0:
                    continue
                change_rate = round((close_v - prev_v) / prev_v * 100, 2) if prev_v > 0 else 0.0
                result[name] = {"value": round(close_v, 2), "change_rate": change_rate}
            except Exception as e:
                logger.warning("yfinance 지수 조회 실패 [%s]: %s", symbol, e)
    except Exception as e:
        logger.warning("_fetch_market_index 전체 실패: %s", e)
    return result


@router.get("")
async def get_dashboard():
    """대시보드 기본 데이터: 시장 지수 + 뉴스 + 정책 (키워드 없이). 5분 Supabase 캐시."""
    cache_key = "dashboard_summary"
    cached = get_generic_cache(cache_key)
    if cached:
        return cached

    news_task = news_service.get_news_list(limit=3)
    policy_task = asyncio.to_thread(policy_service.get_policy_list, limit=2)
    index_task = asyncio.to_thread(_fetch_market_index)

    results = await asyncio.gather(news_task, policy_task, index_task)

    news = results[0]
    policies = results[1]
    market_summary = results[2]  # {"kospi": {...}, "kosdaq": {...}}

    response = {
        "top_news": news["items"],
        "hot_policies": policies["items"],
        "market_summary": market_summary,
    }
    set_generic_cache(cache_key, response, _CACHE_TTL_DASHBOARD)
    return response
