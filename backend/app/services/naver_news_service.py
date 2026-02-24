"""네이버 뉴스 검색 API 연동 서비스."""

import re
import time
import logging
from datetime import datetime

import httpx

from app.config import get_settings
from app.utils.title_cleaner import clean_news_title

logger = logging.getLogger(__name__)

# 키워드 ID → 네이버 검색어 매핑
KEYWORD_QUERY_MAP: dict[str, str] = {
    "ai": "AI 관련주",
    "robot": "로봇 관련주",
    "quantum": "양자컴퓨터 관련주",
    "superconductor": "초전도체 관련주",
    "bio": "바이오 관련주",
    "space": "우주항공 관련주",
    "smr": "SMR 소형원전 관련주",
    "power_infra": "전력인프라 관련주",
    "k_defense": "K방산 관련주",
    "battery_recycle": "폐배터리 재활용 관련주",
    "silver_tech": "디지털헬스케어 관련주",
}

DEFAULT_QUERY = "주식 시장 뉴스"

# 간단한 메모리 캐시 (키워드 → (timestamp, articles))
_cache: dict[str, tuple[float, list[dict]]] = {}
_CACHE_TTL = 300  # 5분

_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(text: str) -> str:
    return _TAG_RE.sub("", text)


def _parse_pub_date(date_str: str) -> str:
    """네이버 API의 RFC 2822 날짜를 ISO 형식으로 변환."""
    try:
        from email.utils import parsedate_to_datetime
        dt = parsedate_to_datetime(date_str)
        return dt.isoformat()
    except Exception:
        return datetime.now().isoformat()


async def search_news(query: str, display: int = 5) -> list[dict]:
    """네이버 뉴스 검색 API를 호출하여 기사 목록을 반환한다."""
    settings = get_settings()
    if not settings.naver_client_id or not settings.naver_client_secret:
        logger.warning("네이버 API 키가 설정되지 않았습니다.")
        return []

    headers = {
        "X-Naver-Client-Id": settings.naver_client_id,
        "X-Naver-Client-Secret": settings.naver_client_secret,
    }
    params = {
        "query": query,
        "display": display,
        "sort": "date",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                "https://openapi.naver.com/v1/search/news.json",
                headers=headers,
                params=params,
            )
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        logger.error("네이버 뉴스 API 호출 실패: %s", e)
        return []

    articles = []
    for item in data.get("items", []):
        articles.append({
            "id": item.get("link", ""),
            "title": clean_news_title(_strip_html(item.get("title", ""))),
            "source": _strip_html(item.get("originallink", item.get("link", ""))),
            "url": item.get("link", ""),
            "published_at": _parse_pub_date(item.get("pubDate", "")),
            "category": "domestic",
            "tags": [],
            "content": _strip_html(item.get("description", "")),
        })
    return articles


async def fetch_news_by_keywords(keyword_ids: list[str]) -> list[dict]:
    """키워드 ID 목록에 대해 네이버 뉴스를 검색하고 병합하여 반환한다."""
    cache_key = ",".join(sorted(keyword_ids))
    now = time.time()

    # 캐시 확인
    if cache_key in _cache:
        cached_time, cached_articles = _cache[cache_key]
        if now - cached_time < _CACHE_TTL:
            return cached_articles

    all_articles: list[dict] = []
    for kid in keyword_ids:
        query = KEYWORD_QUERY_MAP.get(kid)
        if not query:
            continue
        articles = await search_news(query, display=5)
        # 태그 부여
        for a in articles:
            a["tags"] = [kid]
        all_articles.extend(articles)

    # 날짜 역순 정렬
    all_articles.sort(key=lambda a: a.get("published_at", ""), reverse=True)

    # 캐시 저장
    _cache[cache_key] = (now, all_articles)
    return all_articles


async def fetch_default_news() -> list[dict]:
    """키워드 없이 기본 주식 뉴스를 가져온다."""
    cache_key = "__default__"
    now = time.time()

    if cache_key in _cache:
        cached_time, cached_articles = _cache[cache_key]
        if now - cached_time < _CACHE_TTL:
            return cached_articles

    articles = await search_news(DEFAULT_QUERY, display=10)
    _cache[cache_key] = (now, articles)
    return articles
