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


def _safe_col(row, *names, default=None):
    """pandas Series/행에서 여러 가능한 컬럼명 중 첫 번째로 존재하는 값을 반환한다.
    fdr 버전별로 컬럼명이 달라지는 문제(Open/open/시가 등)에 대응한다.
    """
    for n in names:
        try:
            v = row[n]
            if v is not None and not (isinstance(v, float) and np.isnan(v)):
                return v
        except (KeyError, IndexError, TypeError):
            continue
    return default


def _parse_fdr_listing_df(df) -> list[dict]:
    """fdr StockListing DataFrame을 종목 목록으로 변환 (컬럼명 유연 탐색)."""
    if df is None or df.empty:
        return []
    cols = df.columns.tolist()
    code_col = next((c for c in cols if c in ("Code", "Symbol", "종목코드", "code")), None)
    name_col = next((c for c in cols if c in ("Name", "종목명", "name")), None)
    market_col = next((c for c in cols if c in ("Market", "시장구분", "market")), None)
    if code_col is None or name_col is None:
        logger.warning("fdr StockListing 예상치 못한 컬럼: %s", cols)
        return []
    result = []
    for _, row in df.iterrows():
        code_val = str(row[code_col]).strip()
        if not code_val.isdigit():
            continue
        result.append({
            "code": code_val.zfill(6),
            "name": str(row[name_col]).strip(),
            "market": str(row[market_col]).strip() if market_col else "KRX",
        })
    return result


def _get_pykrx_stock_list() -> list[dict]:
    """pykrx로 KRX 종목 목록 전체를 가져온다 (fdr 완전 실패 시 폴백)."""
    try:
        from pykrx import stock as pykrx_stock
        # 최근 거래일 탐색
        date_str = None
        for i in range(7):
            candidate = (datetime.now() - timedelta(days=i)).strftime("%Y%m%d")
            try:
                codes = pykrx_stock.get_market_ticker_list(date=candidate, market="KOSPI")
                if codes:
                    date_str = candidate
                    break
            except Exception:
                continue
        if not date_str:
            return []

        all_codes: list[str] = []
        for market in ("KOSPI", "KOSDAQ"):
            try:
                all_codes += list(pykrx_stock.get_market_ticker_list(date=date_str, market=market))
            except Exception:
                pass

        result = []
        for code in all_codes:
            try:
                name = pykrx_stock.get_market_ticker_name(str(code)) or str(code)
            except Exception:
                name = str(code)
            result.append({"code": str(code).zfill(6), "name": name, "market": "KRX"})
        logger.info("pykrx 종목 목록 로드 완료: %d종목", len(result))
        return result
    except Exception as e:
        logger.error("pykrx 종목 목록 조회 실패: %s", e)
        return []


def _get_dart_corp_codes_stock_list() -> list[dict]:
    """DART 공시 기업코드 캐시(pkl)로 상장 종목 목록을 가져온다 (최후 폴백).

    fdr·pykrx 모두 실패할 때 docs_cache/opendartreader_corp_codes_*.pkl 을 사용한다.
    """
    try:
        import glob as _glob
        import pickle
        import os

        cache_dir = os.path.normpath(
            os.path.join(os.path.dirname(__file__), "..", "..", "docs_cache")
        )
        pkl_files = sorted(
            _glob.glob(os.path.join(cache_dir, "opendartreader_corp_codes_*.pkl"))
        )
        if not pkl_files:
            logger.warning("DART corp codes pkl 파일 없음: %s", cache_dir)
            return []

        with open(pkl_files[-1], "rb") as f:
            df = pickle.load(f)

        # stock_code가 6자리인 행만 → 상장사
        listed = df[df["stock_code"].str.strip().str.len() == 6]
        result = []
        for _, row in listed.iterrows():
            code = str(row["stock_code"]).strip().zfill(6)
            name = str(row["corp_name"]).strip()
            result.append({"code": code, "name": name, "market": "KRX"})

        logger.info("DART corp codes fallback 로드 완료: %d종목 (%s)", len(result), os.path.basename(pkl_files[-1]))
        return result
    except Exception as e:
        logger.error("_get_dart_corp_codes_stock_list 실패: %s", e)
        return []


def get_stock_list() -> list[dict]:
    """KRX 전체 종목 목록을 가져온다. fdr → KOSPI+KOSDAQ 분리 → pykrx 순으로 폴백."""
    global STOCK_LIST_CACHE
    if STOCK_LIST_CACHE is not None:
        return STOCK_LIST_CACHE

    # 1) fdr.StockListing("KRX")
    try:
        df = fdr.StockListing("KRX")
        result = _parse_fdr_listing_df(df)
        if result:
            STOCK_LIST_CACHE = result
            logger.info("KRX 종목 목록 fdr(KRX) 로드 완료: %d종목", len(result))
            return STOCK_LIST_CACHE
        logger.warning("fdr.StockListing('KRX') 빈 결과 → KOSPI/KOSDAQ 분리 시도")
    except Exception as e:
        logger.warning("fdr.StockListing('KRX') 실패: %s → KOSPI/KOSDAQ 분리 시도", e)

    # 2) KOSPI + KOSDAQ 분리 시도
    try:
        df_kospi  = fdr.StockListing("KOSPI")
        df_kosdaq = fdr.StockListing("KOSDAQ")
        result = _parse_fdr_listing_df(df_kospi) + _parse_fdr_listing_df(df_kosdaq)
        if result:
            STOCK_LIST_CACHE = result
            logger.info("KRX 종목 목록 fdr(KOSPI+KOSDAQ) 로드 완료: %d종목", len(result))
            return STOCK_LIST_CACHE
        logger.warning("fdr KOSPI/KOSDAQ 분리도 빈 결과 → pykrx 폴백")
    except Exception as e:
        logger.warning("fdr KOSPI/KOSDAQ 실패: %s → pykrx 폴백", e)

    # 3) pykrx 폴백 (느리지만 최후 수단)
    result = _get_pykrx_stock_list()
    if result:
        STOCK_LIST_CACHE = result
        return STOCK_LIST_CACHE
    logger.warning("pykrx 종목 목록도 실패 → DART corp codes 폴백 시도")

    # 4) DART corp codes pkl 폴백 (오프라인 데이터, 가장 마지막 수단)
    result = _get_dart_corp_codes_stock_list()
    STOCK_LIST_CACHE = result
    if not result:
        logger.error("종목 목록 모든 소스 실패 — 검색/종목명 표시 불가")
    return STOCK_LIST_CACHE


def _pykrx_name(code: str) -> str | None:
    """pykrx로 단일 종목명을 조회한다 (get_stock_list 실패 시 개별 폴백용)."""
    try:
        from pykrx import stock as pykrx_stock
        name = pykrx_stock.get_market_ticker_name(code)
        return name if name else None
    except Exception:
        return None


def search_stocks(query: str) -> list[dict]:
    """종목명 또는 코드로 검색한다. 목록이 비어있어도 6자리 코드 직접 조회를 시도한다."""
    stocks = get_stock_list()
    query_stripped = query.strip()
    query_upper = query_stripped.upper()
    results = []

    # 목록 기반 검색
    for s in stocks:
        if query_upper in s["name"].upper() or query_upper in s["code"]:
            results.append(s)
        if len(results) >= 20:
            break

    # 목록 비어있고 6자리 코드 입력 시 → pykrx 단일 조회
    if not results and query_stripped.isdigit() and len(query_stripped) <= 6:
        code = query_stripped.zfill(6)
        name = _pykrx_name(code)
        if name:
            results.append({"code": code, "name": name, "market": "KRX"})

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
            logger.warning("fdr.DataReader 결과 비어있음: code=%s", code)
            return None

        # fdr 버전에 따라 컬럼명이 다를 수 있음 (Open/open/시가 등)
        logger.debug("fdr 가격 데이터 컬럼: %s", df.columns.tolist())
        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else df.iloc[-1]

        close_curr = _safe_col(latest, "Close", "close", "종가")
        close_prev = _safe_col(prev, "Close", "close", "종가")
        if close_curr is None:
            logger.error("종가 컬럼 없음: code=%s, cols=%s", code, df.columns.tolist())
            return None

        close_curr = float(close_curr)
        close_prev = float(close_prev) if close_prev is not None else close_curr
        change = close_curr - close_prev
        change_rate = round((change / close_prev) * 100, 2) if close_prev else 0
        current_price = close_curr

        vol_ = _safe_col(latest, "Volume", "volume", "거래량")
        high_ = _safe_col(latest, "High", "high", "고가")
        low_ = _safe_col(latest, "Low", "low", "저가")

        # 2. 종목명 찾기: 캐시 목록 우선, 없으면 pykrx 단일 조회
        stocks = get_stock_list()
        name = code
        for s in stocks:
            if s["code"] == code:
                name = s["name"]
                break
        if name == code:
            # 종목 목록이 비어있거나 해당 코드가 없을 때 pykrx로 개별 조회
            pykrx_name = await asyncio.to_thread(_pykrx_name, code)
            if pykrx_name:
                name = pykrx_name

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
            "volume": int(vol_) if vol_ is not None else 0,
            "high": float(high_) if high_ is not None else current_price,
            "low": float(low_) if low_ is not None else current_price,
            **fund,
            "가성비 점수": fund["pbr"],
            "장사 수완": fund["roe"],
            "수급": supply_str,
        }

        # 캐시 저장
        set_generic_cache(cache_key, result, _CACHE_TTL_PRICE)
        return result

    except Exception as e:
        logger.error("get_stock_price_async error: code=%s, %s", code, e, exc_info=True)
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
            logger.warning("차트 데이터 비어있음: code=%s period=%s", code, period)
            return None

        logger.debug("차트 데이터 컬럼: %s", df.columns.tolist())

        # 주봉 변환 — fdr 컬럼명에 맞게 유연하게 탐색
        cols = df.columns.tolist()
        open_col  = next((c for c in cols if c in ("Open",  "open",  "시가")), None)
        high_col  = next((c for c in cols if c in ("High",  "high",  "고가")), None)
        low_col   = next((c for c in cols if c in ("Low",   "low",   "저가")), None)
        close_col = next((c for c in cols if c in ("Close", "close", "종가")), None)
        vol_col   = next((c for c in cols if c in ("Volume","volume","거래량")), None)

        if close_col is None:
            logger.error("차트 종가 컬럼 없음: code=%s, cols=%s", code, cols)
            return None

        if interval == "weekly":
            agg_dict = {}
            if open_col:  agg_dict[open_col]  = "first"
            if high_col:  agg_dict[high_col]  = "max"
            if low_col:   agg_dict[low_col]   = "min"
            if close_col: agg_dict[close_col] = "last"
            if vol_col:   agg_dict[vol_col]   = "sum"
            df = df.resample("W").agg(agg_dict).dropna(subset=[close_col])

        stocks = get_stock_list()
        name = code
        for s in stocks:
            if s["code"] == code:
                name = s["name"]
                break
        if name == code:
            pykrx_name = _pykrx_name(code)
            if pykrx_name:
                name = pykrx_name

        data = []
        for date, row in df.iterrows():
            close_v = _safe_col(row, "Close", "close", "종가")
            if close_v is None:
                continue
            data.append({
                "date": date.strftime("%Y-%m-%d"),
                "open":   float(_safe_col(row, "Open",   "open",   "시가")   or close_v),
                "high":   float(_safe_col(row, "High",   "high",   "고가")   or close_v),
                "low":    float(_safe_col(row, "Low",    "low",    "저가")   or close_v),
                "close":  float(close_v),
                "volume": int(_safe_col(row, "Volume", "volume", "거래량") or 0),
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
            # 종목 목록 dict 키는 소문자 "market"
            market = s.get("market", "KRX")
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

        # PBR 계산 fallback: balance sheet의 자기자본 ÷ 주식수로 BPS 산출
        if result["PBR"] is None:
            try:
                bs = st.balance_sheet
                shares = info.get("sharesOutstanding") or info.get("impliedSharesOutstanding")
                price = info.get("currentPrice") or info.get("regularMarketPrice")
                if bs is not None and not bs.empty and shares and price:
                    for key in bs.index:
                        if "Stockholders Equity" in str(key):
                            equity = float(bs.loc[key].iloc[0])
                            bps = equity / float(shares)
                            if bps > 0:
                                result["PBR"] = round(float(price) / bps, 2)
                            break
            except Exception as e:
                logger.debug("yfinance PBR 계산 fallback [%s]: %s", code, e)

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
