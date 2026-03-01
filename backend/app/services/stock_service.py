import FinanceDataReader as fdr
import pandas as pd
import numpy as np
import asyncio
from datetime import datetime, timedelta
import logging

from app.services.generic_cache_service import get_generic_cache, set_generic_cache

logger = logging.getLogger(__name__)

# pykrx import 사전 검증 (종목 목록 폴백용으로 여전히 필요)
try:
    from pykrx import stock as _pykrx_stock_check  # noqa: F401
    _PYKRX_AVAILABLE = True
except ImportError as e:
    _PYKRX_AVAILABLE = False
    logger.error(
        "pykrx import 실패 — 종목 목록 폴백을 사용할 수 없습니다. "
        "'pip install multipledispatch pykrx' 를 실행하세요. 원인: %s", e
    )

# 주요 종목 목록 (검색용 인메모리 캐시)
STOCK_LIST_CACHE: list[dict] | None = None

# 캐시 TTL (초)
_CACHE_TTL_PRICE = 180  # 3분


# ---------------------------------------------------------------------------
# 유틸 — fdr 컬럼명 유연 탐색
# ---------------------------------------------------------------------------
def _safe_col(row, *names, default=None):
    """pandas Series에서 여러 가능한 컬럼명 중 첫 번째로 존재하는 값을 반환한다."""
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


# ---------------------------------------------------------------------------
# 종목 목록 — fdr → pykrx → DART pkl 순 폴백
# ---------------------------------------------------------------------------
def _get_pykrx_stock_list() -> list[dict]:
    """pykrx로 KRX 종목 목록 전체를 가져온다 (fdr 완전 실패 시 폴백)."""
    try:
        from pykrx import stock as pykrx_stock
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
    """DART 공시 기업코드 캐시(pkl)로 상장 종목 목록을 가져온다 (최후 폴백)."""
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

        listed = df[df["stock_code"].str.strip().str.len() == 6]
        result = []
        for _, row in listed.iterrows():
            code = str(row["stock_code"]).strip().zfill(6)
            name = str(row["corp_name"]).strip()
            result.append({"code": code, "name": name, "market": "KRX"})

        logger.info(
            "DART corp codes fallback 로드 완료: %d종목 (%s)",
            len(result), os.path.basename(pkl_files[-1])
        )
        return result
    except Exception as e:
        logger.error("_get_dart_corp_codes_stock_list 실패: %s", e)
        return []


def get_stock_list() -> list[dict]:
    """KRX 전체 종목 목록을 가져온다. fdr → KOSPI+KOSDAQ 분리 → pykrx → DART pkl 순 폴백."""
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

    # 2) KOSPI + KOSDAQ 분리
    try:
        df_kospi = fdr.StockListing("KOSPI")
        df_kosdaq = fdr.StockListing("KOSDAQ")
        result = _parse_fdr_listing_df(df_kospi) + _parse_fdr_listing_df(df_kosdaq)
        if result:
            STOCK_LIST_CACHE = result
            logger.info("KRX 종목 목록 fdr(KOSPI+KOSDAQ) 로드 완료: %d종목", len(result))
            return STOCK_LIST_CACHE
        logger.warning("fdr KOSPI/KOSDAQ 분리도 빈 결과 → pykrx 폴백")
    except Exception as e:
        logger.warning("fdr KOSPI/KOSDAQ 실패: %s → pykrx 폴백", e)

    # 3) pykrx 폴백
    result = _get_pykrx_stock_list()
    if result:
        STOCK_LIST_CACHE = result
        return STOCK_LIST_CACHE
    logger.warning("pykrx 종목 목록도 실패 → DART corp codes 폴백 시도")

    # 4) DART corp codes pkl 폴백
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

    for s in stocks:
        if query_upper in s["name"].upper() or query_upper in s["code"]:
            results.append(s)
        if len(results) >= 20:
            break

    # 목록에 없고 6자리 코드 입력 시 → pykrx 단일 조회
    if not results and query_stripped.isdigit() and len(query_stripped) <= 6:
        code = query_stripped.zfill(6)
        name = _pykrx_name(code)
        if name:
            results.append({"code": code, "name": name, "market": "KRX"})

    return results


# ---------------------------------------------------------------------------
# 현재가 (KIS API)
# ---------------------------------------------------------------------------
def get_stock_price(code: str, fundamentals: bool = True) -> dict | None:
    """[Sync Wrapper] 레거시 호환용. FastAPI에서는 get_stock_price_async를 사용할 것."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            logger.warning(
                "Async loop is running but synchronous get_stock_price called. "
                "Use get_stock_price_async instead."
            )
    except RuntimeError:
        pass
    return asyncio.run(get_stock_price_async(code, fundamentals))


async def get_stock_price_async(code: str, fundamentals: bool = True) -> dict | None:
    """종목의 현재 시세와 재무 지표를 반환한다 (KIS API, 비동기 + 캐시).

    KIS /inquire-price 1회 호출로 현재가 + PBR/PER/EPS/BPS를 가져온다.
    수급(기관/외국인)은 fundamentals=True일 때 추가 조회한다.
    """
    from app.services import kis_service  # 순환 import 방지

    cache_key = f"stock_price:{code}:{fundamentals}"
    cached = get_generic_cache(cache_key)
    if cached:
        return cached

    try:
        # 1. KIS 현재가 + 재무 지표
        kis_data = await kis_service.get_price(code)
        if not kis_data:
            logger.warning("KIS 현재가 조회 실패: code=%s", code)
            return None

        # 2. 종목명 — 캐시 목록 우선, 없으면 pykrx 단일 조회
        stocks = get_stock_list()
        name = code
        for s in stocks:
            if s["code"] == code:
                name = s["name"]
                break
        if name == code:
            pykrx_name = await asyncio.to_thread(_pykrx_name, code)
            if pykrx_name:
                name = pykrx_name

        # 3. 수급 (KIS, fundamentals=True일 때만)
        investor: dict = {}
        supply_str = "정보 없음"
        if fundamentals:
            investor = await kis_service.get_investor(code)
            supply_str = investor.get("display", "정보 없음")

        # 4. ROE 계산 (EPS / BPS × 100)
        eps = kis_data.get("eps")
        bps = kis_data.get("bps")
        roe = round(eps / bps * 100, 2) if eps and bps and bps > 0 else None
        pbr = kis_data.get("pbr")

        result = {
            "code": code,
            "name": name,
            "current_price": kis_data["current_price"],
            "change": kis_data["change"],
            "change_rate": kis_data["change_rate"],
            "volume": kis_data["volume"],
            "high": kis_data["high"],
            "low": kis_data["low"],
            # KIS 재무 지표
            "pbr": pbr,
            "roe": roe,
            "per": kis_data.get("per"),
            "eps": eps,
            "bps": bps,
            "market_cap": kis_data.get("market_cap"),
            # Phase 3 이후 DART에서 채워질 필드
            "debt_ratio": None,
            "revenue_growth": None,
            "operating_margin": None,
            "operating_cashflow": None,
            "영문종목명": None,
            # 레거시 키 (기존 router/frontend 호환)
            "가성비 점수": pbr,
            "장사 수완": roe,
            "수급": supply_str,
            # 수급 원본 — get_structured_analysis_data에서 재사용 (중복 API 호출 방지)
            "_investor": investor,
        }

        set_generic_cache(cache_key, result, _CACHE_TTL_PRICE)
        return result

    except Exception as e:
        logger.error("get_stock_price_async error: code=%s, %s", code, e, exc_info=True)
        return None


# ---------------------------------------------------------------------------
# 차트 데이터 (FDR — Phase 5에서 KIS로 교체 예정)
# ---------------------------------------------------------------------------
async def get_chart_data_async(code: str, period: str = "3m", interval: str = "daily") -> dict | None:
    """종목 차트 데이터 비동기 래퍼."""
    return await asyncio.to_thread(get_chart_data, code, period, interval)


def get_chart_data(code: str, period: str = "3m", interval: str = "daily") -> dict | None:
    """종목의 차트 데이터를 가져온다 (fdr)."""
    period_map = {"1m": 30, "3m": 90, "6m": 180, "1y": 365}
    days = period_map.get(period, 90)

    try:
        end = datetime.now()
        start = end - timedelta(days=days)
        df = fdr.DataReader(code, start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))
        if df.empty:
            logger.warning("차트 데이터 비어있음: code=%s period=%s", code, period)
            return None

        cols = df.columns.tolist()
        open_col  = next((c for c in cols if c in ("Open",  "open",  "시가")), None)
        high_col  = next((c for c in cols if c in ("High",  "high",  "고가")), None)
        low_col   = next((c for c in cols if c in ("Low",   "low",   "저가")), None)
        close_col = next((c for c in cols if c in ("Close", "close", "종가")), None)
        vol_col   = next((c for c in cols if c in ("Volume", "volume", "거래량")), None)

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
                "date":   date.strftime("%Y-%m-%d"),
                "open":   float(_safe_col(row, "Open",   "open",   "시가")   or close_v),
                "high":   float(_safe_col(row, "High",   "high",   "고가")   or close_v),
                "low":    float(_safe_col(row, "Low",    "low",    "저가")   or close_v),
                "close":  float(close_v),
                "volume": int(_safe_col(row, "Volume", "volume", "거래량") or 0),
            })

        return {"code": code, "name": name, "period": period, "data": data}
    except Exception:
        return None


# ---------------------------------------------------------------------------
# RSI 계산
# ---------------------------------------------------------------------------
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
    return round(float(100 - (100 / (1 + rs))), 1)


# ---------------------------------------------------------------------------
# AI 분석용 구조화 데이터
# ---------------------------------------------------------------------------
async def get_structured_analysis_data(code: str) -> dict | None:
    """AI 분석용 구조화된 데이터를 반환한다 (비동기).

    - 현재가/재무: KIS API (get_stock_price_async 캐시 재사용)
    - 수급: get_stock_price_async 내부에서 이미 조회한 _investor 재사용 (중복 호출 없음)
    - 차트: FDR (RSI, 이동평균선 계산 포함)
    """
    # 1. 현재가 + 재무 + 수급 원본 (캐시 재사용)
    price = await get_stock_price_async(code)
    if not price:
        return None

    # 2. 차트 (FDR)
    chart = await asyncio.to_thread(get_chart_data, code, period="3m")

    # 3. 차트 분석 — RSI, 이동평균선
    rsi = None
    chart_summary = ""
    if chart and chart.get("data"):
        data = chart["data"]
        closes = [float(d["close"]) for d in data]
        rsi = _calc_rsi(closes, 14)
        if len(data) >= 20:
            recent = data[-20:]
            closes_20 = [d["close"] for d in recent]
            ma5  = sum(closes_20[-5:])  / 5
            ma20 = sum(closes_20[-20:]) / 20
            trend = "상승" if ma5 > ma20 else "하락"
            chart_summary = f"5일이평 {ma5:,.0f}원, 20일이평 {ma20:,.0f}원 (단기{trend}세)"
        else:
            chart_summary = f"최근 {len(data)}일 데이터. 종가: {data[-1]['close']:,.0f}원"

    # 4. 수급 — get_stock_price_async가 이미 조회한 investor 데이터 재사용
    investor = price.get("_investor") or {}
    inst_net  = investor.get("inst_net_buy")
    fore_net  = investor.get("fore_net_buy")
    supply_raw = investor.get("display", "정보 없음")

    # 시가총액 대비 순매수 비율
    market_cap = price.get("market_cap")
    supply_pct = None
    if market_cap and market_cap > 0 and inst_net is not None and fore_net is not None:
        net_buy = inst_net + fore_net
        supply_pct = round((net_buy / market_cap) * 100, 3)

    pbr = price.get("pbr")
    roe = price.get("roe")

    return {
        "종목명":   price["name"],
        "영문종목명": price.get("영문종목명"),
        "종목코드": code,
        "현재가":   price["current_price"],
        "등락률":   price["change_rate"],
        "재무": {
            "가성비_점수_PBR":      pbr  if pbr  is not None else "데이터 없음",
            "장사_수완_ROE":        roe  if roe  is not None else "데이터 없음",
            "빚쟁이_지수_부채비율": price.get("debt_ratio")       or "데이터 없음",
            "매출성장률_퍼센트":    price.get("revenue_growth")    or "데이터 없음",
            "영업이익률_퍼센트":    price.get("operating_margin")  or "데이터 없음",
            "영업활동현금흐름":     price.get("operating_cashflow") or "데이터 없음",
        },
        "수급": {
            "최근10일_외국인_기관":    supply_raw,
            "수급_시가총액비율_퍼센트": supply_pct,
            "시가총액_원":             market_cap,
        },
        "차트": {
            "요약":     chart_summary,
            "RSI_14":   rsi,
            "최근_일봉": chart["data"][-10:] if chart and chart.get("data") else [],
        },
        "판정_가이드": {
            "RSI_70이상":           "화상 주의",
            "RSI_30이하":           "동상 주의",
            "부채비율_100이상":     "허덕인다",
            "영업현금흐름_마이너스": "장부만 이익",
            "수급_시가총액비율_0.1퍼이상": "싹 쓸어담는 중",
        },
    }
