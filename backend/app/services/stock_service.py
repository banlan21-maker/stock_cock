import FinanceDataReader as fdr
import pandas as pd
import numpy as np
import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
import logging

from app.services.generic_cache_service import get_generic_cache, set_generic_cache

logger = logging.getLogger(__name__)

# pykrx import 사전 검증 (startup 시 누락 패키지 즉시 감지)
try:
    from pykrx import stock as _pykrx_stock_check  # noqa: F401
    _PYKRX_AVAILABLE = True
except ImportError as e:
    _PYKRX_AVAILABLE = False
    logger.error(
        "pykrx import 실패 — PBR·수급 데이터를 가져올 수 없습니다. "
        "'pip install multipledispatch pykrx' 를 실행하세요. 원인: %s", e
    )

# 주요 종목 목록 (검색용)
STOCK_LIST_CACHE: list[dict] | None = None

# 캐시 TTL (초)
_CACHE_TTL_PRICE = 180  # 3분


def get_stock_list() -> list[dict]:
    """KRX 전체 종목 목록을 가져온다."""
    global STOCK_LIST_CACHE
    if STOCK_LIST_CACHE is None:
        df = fdr.StockListing("KRX")
        STOCK_LIST_CACHE = [
            {
                "code": row["Code"],
                "name": row["Name"],
                "market": row.get("Market", "KRX"),
            }
            for _, row in df.iterrows()
        ]
    return STOCK_LIST_CACHE


def search_stocks(query: str) -> list[dict]:
    """종목명 또는 코드로 검색한다."""
    stocks = get_stock_list()
    query = query.strip().upper()
    results = []
    for s in stocks:
        if query in s["name"].upper() or query in s["code"]:
            results.append(s)
        if len(results) >= 20:
            break
    return results


def get_stock_price(code: str, fundamentals: bool = True) -> dict | None:
    """[Sync Wrapper] 종목의 현재 시세 (캐시 미적용, 레거시 호환용)."""
    # 동기 함수가 필요하다면 loop.run_until_complete 등을 써야 하지만,
    # FastAPI에서는 await get_stock_price_async(code)를 쓰는 게 맞음.
    # 기존 코드 호환성을 위해 유지하되, 내부에서 비동기 로직을 태우진 않음
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # 이미 루프가 돌고 있다면(FastAPI) 이 함수를 부르면 안 됨.
            # 하지만 레거시 코드나 테스트에서 불릴 수 있으므로 경고 로그
            logger.warning("Async loop is running but synchronous get_stock_price called. Use get_stock_price_async instead.")
            # return await get_stock_price_async(code, fundamentals) # 이건 불가능
    except RuntimeError:
        pass
        
    return asyncio.run(get_stock_price_async(code, fundamentals))


async def get_stock_price_async(code: str, fundamentals: bool = True) -> dict | None:
    """종목의 현재(최근 거래일) 시세와 상세 지표를 가져온다 (비동기 + 캐시)."""
    cache_key = f"stock_price:{code}:{fundamentals}"
    cached = get_generic_cache(cache_key)
    if cached:
        return cached

    try:
        # 1. 시세 조회 (FinanceDataReader) - 별도 스레드
        def fetch_fdr():
            end = datetime.now()
            start = end - timedelta(days=7)
            return fdr.DataReader(code, start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))

        df = await asyncio.to_thread(fetch_fdr)
        
        if df.empty:
            return None
        
        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else df.iloc[-1]
        change = float(latest["Close"] - prev["Close"])
        change_rate = round((change / prev["Close"]) * 100, 2) if prev["Close"] else 0
        current_price = float(latest["Close"])

        # 2. 종목명 찾기 (메모리 리스트 조회라 빠름)
        stocks = get_stock_list()
        name = code
        for s in stocks:
            if s["code"] == code:
                name = s["name"]
                break

        # 3. 상세 지표 병렬 조회
        fund: dict = {
            "pbr": None, "roe": None, "debt_ratio": None,
            "revenue_growth": None, "operating_margin": None,
            "operating_cashflow": None,
            "영문종목명": None,
        }
        supply_str = "정보 없음"

        if fundamentals:
            today_str = datetime.now().strftime("%Y%m%d")

            # 작업을 정의
            task_pk = asyncio.to_thread(_get_pykrx_fundamentals, code)
            task_yf = asyncio.to_thread(_get_yfinance_fundamentals, code)
            task_supply = asyncio.to_thread(_get_supply_pct_and_float, code, today_str)

            # 병렬 실행
            pk, yf, supply_res = await asyncio.gather(task_pk, task_yf, task_supply)
            _, _, supply_str = supply_res

            # 데이터 병합 (PyKRX 우선, YFinance 보완)
            if pk.get("PBR") is not None:
                fund["pbr"] = pk["PBR"]
            if pk.get("ROE") is not None:
                fund["roe"] = pk["ROE"]

            if fund["pbr"] is None and yf.get("PBR") is not None:
                fund["pbr"] = yf["PBR"]
            if fund["roe"] is None and yf.get("ROE") is not None:
                fund["roe"] = yf["ROE"]

            if yf.get("부채비율") is not None:
                fund["debt_ratio"] = yf["부채비율"]
            if yf.get("매출성장률") is not None:
                fund["revenue_growth"] = yf["매출성장률"]
            if yf.get("영업이익률") is not None:
                fund["operating_margin"] = yf["영업이익률"]
            if yf.get("영업활동현금흐름") is not None:
                fund["operating_cashflow"] = yf["영업활동현금흐름"]
            if yf.get("영문종목명") is not None:
                fund["영문종목명"] = yf["영문종목명"]

        result = {
            "code": code,
            "name": name,
            "current_price": current_price,
            "change": change,
            "change_rate": change_rate,
            "volume": int(latest["Volume"]),
            "high": float(latest["High"]),
            "low": float(latest["Low"]),
            **fund,
            "가성비 점수": fund["pbr"],
            "장사 수완": fund["roe"],
            "수급": supply_str,
        }

        # 캐시 저장
        set_generic_cache(cache_key, result, _CACHE_TTL_PRICE)
        return result

    except Exception as e:
        logger.error("get_stock_price_async error: %s", e)
        return None


async def get_chart_data_async(code: str, period: str = "3m", interval: str = "daily") -> dict | None:
    """종목 차트 데이터 비동기 래퍼 (병렬 조회용)."""
    return await asyncio.to_thread(get_chart_data, code, period, interval)


def get_chart_data(code: str, period: str = "3m", interval: str = "daily") -> dict | None:
    """종목의 차트 데이터를 가져온다."""
    period_map = {"1m": 30, "3m": 90, "6m": 180, "1y": 365}
    days = period_map.get(period, 90)

    try:
        end = datetime.now()
        start = end - timedelta(days=days)
        df = fdr.DataReader(code, start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))
        if df.empty:
            return None

        # 주봉 변환
        if interval == "weekly":
            df = df.resample("W").agg({
                "Open": "first",
                "High": "max",
                "Low": "min",
                "Close": "last",
                "Volume": "sum",
            }).dropna()

        stocks = get_stock_list()
        name = code
        for s in stocks:
            if s["code"] == code:
                name = s["name"]
                break

        data = []
        for date, row in df.iterrows():
            data.append({
                "date": date.strftime("%Y-%m-%d"),
                "open": float(row["Open"]),
                "high": float(row["High"]),
                "low": float(row["Low"]),
                "close": float(row["Close"]),
                "volume": int(row["Volume"]),
            })

        return {"code": code, "name": name, "period": period, "data": data}
    except Exception:
        return None


def _get_yfinance_ticker(code: str) -> str:
    """KRX 종목코드를 yfinance 티커 형식으로 변환 (005930 -> 005930.KS)"""
    base = code.replace(".KS", "").replace(".KQ", "")
    stocks = get_stock_list()
    for s in stocks:
        if s["code"] == base:
            market = s.get("Market", "KRX")
            return f"{base}.KQ" if market == "KOSDAQ" else f"{base}.KS"
    return f"{base}.KS"


def _get_pykrx_fundamentals(code: str) -> dict:
    """pykrx로 PBR, ROE(EPS/BPS) 재무 지표. 국내 주식 최우선."""
    result = {
        "PBR": None, "ROE": None,
        "매출성장률": None, "부채비율": None, "영업이익률": None,
        "영업활동현금흐름": None, "영문종목명": None
    }
    try:
        from pykrx import stock
        end = datetime.now()
        for i in range(10):
            target = (end - timedelta(days=i)).strftime("%Y%m%d")
            df = stock.get_market_fundamental_by_date(target, target, code)
            if df is None or df.empty:
                continue
            row = df.iloc[0]
            # 컬럼명 대소문자 무관하게 탐색
            row_index_upper = {str(c).upper(): c for c in row.index}
            pbr_col = row_index_upper.get("PBR")
            if pbr_col is not None:
                try:
                    f = float(row[pbr_col])
                    if f > 0:
                        result["PBR"] = round(f, 2)
                except (ValueError, TypeError):
                    pass
            eps_col = row_index_upper.get("EPS")
            bps_col = row_index_upper.get("BPS")
            if eps_col is not None and bps_col is not None:
                try:
                    b = float(row[bps_col])
                    if b > 0:
                        result["ROE"] = round(float(row[eps_col]) / b * 100, 2)
                except (ValueError, TypeError):
                    pass
            if result["PBR"] is not None or result["ROE"] is not None:
                logger.debug("pykrx result [%s] at %s: PBR=%s ROE=%s", code, target, result["PBR"], result["ROE"])
                break
        else:
            logger.debug("pykrx: %s 최근 10일 펀더멘털 데이터 없음", code)
    except Exception as e:
        logger.warning("_get_pykrx_fundamentals error [%s]: %s", code, e)
    return result


def _get_yfinance_fundamentals(code: str) -> dict:
    """yfinance로 보조 재무 (pykrx에 없는 매출성장률, 부채비율 등). 해외주/폴백용."""
    result = {
        "PBR": None, "ROE": None,
        "매출성장률": None, "부채비율": None, "영업이익률": None,
        "영업활동현금흐름": None, "영문종목명": None
    }
    try:
        import yfinance as yf
        ticker = _get_yfinance_ticker(code)
        st = yf.Ticker(ticker)
        # yfinance info 호출은 네트워크 I/O 포함
        info = st.info or {}
        if info.get("priceToBook") is not None:
            result["PBR"] = round(float(info["priceToBook"]), 2)
        if info.get("returnOnEquity") is not None:
            result["ROE"] = round(float(info["returnOnEquity"]) * 100, 2)
        if info.get("revenueGrowth") is not None:
            result["매출성장률"] = round(float(info["revenueGrowth"]) * 100, 2)
        if info.get("debtToEquity") is not None:
            result["부채비율"] = round(float(info["debtToEquity"]), 1)
        if info.get("operatingMargins") is not None:
            result["영업이익률"] = round(float(info["operatingMargins"]) * 100, 2)
        if info.get("operatingCashflow") is not None:
            result["영업활동현금흐름"] = int(info["operatingCashflow"])
        result["영문종목명"] = info.get("longName") or info.get("shortName")

        # 매출성장률 fallback: 연간 재무제표에서 직접 계산
        if result["매출성장률"] is None:
            try:
                fin = st.financials  # rows=항목, cols=날짜(최신순)
                if fin is not None and not fin.empty and len(fin.columns) >= 2:
                    for key in fin.index:
                        if "Revenue" in str(key):
                            r0 = float(fin.loc[key].iloc[0])
                            r1 = float(fin.loc[key].iloc[1])
                            if r1 != 0:
                                result["매출성장률"] = round((r0 - r1) / abs(r1) * 100, 2)
                            break
            except Exception as e:
                logger.debug("yfinance 매출성장률 fallback [%s]: %s", code, e)

        # 영업활동현금흐름 fallback: 현금흐름표에서 직접 조회
        if result["영업활동현금흐름"] is None:
            try:
                cf = st.cashflow  # rows=항목, cols=날짜(최신순)
                if cf is not None and not cf.empty:
                    ocf_keywords = (
                        "Operating Cash Flow",
                        "Total Cash From Operating Activities",
                        "Cash From Operations",
                        "Net Cash From Operating",
                    )
                    for key in cf.index:
                        if any(kw in str(key) for kw in ocf_keywords):
                            try:
                                val = float(cf.loc[key].iloc[0])
                                if val == val:  # NaN 체크 (NaN != NaN)
                                    result["영업활동현금흐름"] = int(val)
                            except (TypeError, ValueError):
                                pass
                            break
            except Exception as e:
                logger.debug("yfinance 영업활동현금흐름 fallback [%s]: %s", code, e)

        logger.debug(
            "yfinance result [%s]: PBR=%s 매출성장률=%s OCF=%s",
            code, result["PBR"], result["매출성장률"], result["영업활동현금흐름"],
        )
    except Exception as e:
        logger.warning("_get_yfinance_fundamentals error [%s]: %s", code, e)
    return result


def _calc_rsi(closes: list[float], period: int = 14) -> float | None:
    """종가 시리즈로 RSI(14) 계산. closes는 최소 period+1개 이상 필요."""
    if len(closes) < period + 1:
        return None
    closes_arr = np.array(closes[-period - 1:], dtype=float)
    deltas = np.diff(closes_arr)
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)
    avg_gain = np.mean(gains)
    avg_loss = np.mean(losses)
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return round(float(rsi), 1)


def _first_col(df, *names: str):
    """DataFrame 컬럼에서 names 중 존재하는 첫 컬럼명 반환."""
    if df is None or df.empty:
        return None
    cols = [str(c) for c in df.columns]
    for n in names:
        for c in cols:
            if n in c or n == c:
                return c
    return None


def _get_supply_pct_and_float(code: str, today_str: str) -> tuple[float | None, int | None, str]:
    """pykrx로 기관/외국인 수급 (거래대금 기반). 국내 거래소 전용.

    Returns:
        (시가총액대비_순매수비율_%, 시가총액_원, 표시용_텍스트)
    """
    try:
        from pykrx import stock
        # 주말/휴일 고려: 최근 거래일 탐색
        end_dt = datetime.strptime(today_str, "%Y%m%d")
        end_date = None
        for d in range(0, 8):
            cand = (end_dt - timedelta(days=d)).strftime("%Y%m%d")
            cap = stock.get_market_cap(cand, cand, code)
            if cap is not None and not cap.empty:
                end_date = cand
                break
        if not end_date:
            logger.debug("수급: %s 최근 거래일 없음 (today=%s)", code, today_str)
            return None, None, "정보 없음"

        start = (end_dt - timedelta(days=10)).strftime("%Y%m%d")

        # 거래대금(원) 기반으로 조회 — 억 단위로 표시 가능
        val_df = stock.get_market_trading_value_by_date(start, end_date, code)
        cap_df = stock.get_market_cap(start, end_date, code)

        if val_df is None or val_df.empty or cap_df is None or cap_df.empty:
            logger.debug("수급: %s val/cap df 비어있음 (%s~%s)", code, start, end_date)
            return None, None, "정보 없음"

        inst_col = _first_col(val_df, "기관합계", "기관")
        fore_col = _first_col(val_df, "외국인합계", "외국인")
        if not inst_col or not fore_col:
            logger.warning("수급: %s 기관/외국인 컬럼 없음. 컬럼: %s", code, list(val_df.columns))
            return None, None, "정보 없음"

        inst_net = float(val_df[inst_col].sum())   # 기관 순매수 (원)
        fore_net = float(val_df[fore_col].sum())   # 외국인 순매수 (원, 음수=순매도)
        net_buy = inst_net + fore_net

        # 시가총액 (가장 최근일)
        last = cap_df.iloc[-1]
        mktcap_col = _first_col(cap_df, "시가총액")
        market_cap = 0.0
        if mktcap_col:
            try:
                v = last.get(mktcap_col, 0)
                if v is not None and str(v) not in ("nan", "NaN", ""):
                    market_cap = float(v)
            except (ValueError, TypeError):
                pass

        if market_cap <= 0:
            logger.debug("수급: %s 시가총액 없음", code)
            return None, None, "정보 없음"

        pct = round((net_buy / market_cap) * 100, 3)
        raw = f"기관 {int(inst_net/1e8):+,}억, 외국인 {int(fore_net/1e8):+,}억 (최근 5일)"
        return pct, int(market_cap), raw
    except Exception as e:
        logger.warning("_get_supply_pct_and_float error [%s]: %s", code, e)
        return None, None, "정보 없음"


async def get_structured_analysis_data(code: str) -> dict | None:
    """
    AI 분석용 구조화된 데이터를 반환한다 (비동기).
    - RSI(과열도), 수급%, 부채/현금흐름 판정
    - 재무, 차트, 뉴스
    """
    # 기본 주가/재무 정보 (캐시된 비동기 함수 호출)
    price = await get_stock_price_async(code)
    if not price:
        return None

    # 차트 데이터 (별도 캐싱 없으나 DB 호출 등 고려) - FDR 호출이므로 to_thread 권장
    chart = await asyncio.to_thread(get_chart_data, code, period="3m")

    today_str = datetime.now().strftime("%Y%m%d")
    
    # 차트 분석
    rsi = None
    chart_summary = ""
    if chart and chart.get("data"):
        data = chart["data"]
        closes = [float(d["close"]) for d in data]
        rsi = _calc_rsi(closes, 14)
        if len(data) >= 20:
            recent = data[-20:]
            closes_20 = [d["close"] for d in recent]
            ma5 = sum(closes_20[-5:]) / 5
            ma20 = sum(closes_20[-20:]) / 20
            trend = "상승" if ma5 > ma20 else "하락"
            chart_summary = f"5일이평 {ma5:,.0f}원, 20일이평 {ma20:,.0f}원 (단기{trend}세)"
        else:
            chart_summary = f"최근 {len(data)}일 데이터. 종가: {data[-1]['close']:,.0f}원"

    pbr = price.get("가성비 점수")
    roe = price.get("장사 수완")
    debt_ratio = price.get("debt_ratio")
    ocf = price.get("operating_cashflow")
    rev_growth = price.get("revenue_growth")
    op_margin = price.get("operating_margin")

    supply_pct, outstanding, supply_raw = await asyncio.to_thread(
        _get_supply_pct_and_float, code, today_str
    )

    return {
        "종목명": price["name"],
        "영문종목명": price.get("영문종목명"),
        "종목코드": code,
        "현재가": price["current_price"],
        "등락률": price["change_rate"],
        "재무": {
            "가성비_점수_PBR": pbr if pbr is not None else "데이터 없음",
            "장사_수완_ROE": roe if roe is not None else "데이터 없음",
            "빚쟁이_지수_부채비율": debt_ratio if debt_ratio is not None else "데이터 없음",
            "매출성장률_퍼센트": rev_growth if rev_growth is not None else "데이터 없음",
            "영업이익률_퍼센트": op_margin if op_margin is not None else "데이터 없음",
            "영업활동현금흐름": ocf if ocf is not None else "데이터 없음",
        },
        "수급": {
            "최근5일_외국인_기관": supply_raw if supply_raw else "정보 없음",
            "수급_시가총액비율_퍼센트": supply_pct,
            "시가총액_원": outstanding,
        },
        "차트": {
            "요약": chart_summary,
            "RSI_14": rsi,
            "최근_일봉": chart["data"][-10:] if chart and chart.get("data") else [],
        },
        "판정_가이드": {
            "RSI_70이상": "화상 주의",
            "RSI_30이하": "동상 주의",
            "부채비율_100이상": "허덕인다",
            "영업현금흐름_마이너스": "장부만 이익",
            "수급_시가총액비율_0.1퍼이상": "싹 쓸어담는 중",
        },
    }
