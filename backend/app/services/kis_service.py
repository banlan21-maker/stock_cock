"""한국투자증권(KIS) OpenAPI 클라이언트.

- Access Token을 Supabase kis_token 테이블에 저장해 재사용 (하루 1회 발급)
- 만료 30분 전 자동 갱신
- Rate Limit: asyncio.Semaphore(15) + 50ms 딜레이 (초당 20건 제한 대응)

환경 변수 (backend/.env):
    KIS_APP_KEY    : 앱키
    KIS_APP_SECRET : 앱시크릿
    KIS_MOCK       : true면 모의투자 환경 (기본 false)

Supabase 테이블 (사전 생성 필요):
    CREATE TABLE kis_token (
        id           int PRIMARY KEY DEFAULT 1,
        access_token text NOT NULL,
        expires_at   timestamptz NOT NULL,
        updated_at   timestamptz DEFAULT now()
    );
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta

import httpx

from app.config import get_settings
from app.utils.supabase_client import get_supabase

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 상수
# ---------------------------------------------------------------------------
_KIS_REAL_BASE = "https://openapi.koreainvestment.com:9443"
_KIS_MOCK_BASE = "https://openapivts.koreainvestment.com:29443"

# Rate Limit 제어: 초당 20건 → 15건으로 안전 마진, 요청 간 50ms 간격
_SEMAPHORE = asyncio.Semaphore(15)
_REQUEST_DELAY = 0.05


# ---------------------------------------------------------------------------
# 내부 헬퍼
# ---------------------------------------------------------------------------
def _base_url() -> str:
    return _KIS_MOCK_BASE if get_settings().kis_mock else _KIS_REAL_BASE


def _check_credentials() -> None:
    s = get_settings()
    if not s.kis_app_key or not s.kis_app_secret:
        raise ValueError(
            "KIS_APP_KEY 또는 KIS_APP_SECRET이 설정되지 않았습니다. "
            "backend/.env에 추가하세요."
        )


def _to_float(v, default=None):
    """문자열 → float 변환. 빈값·0.0은 default로 처리 (KIS는 데이터 없을 때 '0.00' 반환)."""
    if v is None or v == "":
        return default
    try:
        f = float(v)
        return f if f != 0.0 else default
    except (ValueError, TypeError):
        return default


def _to_price(v, default=0.0):
    """현재가·거래량 등 0이 유효한 숫자 필드용 변환."""
    if v is None or v == "":
        return default
    try:
        return float(v)
    except (ValueError, TypeError):
        return default


# ---------------------------------------------------------------------------
# 토큰 관리 (동기 DB 헬퍼 + 비동기 퍼블릭 함수)
# ---------------------------------------------------------------------------
def _get_stored_token() -> tuple[str, datetime] | None:
    """Supabase kis_token 테이블에서 저장된 토큰을 조회한다 (동기)."""
    try:
        supabase = get_supabase()
        r = (
            supabase.table("kis_token")
            .select("access_token, expires_at")
            .eq("id", 1)
            .execute()
        )
        if r.data:
            row = r.data[0]
            expires_str = row["expires_at"].replace("Z", "+00:00")
            expires_at = datetime.fromisoformat(expires_str)
            # timezone-naive면 UTC로 간주
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            return row["access_token"], expires_at
        return None
    except Exception as e:
        logger.warning("KIS 토큰 DB 조회 실패: %s", e)
        return None


def _save_token(token: str, expires_at: datetime) -> None:
    """Supabase kis_token 테이블에 토큰을 저장/갱신한다 (동기)."""
    try:
        supabase = get_supabase()
        supabase.table("kis_token").upsert(
            {
                "id": 1,
                "access_token": token,
                "expires_at": expires_at.isoformat(),
            },
            on_conflict="id",
        ).execute()
    except Exception as e:
        logger.warning("KIS 토큰 DB 저장 실패: %s", e)


async def _issue_token() -> tuple[str, datetime]:
    """KIS API에서 신규 Access Token을 발급받는다."""
    _check_credentials()
    s = get_settings()
    url = f"{_base_url()}/oauth2/tokenP"
    payload = {
        "grant_type": "client_credentials",
        "appkey": s.kis_app_key,
        "appsecret": s.kis_app_secret,
    }
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()

    token = data["access_token"]
    expires_in = int(data.get("expires_in", 86400))
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
    return token, expires_at


async def get_token() -> str:
    """유효한 Access Token을 반환한다.

    Supabase에 저장된 토큰이 있고 만료 30분 이상 남아있으면 재사용.
    없거나 곧 만료되면 KIS에서 새로 발급 후 Supabase에 저장.
    """
    now = datetime.now(timezone.utc)
    renewal_threshold = now + timedelta(minutes=30)

    stored = await asyncio.to_thread(_get_stored_token)
    if stored:
        token, expires_at = stored
        if expires_at > renewal_threshold:
            return token

    logger.info("KIS 토큰 발급/갱신 시작")
    token, expires_at = await _issue_token()
    await asyncio.to_thread(_save_token, token, expires_at)
    logger.info("KIS 토큰 갱신 완료 (만료: %s)", expires_at.strftime("%Y-%m-%d %H:%M UTC"))
    return token


# ---------------------------------------------------------------------------
# 공통 GET 요청
# ---------------------------------------------------------------------------
async def _kis_get(path: str, tr_id: str, params: dict[str, str]) -> dict:
    """KIS API GET 요청 (Rate Limit + 인증 헤더 자동 처리)."""
    async with _SEMAPHORE:
        await asyncio.sleep(_REQUEST_DELAY)
        token = await get_token()
        s = get_settings()
        headers = {
            "authorization": f"Bearer {token}",
            "appkey": s.kis_app_key,
            "appsecret": s.kis_app_secret,
            "tr_id": tr_id,
            "custtype": "P",
            "Content-Type": "application/json; charset=utf-8",
        }
        url = f"{_base_url()}{path}"
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, headers=headers, params=params)
            resp.raise_for_status()
            return resp.json()


# ---------------------------------------------------------------------------
# 현재가 + 재무 지표 (PBR/PER/EPS/BPS)
# ---------------------------------------------------------------------------
async def get_price(code: str) -> dict | None:
    """종목 현재가와 재무 지표를 반환한다.

    KIS /inquire-price 단일 호출로 현재가 + PBR/PER/EPS/BPS를 모두 가져온다.

    Returns:
        {
            code, current_price, change, change_rate,
            volume, high, low,
            per, pbr, eps, bps   ← 데이터 없으면 None
        }
        API 실패 시 None.
    """
    try:
        data = await _kis_get(
            "/uapi/domestic-stock/v1/quotations/inquire-price",
            "FHKST01010100",
            {"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": code},
        )
        out = data.get("output", {})
        if not out:
            logger.warning("KIS 현재가 빈 응답: code=%s, rt_cd=%s", code, data.get("rt_cd"))
            return None

        # hts_avls: 시가총액 (KIS 반환 단위 = 억원 → 원으로 변환)
        try:
            hts_avls = out.get("hts_avls")
            market_cap = int(float(hts_avls) * 1e8) if hts_avls and float(hts_avls) > 0 else None
        except (ValueError, TypeError):
            market_cap = None

        return {
            "code": code,
            "current_price": _to_price(out.get("stck_prpr")),
            "change": _to_price(out.get("prdy_vrss")),
            "change_rate": _to_price(out.get("prdy_ctrt")),
            "volume": int(_to_price(out.get("acml_vol"), 0)),
            "high": _to_price(out.get("stck_hgpr")),
            "low": _to_price(out.get("stck_lwpr")),
            "market_cap": market_cap,
            # 재무 지표: 0.00 = 데이터 없음 → None 처리
            "per": _to_float(out.get("per")),
            "pbr": _to_float(out.get("pbr")),
            "eps": _to_float(out.get("eps")),
            "bps": _to_float(out.get("bps")),
        }
    except Exception as e:
        logger.warning("KIS get_price 실패 [%s]: %s", code, e)
        return None


# ---------------------------------------------------------------------------
# 수급 (기관/외국인 최근 10일 순매수)
# ---------------------------------------------------------------------------
async def get_investor(code: str) -> dict:
    """기관·외국인 최근 10일 순매수 거래대금을 반환한다.

    Returns:
        {
            inst_net_buy: 기관 순매수 합계 (원, 음수=순매도),
            fore_net_buy: 외국인 순매수 합계 (원),
            supply_pct:   시가총액 대비 순매수 비율 (%, None이면 계산 불가),
            display:      "기관 +XXXX억, 외국인 -XXXX억 (최근 10일)"
        }
    """
    try:
        today = datetime.now().strftime("%Y%m%d")
        data = await _kis_get(
            "/uapi/domestic-stock/v1/quotations/inquire-investor",
            "FHKST01010900",
            {
                "FID_COND_MRKT_DIV_CODE": "J",
                "FID_INPUT_ISCD": code,
                "FID_INPUT_DATE_1": today,
            },
        )

        # output2: 일자별 투자자 데이터 배열
        rows = data.get("output2") or []

        inst_total = 0
        fore_total = 0
        for row in rows[:10]:  # 최근 10 거래일
            try:
                inst_total += int(row.get("orgn_ntby_tr_pbmn") or 0)
                fore_total += int(row.get("frgn_ntby_tr_pbmn") or 0)
            except (ValueError, TypeError):
                continue

        display = (
            f"기관 {int(inst_total / 1e8):+,}억, "
            f"외국인 {int(fore_total / 1e8):+,}억 (최근 10일)"
        )

        # 시가총액 대비 비율: 현재가 조회 결과의 시가총액이 없으면 None
        # (호출 측에서 시가총액 전달 시 계산 가능하도록 raw 값도 노출)
        return {
            "inst_net_buy": inst_total,
            "fore_net_buy": fore_total,
            "supply_pct": None,  # 시가총액 필요 → stock_service에서 계산
            "display": display,
        }
    except Exception as e:
        logger.warning("KIS get_investor 실패 [%s]: %s", code, e)
        return {
            "inst_net_buy": None,
            "fore_net_buy": None,
            "supply_pct": None,
            "display": "정보 없음",
        }


# ---------------------------------------------------------------------------
# 다중 종목 현재가 (포트폴리오 / 종목비교용)
# ---------------------------------------------------------------------------
async def get_prices_bulk(codes: list[str]) -> dict[str, dict]:
    """여러 종목의 현재가를 Rate Limit을 지키며 병렬로 조회한다.

    Semaphore로 동시 요청 수를 제한하므로 외부에서 추가 제어 불필요.

    Returns:
        {code: get_price 결과 or None}
    """
    tasks = [get_price(code) for code in codes]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return {
        code: (None if isinstance(r, Exception) else r)
        for code, r in zip(codes, results)
    }
