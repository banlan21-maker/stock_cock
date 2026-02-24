"""DART 전자공시 서비스.

OpenDartReader를 활용해 공시 목록·내용을 수집하고 Gemini AI 분석과 연계한다.
캐싱은 generic_kv_cache 테이블을 재사용한다.

환경 변수:
    DART_API_KEY: DART 전자공시 API 키 (https://opendart.fss.or.kr 에서 발급)
"""
import asyncio
import json
import logging
from datetime import datetime, timedelta

from app.config import get_settings
from app.services.generic_cache_service import get_generic_cache, set_generic_cache

logger = logging.getLogger(__name__)

_dart_instance = None


def _get_dart():
    """OpenDartReader 싱글턴 인스턴스 반환."""
    global _dart_instance
    if _dart_instance is not None:
        return _dart_instance
    try:
        import OpenDartReader  # noqa: F401 (설치 확인용)
        settings = get_settings()
        api_key = (settings.dart_api_key or "").strip()
        if not api_key:
            raise ValueError(
                "DART_API_KEY가 설정되지 않았습니다. backend/.env에 DART_API_KEY를 추가하세요."
            )
        # `import OpenDartReader`는 클래스 자체를 임포트함 (모듈이 아님)
        _dart_instance = OpenDartReader(api_key)
        return _dart_instance
    except ImportError:
        raise ValueError(
            "OpenDartReader 패키지가 필요합니다. "
            "pip install OpenDartReader 실행 후 서버를 재시작하세요."
        )


def _row_to_dict(row) -> dict:
    """DataFrame 행을 공시 dict로 변환."""
    return {
        "rcp_no": str(row.get("rcept_no", "")),
        "corp_name": row.get("corp_name", ""),
        "stock_code": str(row.get("stock_code", "") or ""),
        "report_nm": row.get("report_nm", ""),
        "rcept_dt": str(row.get("rcept_dt", "")),
        "flr_nm": row.get("flr_nm", ""),
        "rm": row.get("rm", ""),
    }


async def get_disclosure_list(stock_code: str, days: int = 30) -> list[dict]:
    """특정 종목의 최근 공시 목록을 반환한다 (당일 기준, 1시간 캐시)."""
    today_str = datetime.now().strftime("%Y%m%d")
    cache_key = f"dart:list:{stock_code}:{days}:{today_str}"
    cached = await asyncio.to_thread(get_generic_cache, cache_key)
    if cached is not None:
        return cached

    try:
        dart = _get_dart()
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        df = await asyncio.to_thread(
            dart.list,
            stock_code,
            start=start_date.strftime("%Y%m%d"),
            end=end_date.strftime("%Y%m%d"),
            kind="",
            final="T",
        )

        if df is None or (hasattr(df, "empty") and df.empty):
            result: list[dict] = []
        else:
            result = [_row_to_dict(row) for _, row in df.head(20).iterrows()]

        await asyncio.to_thread(set_generic_cache, cache_key, result, 3600)
        return result

    except ValueError:
        raise
    except Exception as e:
        logger.warning("DART 공시 목록 조회 실패 [%s]: %s", stock_code, e)
        raise


async def get_today_disclosures(max_items: int = 30) -> list[dict]:
    """오늘 발표된 주요 공시 목록을 반환한다 (전체 상장사, 30분 캐시).

    정기공시(A)와 주요사항보고(B, 유상증자·합병 등)를 수집한다.
    """
    today = datetime.now().strftime("%Y%m%d")
    cache_key = f"dart:today:{today}"
    cached = await asyncio.to_thread(get_generic_cache, cache_key)
    if cached is not None:
        return cached

    try:
        dart = _get_dart()
        result: list[dict] = []

        for kind in ["A", "B"]:
            df = await asyncio.to_thread(
                dart.list,
                None,       # 전체 종목
                start=today,
                end=today,
                kind=kind,
                final="T",
            )
            if df is not None and not (hasattr(df, "empty") and df.empty):
                for _, row in df.iterrows():
                    if row.get("stock_code"):   # 상장사만 포함
                        result.append(_row_to_dict(row))
                    if len(result) >= max_items:
                        break
            if len(result) >= max_items:
                break

        result = result[:max_items]
        await asyncio.to_thread(set_generic_cache, cache_key, result, 1800)  # 30분
        return result

    except ValueError:
        raise
    except Exception as e:
        logger.warning("DART 오늘 공시 조회 실패: %s", e)
        raise


async def get_disclosure_analysis(rcp_no: str, report_nm: str = "", corp_name: str = "") -> dict:
    """공시 번호로 본문을 추출하고 꼰대아저씨 AI 분석 결과를 반환한다 (24시간 캐시)."""
    cache_key = f"dart:analysis:{rcp_no}"
    cached = await asyncio.to_thread(get_generic_cache, cache_key)
    if cached is not None:
        return cached

    from app.services import gemini_service  # 순환 import 방지

    try:
        dart = _get_dart()
        text_content = ""

        try:
            # dart.document(rcp_no)로 전체 XML 문서를 받아 BeautifulSoup으로 텍스트 추출
            xml_doc = await asyncio.to_thread(dart.document, rcp_no)
            if xml_doc:
                from bs4 import BeautifulSoup
                import warnings
                warnings.filterwarnings("ignore", category=UserWarning)
                soup = BeautifulSoup(xml_doc, "lxml")
                raw_text = soup.get_text(separator=" ", strip=True)
                if raw_text:
                    text_content = raw_text[:4000]
        except Exception as e:
            logger.warning("공시 본문 추출 실패 [%s]: %s", rcp_no, e)

        if not text_content:
            text_content = (
                f"공시명: {report_nm}\n기업명: {corp_name}\n"
                f"(공시 본문을 직접 가져올 수 없어 공시명만으로 분석합니다.)"
            )

        raw = await gemini_service.analyze_disclosure(
            rcp_no=rcp_no,
            report_nm=report_nm,
            corp_name=corp_name,
            content=text_content,
        )
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0]

        result = json.loads(cleaned)
        result["rcp_no"] = rcp_no

        await asyncio.to_thread(set_generic_cache, cache_key, result, 86400)  # 24h
        return result

    except ValueError:
        raise
    except Exception as e:
        logger.warning("DART 공시 분석 실패 [%s]: %s", rcp_no, e)
        raise
