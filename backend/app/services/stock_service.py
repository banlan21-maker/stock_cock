import time
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
_STOCK_LIST_CACHE_TS: float = 0.0          # 마지막 성공적 로드 시각
_STOCK_LIST_CACHE_TTL: float = 3600.0     # 1시간마다 자동 갱신

# 캐시 TTL (초)
_CACHE_TTL_PRICE = 180  # 3분

# 실패 종목 단기 캐시 (상폐/데이터없음 종목 반복 재시도 방지)
_PRICE_FAIL_CACHE: dict[str, float] = {}   # code → 실패 시각
_PRICE_FAIL_TTL: float = 600.0             # 10분간 재시도 스킵

# fdr.StockListing('KRX') 실패 회로 차단기 (KRX API 불안정 대응)
_FDR_KRX_FAIL_TS: float = 0.0             # 마지막 실패 시각
_FDR_KRX_FAIL_TTL: float = 1800.0         # 30분간 스킵


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
# 종목명 정규화 (검색 매칭 향상)
# ---------------------------------------------------------------------------
def _normalize_stock_name(name: str) -> str:
    """종목명에서 법인 접미어·공백을 제거해 검색 정규화에 사용한다."""
    n = name.strip()
    for suffix in ("(주)", "(유)", "주식회사", " 홀딩스", "홀딩스", "(코스닥)", "(코스피)", " Inc.", " Corp.", " Co."):
        if n.endswith(suffix):
            n = n[: -len(suffix)].strip()
    # 내부 공백, 특수 공백 제거
    n = n.replace(" ", "").replace("\xa0", "").replace("\u200b", "")
    return n


# ---------------------------------------------------------------------------
# 종목 목록 — fdr → KOSPI+KOSDAQ 분리 → pykrx → DART pkl 순 폴백
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
        for market in ("KOSPI", "KOSDAQ", "KONEX"):
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
            # pykrx market 정보 포함 (yfinance suffix 결정에 필요)
            result.append({"code": str(code).zfill(6), "name": name, "market": "KRX"})
        logger.info("pykrx 종목 목록 로드 완료: %d종목", len(result))
        return result
    except Exception as e:
        logger.error("pykrx 종목 목록 조회 실패: %s", e)
        return []


def _fix_corp_name_encoding(name: str) -> str:
    """CP949 bytes가 latin-1 str로 잘못 저장된 경우 올바른 한글 Unicode로 변환한다.

    구버전 opendartreader pkl에서 corp_name이 latin-1(code points < 256)로
    잘못 저장되는 경우가 있다. 이 경우 latin-1 인코딩 → CP949 디코딩으로 복원한다.
    """
    try:
        # 모든 문자가 latin-1 범위(< 256)이면 CP949 bytes로 잘못 저장된 것으로 판단
        if all(ord(c) < 256 for c in name):
            return name.encode("latin-1").decode("cp949")
    except (UnicodeDecodeError, UnicodeEncodeError):
        pass
    return name


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
            name = _fix_corp_name_encoding(str(row["corp_name"]).strip())
            result.append({"code": code, "name": name, "market": "KRX"})

        logger.info(
            "DART corp codes fallback 로드 완료: %d종목 (%s)",
            len(result), os.path.basename(pkl_files[-1])
        )
        return result
    except Exception as e:
        logger.error("_get_dart_corp_codes_stock_list 실패: %s", e)
        return []


def get_stock_list(force_refresh: bool = False) -> list[dict]:
    """KRX 전체 종목 목록을 가져온다. fdr → KOSPI+KOSDAQ 분리 → pykrx → DART pkl 순 폴백.

    - STOCK_LIST_CACHE 가 비어있거나 TTL(1시간) 초과 시 자동 갱신
    - force_refresh=True 이면 캐시를 무효화하고 강제 재조회
    """
    global STOCK_LIST_CACHE, _STOCK_LIST_CACHE_TS

    now = time.time()
    age = now - _STOCK_LIST_CACHE_TS
    # 유효한 캐시: 비어있지 않고, TTL 이내
    if not force_refresh and STOCK_LIST_CACHE and age < _STOCK_LIST_CACHE_TTL:
        return STOCK_LIST_CACHE

    # 강제 갱신 또는 캐시 만료 시 재로드
    if force_refresh:
        STOCK_LIST_CACHE = None
        logger.info("STOCK_LIST_CACHE 강제 갱신 요청")
    elif STOCK_LIST_CACHE and age >= _STOCK_LIST_CACHE_TTL:
        logger.info("STOCK_LIST_CACHE TTL 만료 (%.0f초) — 갱신", age)

    # 1) fdr.StockListing("KRX") — 최근 30분 내 실패 이력 있으면 스킵 (KRX API 불안정 대응)
    global _FDR_KRX_FAIL_TS
    if (time.time() - _FDR_KRX_FAIL_TS) > _FDR_KRX_FAIL_TTL:
        try:
            df = fdr.StockListing("KRX")
            result = _parse_fdr_listing_df(df)
            if result:
                STOCK_LIST_CACHE = result
                _STOCK_LIST_CACHE_TS = time.time()
                logger.info("KRX 종목 목록 fdr(KRX) 로드 완료: %d종목", len(result))
                return STOCK_LIST_CACHE
            logger.warning("fdr.StockListing('KRX') 빈 결과 → KOSPI/KOSDAQ 분리 시도")
            _FDR_KRX_FAIL_TS = time.time()
        except Exception as e:
            logger.warning("fdr.StockListing('KRX') 실패: %s → KOSPI/KOSDAQ 분리 시도", e)
            _FDR_KRX_FAIL_TS = time.time()
    else:
        logger.debug("fdr.StockListing('KRX') 최근 실패 기록 → 스킵 (%.0f초 남음)",
                     _FDR_KRX_FAIL_TTL - (time.time() - _FDR_KRX_FAIL_TS))

    # 2) KOSPI + KOSDAQ + KONEX 분리
    try:
        dfs = []
        for market in ("KOSPI", "KOSDAQ", "KONEX"):
            try:
                dfs.append(fdr.StockListing(market))
            except Exception:
                pass
        result = []
        for df in dfs:
            result += _parse_fdr_listing_df(df)
        if result:
            STOCK_LIST_CACHE = result
            _STOCK_LIST_CACHE_TS = time.time()
            logger.info("KRX 종목 목록 fdr(분리) 로드 완료: %d종목", len(result))
            return STOCK_LIST_CACHE
        logger.warning("fdr 분리 조회도 빈 결과 → pykrx 폴백")
    except Exception as e:
        logger.warning("fdr 분리 조회 실패: %s → pykrx 폴백", e)

    # 3) pykrx 폴백
    result = _get_pykrx_stock_list()
    if result:
        STOCK_LIST_CACHE = result
        _STOCK_LIST_CACHE_TS = time.time()
        return STOCK_LIST_CACHE
    logger.warning("pykrx 종목 목록도 실패 → DART corp codes 폴백 시도")

    # 4) DART corp codes pkl 폴백
    result = _get_dart_corp_codes_stock_list()
    if result:
        STOCK_LIST_CACHE = result
        _STOCK_LIST_CACHE_TS = time.time()
    else:
        logger.error("종목 목록 모든 소스 실패 — 검색/종목명 표시 불가")
        # 실패 시에도 빈 리스트를 캐시하되, TTL을 짧게 설정 (5분 후 재시도)
        STOCK_LIST_CACHE = []
        _STOCK_LIST_CACHE_TS = now - (_STOCK_LIST_CACHE_TTL - 300)
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
    """종목명 또는 코드로 검색한다.

    - 종목명 정규화 매칭 (접미어 제거, 공백 제거)
    - 목록 미히트 시 목록 강제 갱신 후 재시도
    - 6자리 코드 입력 시 pykrx 직접 조회
    """
    stocks = get_stock_list()
    query_stripped = query.strip()
    query_upper = query_stripped.upper()
    query_norm = _normalize_stock_name(query_stripped).upper()
    results: list[dict] = []

    for s in stocks:
        name_upper = s["name"].upper()
        name_norm = _normalize_stock_name(s["name"]).upper()
        if (
            query_upper in name_upper
            or query_upper in name_norm
            or query_norm in name_upper
            or query_norm in name_norm
            or query_upper in s["code"]
        ):
            results.append(s)
        if len(results) >= 20:
            break

    # 결과 없음: 캐시가 오래됐을 수 있으므로 강제 갱신 후 재시도 (1회)
    if not results and len(query_stripped) >= 2:
        stocks = get_stock_list(force_refresh=True)
        for s in stocks:
            name_upper = s["name"].upper()
            name_norm = _normalize_stock_name(s["name"]).upper()
            if (
                query_upper in name_upper
                or query_upper in name_norm
                or query_norm in name_upper
                or query_norm in name_norm
                or query_upper in s["code"]
            ):
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
    """종목의 현재 시세와 재무 지표를 반환한다 (비동기 + 캐시).

    1차: KIS API (한국 네트워크에서만 접근 가능)
    2차: FDR + pykrx 폴백 (GCP Cloud Functions 등 해외 서버용)
    """
    # 최근 실패 종목은 즉시 None 반환 (상폐/데이터없음 종목 반복 시도 방지)
    fail_ts = _PRICE_FAIL_CACHE.get(code)
    if fail_ts and (time.time() - fail_ts) < _PRICE_FAIL_TTL:
        return None

    cache_key = f"stock_price:{code}:{fundamentals}"
    cached = get_generic_cache(cache_key)
    if cached:
        return cached

    # ── 1차 시도: KIS API ────────────────────────────────────────────────────
    result = await _try_kis_price(code, fundamentals)

    # ── 2차 시도: FDR + pykrx 폴백 (KIS 네트워크 오류 시) ────────────────────
    if result is None:
        result = await _try_fdr_price(code, fundamentals)

    if result:
        set_generic_cache(cache_key, result, _CACHE_TTL_PRICE)
    else:
        # 데이터 없는 종목은 10분간 재시도 스킵
        _PRICE_FAIL_CACHE[code] = time.time()
    return result


async def _try_kis_price(code: str, fundamentals: bool) -> dict | None:
    """KIS API로 현재가 + 재무 지표 조회. 네트워크 오류 시 None 반환."""
    # 지수 코드는 KIS 미지원 → FDR 폴백에서 마지막 거래일 데이터 반환
    if code in ("KS11", "KQ11"):
        return None
    try:
        from app.services import kis_service  # 순환 import 방지

        kis_data = await kis_service.get_price(code)
        # 0원 = 장 마감/공휴일이거나 미지원 종목 → FDR 폴백으로 마지막 거래일 데이터 사용
        if not kis_data or kis_data.get("current_price", 0) == 0:
            return None

        # 종목명
        stocks = get_stock_list()
        name = code
        for s in stocks:
            if s["code"] == code:
                name = s["name"]
                break
        if name == code:
            pn = await asyncio.to_thread(_pykrx_name, code)
            if pn:
                name = pn

        # 수급 + yfinance 보조 재무 병렬 조회 (부채비율/매출성장률/영업이익률/영업현금흐름)
        investor: dict = {}
        yf_data: dict = {}
        supply_str = "정보 없음"
        if fundamentals:
            investor, yf_data = await asyncio.gather(
                kis_service.get_investor(code),
                asyncio.to_thread(_get_yfinance_fundamentals, code),
            )
            supply_str = investor.get("display", "정보 없음")

        eps = kis_data.get("eps")
        bps = kis_data.get("bps")
        roe = round(eps / bps * 100, 2) if eps and bps and bps > 0 else None
        pbr = kis_data.get("pbr")

        return {
            "code": code, "name": name,
            "current_price": kis_data["current_price"],
            "change": kis_data["change"],
            "change_rate": kis_data["change_rate"],
            "volume": kis_data["volume"],
            "high": kis_data["high"],
            "low": kis_data["low"],
            "pbr": pbr, "roe": roe,
            "per": kis_data.get("per"),
            "eps": eps, "bps": bps,
            "market_cap": kis_data.get("market_cap"),
            "debt_ratio": yf_data.get("부채비율"),
            "revenue_growth": yf_data.get("매출성장률"),
            "operating_margin": yf_data.get("영업이익률"),
            "operating_cashflow": yf_data.get("영업활동현금흐름"),
            "영문종목명": yf_data.get("영문종목명"),
            "가성비 점수": pbr, "장사 수완": roe,
            "수급": supply_str, "_investor": investor,
            "_source": "kis",
        }
    except Exception as e:
        # DNS 오류(해외 서버) 또는 네트워크 오류 → 폴백으로 넘김
        logger.warning("KIS API 사용 불가 [%s]: %s → FDR 폴백", code, e)
        return None


async def _try_fdr_price(code: str, fundamentals: bool) -> dict | None:
    """FDR + pykrx + yfinance로 현재가 + 재무 지표 조회 (폴백)."""
    try:
        # 1. 시세 (FDR)
        def fetch_fdr():
            end = datetime.now()
            start = end - timedelta(days=7)
            return fdr.DataReader(code, start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))

        df = await asyncio.to_thread(fetch_fdr)

        # FDR 빈 결과 → yfinance 가격 폴백
        if df.empty:
            try:
                _, ticker_str = _get_yfinance_ticker(code)
                import yfinance as yf
                yf_hist = await asyncio.to_thread(lambda: yf.Ticker(ticker_str).history(period="5d"))
                if yf_hist.empty:
                    logger.warning("FDR + yfinance 가격 폴백 모두 빈 결과 [%s] → pykrx 시도", code)
                    return await _try_pykrx_price(code, fundamentals)
                df = yf_hist
                logger.info("yfinance 가격 폴백 사용 [%s] (%s)", code, ticker_str)
            except Exception as e:
                logger.warning("yfinance 가격 폴백 실패 [%s]: %s → pykrx 시도", code, e)
                return await _try_pykrx_price(code, fundamentals)

        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else df.iloc[-1]
        close_curr = _safe_col(latest, "Close", "close", "종가")
        close_prev = _safe_col(prev, "Close", "close", "종가")
        if close_curr is None:
            return None

        close_curr = float(close_curr)
        close_prev = float(close_prev) if close_prev is not None else close_curr
        change = close_curr - close_prev
        change_rate = round((change / close_prev) * 100, 2) if close_prev else 0

        # 2. 종목명
        stocks = get_stock_list()
        name = code
        for s in stocks:
            if s["code"] == code:
                name = s["name"]
                break
        if name == code:
            pn = await asyncio.to_thread(_pykrx_name, code)
            if pn:
                name = pn

        # 3. 재무 + 수급 (병렬, fundamentals=True일 때만)
        pbr, roe = None, None
        debt_ratio, rev_growth, op_margin, ocf = None, None, None, None
        eng_name = None
        supply_str = "정보 없음"
        investor: dict = {}

        if fundamentals:
            today_str = datetime.now().strftime("%Y%m%d")
            pk, yf, supply_res = await asyncio.gather(
                asyncio.to_thread(_get_pykrx_fundamentals, code),
                asyncio.to_thread(_get_yfinance_fundamentals, code),
                asyncio.to_thread(_get_supply_pct_and_float, code, today_str),
            )
            supply_pct_val, market_cap_val, supply_str = supply_res
            # _investor에 수급 데이터 저장 (get_structured_analysis_data에서 재사용)
            investor = {
                "display": supply_str,
                "supply_pct": supply_pct_val,
                "market_cap": market_cap_val,
            }
            pbr = pk.get("PBR") or yf.get("PBR")
            roe = pk.get("ROE") or yf.get("ROE")
            debt_ratio = yf.get("부채비율")
            rev_growth = yf.get("매출성장률")
            op_margin = yf.get("영업이익률")
            ocf = yf.get("영업활동현금흐름")
            eng_name = yf.get("영문종목명")

        vol_ = _safe_col(latest, "Volume", "volume", "거래량")
        high_ = _safe_col(latest, "High", "high", "고가")
        low_ = _safe_col(latest, "Low", "low", "저가")

        return {
            "code": code, "name": name,
            "current_price": close_curr,
            "change": change, "change_rate": change_rate,
            "volume": int(vol_) if vol_ is not None else 0,
            "high": float(high_) if high_ is not None else close_curr,
            "low": float(low_) if low_ is not None else close_curr,
            "pbr": pbr, "roe": roe,
            "per": None, "eps": None, "bps": None, "market_cap": None,
            "debt_ratio": debt_ratio, "revenue_growth": rev_growth,
            "operating_margin": op_margin, "operating_cashflow": ocf,
            "영문종목명": eng_name,
            "가성비 점수": pbr, "장사 수완": roe,
            "수급": supply_str, "_investor": investor,
            "_source": "fdr",
        }
    except Exception as e:
        logger.error("FDR 폴백도 실패 [%s]: %s", code, e, exc_info=True)
        return None


# ── pykrx 가격 폴백 (FDR + yfinance 모두 실패 시, KOSDAQ 소형주 대응) ─────────

def _get_pykrx_ohlcv(code: str) -> dict | None:
    """pykrx로 최근 거래일 OHLCV + 전일비 등락률 조회."""
    try:
        from pykrx import stock as pykrx_stock
        end = datetime.now()
        start = (end - timedelta(days=10)).strftime("%Y%m%d")
        end_str = end.strftime("%Y%m%d")
        df = pykrx_stock.get_market_ohlcv(start, end_str, code)
        if df is None or df.empty:
            return None
        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else df.iloc[-1]
        close = float(latest.get("종가", 0))
        prev_close = float(prev.get("종가", close))
        if close <= 0:
            return None
        change = close - prev_close
        change_rate = round((change / prev_close) * 100, 2) if prev_close else 0
        return {
            "close": close,
            "open": float(latest.get("시가", close)),
            "high": float(latest.get("고가", close)),
            "low": float(latest.get("저가", close)),
            "volume": int(latest.get("거래량", 0)),
            "change": change,
            "change_rate": change_rate,
        }
    except Exception as e:
        logger.warning("_get_pykrx_ohlcv [%s]: %s", code, e)
        return None


async def _try_pykrx_price(code: str, fundamentals: bool) -> dict | None:
    """pykrx로 현재가 조회 (FDR + yfinance 모두 실패 시 폴백, KOSDAQ 소형주 대응)."""
    pk_data = await asyncio.to_thread(_get_pykrx_ohlcv, code)
    if not pk_data:
        logger.warning("pykrx 가격 폴백도 실패 [%s]", code)
        return None
    logger.info("pykrx 가격 폴백 사용 [%s]", code)

    stocks = get_stock_list()
    name = code
    for s in stocks:
        if s["code"] == code:
            name = s["name"]
            break
    if name == code:
        pn = await asyncio.to_thread(_pykrx_name, code)
        if pn:
            name = pn

    pbr, roe = None, None
    debt_ratio, rev_growth, op_margin, ocf = None, None, None, None
    eng_name = None
    supply_str = "정보 없음"
    investor: dict = {}

    if fundamentals:
        today_str = datetime.now().strftime("%Y%m%d")
        pk, yf, supply_res = await asyncio.gather(
            asyncio.to_thread(_get_pykrx_fundamentals, code),
            asyncio.to_thread(_get_yfinance_fundamentals, code),
            asyncio.to_thread(_get_supply_pct_and_float, code, today_str),
        )
        supply_pct_val, market_cap_val, supply_str = supply_res
        investor = {
            "display": supply_str,
            "supply_pct": supply_pct_val,
            "market_cap": market_cap_val,
        }
        pbr = pk.get("PBR") or yf.get("PBR")
        roe = pk.get("ROE") or yf.get("ROE")
        debt_ratio = yf.get("부채비율")
        rev_growth = yf.get("매출성장률")
        op_margin = yf.get("영업이익률")
        ocf = yf.get("영업활동현금흐름")
        eng_name = yf.get("영문종목명")

    return {
        "code": code, "name": name,
        "current_price": pk_data["close"],
        "change": pk_data["change"], "change_rate": pk_data["change_rate"],
        "volume": pk_data["volume"],
        "high": pk_data["high"],
        "low": pk_data["low"],
        "pbr": pbr, "roe": roe,
        "per": None, "eps": None, "bps": None, "market_cap": None,
        "debt_ratio": debt_ratio, "revenue_growth": rev_growth,
        "operating_margin": op_margin, "operating_cashflow": ocf,
        "영문종목명": eng_name,
        "가성비 점수": pbr, "장사 수완": roe,
        "수급": supply_str, "_investor": investor,
        "_source": "pykrx",
    }


# ── FDR 폴백용 내부 함수들 ────────────────────────────────────────────────────

def _get_pykrx_fundamentals(code: str) -> dict:
    """pykrx로 PBR, ROE 재무 지표. FDR 폴백 경로에서 사용."""
    result = {"PBR": None, "ROE": None}
    try:
        from pykrx import stock
        end = datetime.now()
        for i in range(10):
            target = (end - timedelta(days=i)).strftime("%Y%m%d")
            df = stock.get_market_fundamental_by_date(target, target, code)
            if df is None or df.empty:
                continue
            row = df.iloc[0]
            idx_upper = {str(c).upper(): c for c in row.index}
            pbr_col = idx_upper.get("PBR")
            if pbr_col is not None:
                try:
                    f = float(row[pbr_col])
                    if f > 0:
                        result["PBR"] = round(f, 2)
                except (ValueError, TypeError):
                    pass
            eps_col = idx_upper.get("EPS")
            bps_col = idx_upper.get("BPS")
            if eps_col and bps_col:
                try:
                    b = float(row[bps_col])
                    if b > 0:
                        result["ROE"] = round(float(row[eps_col]) / b * 100, 2)
                except (ValueError, TypeError):
                    pass
            if result["PBR"] is not None or result["ROE"] is not None:
                break
    except Exception as e:
        logger.warning("_get_pykrx_fundamentals [%s]: %s", code, e)
    return result


def _get_yfinance_ticker(code: str):
    """종목 코드에 맞는 yfinance Ticker 객체를 반환한다.

    1. STOCK_LIST_CACHE 의 market 필드로 suffix 결정 (.KS / .KQ)
    2. market 정보가 없거나 'KRX' 일 때는 .KS 먼저 시도, info 없으면 .KQ 로 재시도
    """
    import yfinance as yf

    # 지수 코드 특별 처리 (FDR: KS11/KQ11, Yahoo: ^KS11/^KQ11)
    _INDEX_MAP = {"KS11": "^KS11", "KQ11": "^KQ11"}
    if code in _INDEX_MAP:
        ticker_str = _INDEX_MAP[code]
        return yf.Ticker(ticker_str), ticker_str

    stocks = get_stock_list()
    market_info = None
    for s in stocks:
        if s["code"] == code:
            market_info = s.get("market", "")
            break

    if market_info and market_info.upper() == "KOSDAQ":
        # 확실히 코스닥 → .KQ 만 시도
        return yf.Ticker(f"{code}.KQ"), f"{code}.KQ"

    if market_info and market_info.upper() == "KOSPI":
        # 확실히 코스피 → .KS 만 시도
        return yf.Ticker(f"{code}.KS"), f"{code}.KS"

    # market 정보가 'KRX' 또는 없는 경우 → .KS 기본값 (info HTTP 호출 제거)
    # info 조회로 시장 탐지 시 1-2초 추가 소요되므로 제거. KIS/FDR이 주 데이터 소스.
    return yf.Ticker(f"{code}.KS"), f"{code}.KS"


def _fill_from_financial_statements(st, result: dict) -> None:
    """st.financials / st.cashflow / st.balance_sheet 로 누락 재무 보완.

    yfinance info 에 데이터가 없는 소형주를 위한 fallback.
    """
    # ── 영업활동현금흐름 ────────────────────────────────────────────────────────
    if result.get("영업활동현금흐름") is None:
        try:
            cf = st.cashflow
            if cf is not None and not cf.empty:
                ocf_keys = [r for r in cf.index if "Operating" in str(r) and "Cash" in str(r)]
                if not ocf_keys:
                    ocf_keys = [r for r in cf.index if "Cash Flow" in str(r) and "Operation" in str(r)]
                if ocf_keys:
                    v = cf.loc[ocf_keys[0]].iloc[0]
                    if v is not None and not (isinstance(v, float) and np.isnan(v)):
                        result["영업활동현금흐름"] = int(float(v))
        except Exception as e:
            logger.debug("cashflow fallback 실패: %s", e)

    # ── 매출성장률 / 영업이익률 ────────────────────────────────────────────────
    if result.get("매출성장률") is None or result.get("영업이익률") is None:
        try:
            fin = st.financials
            if fin is not None and not fin.empty and fin.shape[1] >= 2:
                # 매출 (Total Revenue)
                rev_keys = [r for r in fin.index if "Total Revenue" in str(r) or ("Revenue" in str(r) and "Total" in str(r))]
                if not rev_keys:
                    rev_keys = [r for r in fin.index if "Revenue" in str(r)]

                # 영업이익 (Operating Income / Operating Profit)
                op_keys = [r for r in fin.index if "Operating Income" in str(r)]
                if not op_keys:
                    op_keys = [r for r in fin.index if "Operating" in str(r) and "Income" in str(r)]

                if rev_keys:
                    rev0 = float(fin.loc[rev_keys[0]].iloc[0])
                    if result.get("매출성장률") is None and fin.shape[1] >= 2:
                        rev1 = float(fin.loc[rev_keys[0]].iloc[1])
                        if rev1 and rev1 != 0 and not np.isnan(rev0) and not np.isnan(rev1):
                            result["매출성장률"] = round((rev0 - rev1) / abs(rev1) * 100, 2)

                    if result.get("영업이익률") is None and op_keys and not np.isnan(rev0) and rev0 != 0:
                        op0 = float(fin.loc[op_keys[0]].iloc[0])
                        if not np.isnan(op0):
                            result["영업이익률"] = round(op0 / rev0 * 100, 2)
        except Exception as e:
            logger.debug("financials fallback 실패: %s", e)

    # ── 부채비율 ───────────────────────────────────────────────────────────────
    if result.get("부채비율") is None:
        try:
            bs = st.balance_sheet
            if bs is not None and not bs.empty:
                debt_keys = [r for r in bs.index if "Total Debt" in str(r)]
                if not debt_keys:
                    debt_keys = [r for r in bs.index if "Long Term Debt" in str(r)]
                eq_keys = [r for r in bs.index if "Stockholders" in str(r) and "Equity" in str(r)]
                if not eq_keys:
                    eq_keys = [r for r in bs.index if "Total Equity" in str(r)]

                if debt_keys and eq_keys:
                    debt = float(bs.loc[debt_keys[0]].iloc[0])
                    equity = float(bs.loc[eq_keys[0]].iloc[0])
                    if (
                        equity and equity > 0
                        and not np.isnan(debt) and not np.isnan(equity)
                    ):
                        result["부채비율"] = round(debt / equity * 100, 1)
        except Exception as e:
            logger.debug("balance_sheet fallback 실패: %s", e)


def _get_yfinance_fundamentals(code: str) -> dict:
    """yfinance로 보조 재무 (부채비율, 매출성장률 등). FDR/KIS 경로 모두에서 사용.

    - st.info 우선 (대형주/코스피200)
    - info 에 데이터 없으면 st.financials / st.cashflow / st.balance_sheet 로 보완 (소형주 지원)
    - market suffix 자동 감지 (.KS / .KQ)
    """
    result: dict = {
        "PBR": None, "ROE": None,
        "매출성장률": None, "부채비율": None, "영업이익률": None,
        "영업활동현금흐름": None, "영문종목명": None,
    }
    try:
        st, ticker_str = _get_yfinance_ticker(code)
        info = st.info or {}

        # ── info 기반 (대형주·코스피200에서 주로 채워짐) ──────────────────────
        if info.get("priceToBook"):
            result["PBR"] = round(float(info["priceToBook"]), 2)
        if info.get("returnOnEquity"):
            result["ROE"] = round(float(info["returnOnEquity"]) * 100, 2)
        if info.get("revenueGrowth"):
            result["매출성장률"] = round(float(info["revenueGrowth"]) * 100, 2)
        if info.get("debtToEquity"):
            result["부채비율"] = round(float(info["debtToEquity"]), 1)
        if info.get("operatingMargins"):
            result["영업이익률"] = round(float(info["operatingMargins"]) * 100, 2)
        if info.get("operatingCashflow"):
            result["영업활동현금흐름"] = int(info["operatingCashflow"])
        result["영문종목명"] = info.get("longName") or info.get("shortName")

        # ── 재무제표 fallback (소형주 — info 에 데이터 없는 경우 보완) ──────────
        needs_fallback = (
            result["매출성장률"] is None
            or result["영업이익률"] is None
            or result["영업활동현금흐름"] is None
            or result["부채비율"] is None
        )
        if needs_fallback:
            _fill_from_financial_statements(st, result)

        logger.debug(
            "_get_yfinance_fundamentals [%s] ticker=%s 매출성장률=%s 영업이익률=%s OCF=%s 부채비율=%s",
            code, ticker_str,
            result["매출성장률"], result["영업이익률"],
            result["영업활동현금흐름"], result["부채비율"],
        )
    except Exception as e:
        logger.warning("_get_yfinance_fundamentals [%s]: %s", code, e)
    return result


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
    """pykrx로 기관/외국인 수급 (FDR 폴백 경로에서 사용)."""
    try:
        from pykrx import stock
        end_dt = datetime.strptime(today_str, "%Y%m%d")
        end_date = None
        for d in range(0, 8):
            cand = (end_dt - timedelta(days=d)).strftime("%Y%m%d")
            cap = stock.get_market_cap(cand, cand, code)
            if cap is not None and not cap.empty:
                end_date = cand
                break
        if not end_date:
            return None, None, "정보 없음"

        start = (end_dt - timedelta(days=10)).strftime("%Y%m%d")
        val_df = stock.get_market_trading_value_by_date(start, end_date, code)
        cap_df = stock.get_market_cap(start, end_date, code)
        if val_df is None or val_df.empty or cap_df is None or cap_df.empty:
            return None, None, "정보 없음"

        inst_col = _first_col(val_df, "기관합계", "기관")
        fore_col = _first_col(val_df, "외국인합계", "외국인")
        if not inst_col or not fore_col:
            return None, None, "정보 없음"

        inst_net = float(val_df[inst_col].sum())
        fore_net = float(val_df[fore_col].sum())
        net_buy = inst_net + fore_net

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
            return None, None, "정보 없음"

        pct = round((net_buy / market_cap) * 100, 3)
        raw = f"기관 {int(inst_net/1e8):+,}억, 외국인 {int(fore_net/1e8):+,}억 (최근 10일)"
        return pct, int(market_cap), raw
    except Exception as e:
        logger.warning("_get_supply_pct_and_float [%s]: %s", code, e)
        return None, None, "정보 없음"


# ---------------------------------------------------------------------------
# 차트 데이터 (FDR — Phase 5에서 KIS로 교체 예정)
# ---------------------------------------------------------------------------
async def get_chart_data_async(code: str, period: str = "3m", interval: str = "daily") -> dict | None:
    """종목 차트 데이터 비동기 래퍼."""
    return await asyncio.to_thread(get_chart_data, code, period, interval)


def get_chart_data(code: str, period: str = "3m", interval: str = "daily") -> dict | None:
    """종목의 차트 데이터를 가져온다 (fdr → yfinance 폴백)."""
    period_map = {"1m": 30, "3m": 90, "6m": 180, "1y": 365}
    days = period_map.get(period, 90)

    df = None
    open_col = high_col = low_col = close_col = vol_col = None

    # 1차: FDR
    try:
        end = datetime.now()
        start = end - timedelta(days=days)
        df_fdr = fdr.DataReader(code, start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))
        if not df_fdr.empty:
            df = df_fdr
            cols = df.columns.tolist()
            open_col  = next((c for c in cols if c in ("Open",  "open",  "시가")), None)
            high_col  = next((c for c in cols if c in ("High",  "high",  "고가")), None)
            low_col   = next((c for c in cols if c in ("Low",   "low",   "저가")), None)
            close_col = next((c for c in cols if c in ("Close", "close", "종가")), None)
            vol_col   = next((c for c in cols if c in ("Volume", "volume", "거래량")), None)
    except Exception as e:
        logger.warning("FDR 차트 조회 실패 [%s]: %s → yfinance 폴백", code, e)

    # 2차: yfinance 폴백 (FDR 실패 또는 빈 결과)
    if df is None or df.empty or close_col is None:
        try:
            import yfinance as yf
            yf_period_map = {"1m": "1mo", "3m": "3mo", "6m": "6mo", "1y": "1y"}
            _, ticker_str = _get_yfinance_ticker(code)
            st = yf.Ticker(ticker_str)
            df_yf = st.history(period=yf_period_map.get(period, "3mo"))
            if not df_yf.empty:
                df = df_yf
                cols = df.columns.tolist()
                open_col  = next((c for c in cols if c in ("Open",  "시가")), None)
                high_col  = next((c for c in cols if c in ("High",  "고가")), None)
                low_col   = next((c for c in cols if c in ("Low",   "저가")), None)
                close_col = next((c for c in cols if c in ("Close", "종가")), None)
                vol_col   = next((c for c in cols if c in ("Volume", "거래량")), None)
                logger.info("yfinance 차트 폴백 사용 [%s]", ticker_str)
        except Exception as e:
            logger.warning("yfinance 차트 폴백 실패 [%s]: %s", code, e)

    # 3차: pykrx 지수 폴백 (KS11/KQ11 등 FDR·yfinance 모두 실패 시)
    if (df is None or df.empty or close_col is None) and _PYKRX_AVAILABLE:
        _INDEX_PYKRX = {"KS11": "1028", "KQ11": "2001"}
        pykrx_idx = _INDEX_PYKRX.get(code)
        if pykrx_idx:
            try:
                from pykrx import stock as pykrx_stock
                _start = datetime.now() - timedelta(days=days)
                df_pkrx = pykrx_stock.get_index_ohlcv_by_date(
                    _start.strftime("%Y%m%d"),
                    datetime.now().strftime("%Y%m%d"),
                    pykrx_idx,
                )
                if not df_pkrx.empty:
                    df = df_pkrx
                    df.index = pd.to_datetime(df.index)
                    cols = df.columns.tolist()
                    open_col  = next((c for c in cols if c in ("시가", "Open")), None)
                    high_col  = next((c for c in cols if c in ("고가", "High")), None)
                    low_col   = next((c for c in cols if c in ("저가", "Low")), None)
                    close_col = next((c for c in cols if c in ("종가", "Close")), None)
                    vol_col   = next((c for c in cols if c in ("거래량", "Volume")), None)
                    logger.info("pykrx 지수 차트 폴백 사용 [%s → %s]", code, pykrx_idx)
            except Exception as e:
                logger.warning("pykrx 지수 차트 폴백 실패 [%s]: %s", code, e)

    # 4차: 직접 HTTP → Yahoo Finance JSON API (KS11/KQ11 전용)
    if (df is None or df.empty or close_col is None) and code in ("KS11", "KQ11"):
        _YF_URL_MAP = {"KS11": "%5EKS11", "KQ11": "%5EKQ11"}
        yf_url_code = _YF_URL_MAP.get(code)
        if yf_url_code:
            try:
                import requests as _requests
                end_ts = int(datetime.now().timestamp())
                start_ts = int((datetime.now() - timedelta(days=days + 10)).timestamp())
                url = (
                    f"https://query1.finance.yahoo.com/v8/finance/chart/{yf_url_code}"
                    f"?period1={start_ts}&period2={end_ts}&interval=1d&events=history"
                )
                resp = _requests.get(
                    url,
                    headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"},
                    timeout=15,
                )
                resp.raise_for_status()
                chart_data = resp.json()["chart"]["result"][0]
                timestamps = chart_data["timestamp"]
                quote = chart_data["indicators"]["quote"][0]
                closes = quote.get("close", [])
                opens = quote.get("open", [None] * len(timestamps))
                highs = quote.get("high", [None] * len(timestamps))
                lows = quote.get("low", [None] * len(timestamps))
                volumes = quote.get("volume", [None] * len(timestamps))
                dates_idx = pd.to_datetime(timestamps, unit="s", utc=True).tz_convert("Asia/Seoul").normalize().tz_localize(None)
                df_http = pd.DataFrame(
                    {"Open": opens, "High": highs, "Low": lows, "Close": closes, "Volume": volumes},
                    index=dates_idx,
                )
                df_http = df_http.dropna(subset=["Close"])
                if not df_http.empty:
                    df = df_http
                    open_col = "Open"
                    high_col = "High"
                    low_col = "Low"
                    close_col = "Close"
                    vol_col = "Volume"
                    logger.info("직접 HTTP Yahoo Finance 폴백 사용 [%s]", code)
            except Exception as e:
                logger.warning("직접 HTTP Yahoo Finance 폴백 실패 [%s]: %s", code, e)

    if df is None or df.empty:
        logger.warning("차트 데이터 비어있음: code=%s period=%s", code, period)
        return None

    if close_col is None:
        logger.error("차트 종가 컬럼 없음: code=%s, cols=%s", code, df.columns.tolist())
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

    # 4. 수급 — get_stock_price_async가 이미 조회한 _investor 재사용 (중복 호출 없음)
    investor = price.get("_investor") or {}
    supply_raw = investor.get("display") or price.get("수급") or "정보 없음"
    market_cap = price.get("market_cap") or investor.get("market_cap")
    supply_pct = investor.get("supply_pct")  # FDR 경로에서 이미 계산됨

    # KIS 경로: inst_net_buy + fore_net_buy로 supply_pct 계산
    if supply_pct is None:
        inst_net = investor.get("inst_net_buy")
        fore_net = investor.get("fore_net_buy")
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
