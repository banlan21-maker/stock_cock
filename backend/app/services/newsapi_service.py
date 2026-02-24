"""NewsAPI.org 해외뉴스 연동 서비스.

키워드별 영문 검색어로 해외 뉴스를 가져오고,
네이버 뉴스와 동일한 NewsArticle 형식으로 변환한다.
영문 제목은 Gemini로 한국어 번역 후 캐싱한다.
"""

import time
import logging
import json
import asyncio
from datetime import datetime

import httpx

from app.config import get_settings
from app.utils.title_cleaner import clean_news_title

logger = logging.getLogger(__name__)

# 키워드 ID → 영문 검색어 매핑
KEYWORD_QUERY_MAP: dict[str, str] = {
    "ai": "AI semiconductor stock market",
    "robot": "robotics automation stock",
    "quantum": "quantum computing investment",
    "superconductor": "superconductor technology stock",
    "bio": "biotech pharma stock market",
    "space": "space aerospace defense stock",
    "smr": "small modular reactor nuclear energy",
    "power_infra": "power grid infrastructure investment",
    "k_defense": "South Korea defense industry",
    "battery_recycle": "battery recycling EV stock",
    "silver_tech": "digital health aging technology stock",
}

DEFAULT_QUERY = "stock market investing"

# 간단한 메모리 캐시 (키워드 → (timestamp, articles))
_cache: dict[str, tuple[float, list[dict]]] = {}
_CACHE_TTL = 300  # 5분

# 번역 캐시 (영문 제목 → 한국어 제목) - 앱 재시작 전까지 유지
_title_cache: dict[str, str] = {}


def _parse_published_at(date_str: str | None) -> str:
    """NewsAPI의 ISO 8601 날짜를 그대로 반환하거나 현재 시각으로 폴백."""
    if date_str:
        return date_str
    return datetime.now().isoformat()


async def _translate_titles_batch(titles: list[str]) -> list[str]:
    """캐시에 없는 영문 제목만 Gemini로 일괄 번역한다. 실패 시 원문 반환."""
    if not titles:
        return titles

    # 캐시에 있는 것은 바로 사용, 없는 것만 번역 대상
    uncached_indices: list[int] = []
    uncached_titles: list[str] = []
    result = list(titles)  # 복사본

    for i, t in enumerate(titles):
        if t in _title_cache:
            result[i] = _title_cache[t]
        else:
            uncached_indices.append(i)
            uncached_titles.append(t)

    if not uncached_titles:
        return result  # 모두 캐시 히트

    # Gemini 번역 (재시도 1회만, 타임아웃 10초)
    try:
        from app.services.gemini_service import _get_model
        model = _get_model()
        prompt = f"""아래 영문 뉴스 제목들을 한국어로 자연스럽게 번역해주세요.
반드시 JSON 배열만 출력하세요. 다른 텍스트 없이.
입력 개수와 동일한 개수의 번역 결과를 같은 순서로 반환하세요.

입력:
{json.dumps(uncached_titles, ensure_ascii=False)}

출력 예시: ["번역된 제목1", "번역된 제목2", ...]"""

        # 10초 타임아웃 적용
        text = await asyncio.wait_for(
            asyncio.get_event_loop().run_in_executor(
                None, lambda: model.generate_content(prompt).text
            ),
            timeout=10.0,
        )
        text = text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0]
        translated = json.loads(text)
        if isinstance(translated, list) and len(translated) == len(uncached_titles):
            for idx, kr_title in zip(uncached_indices, translated):
                result[idx] = kr_title
                _title_cache[titles[idx]] = kr_title  # 캐시 저장
            return result
    except asyncio.TimeoutError:
        logger.warning("제목 번역 타임아웃(10초), 원문 사용")
    except Exception as e:
        logger.warning("제목 번역 실패, 원문 사용: %s", str(e)[:100])

    return result


async def search_news(query: str, page_size: int = 5) -> list[dict]:
    """NewsAPI.org /v2/everything 엔드포인트를 호출하여 기사 목록을 반환한다.
    제목 번역은 하지 않음 - fetch_news_by_keywords에서 일괄 처리.
    """
    settings = get_settings()
    if not settings.news_api_key:
        logger.warning("NewsAPI 키가 설정되지 않았습니다.")
        return []

    headers = {"X-Api-Key": settings.news_api_key}
    params = {
        "q": query,
        "pageSize": page_size,
        "sortBy": "publishedAt",
        "language": "en",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                "https://newsapi.org/v2/everything",
                headers=headers,
                params=params,
            )
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        logger.error("NewsAPI 호출 실패: %s", e)
        return []

    articles = []
    for item in data.get("articles", []):
        url = item.get("url", "")
        articles.append({
            "id": url,
            "title": clean_news_title(item.get("title", "")),
            "source": (item.get("source") or {}).get("name", "Unknown"),
            "url": url,
            "published_at": _parse_published_at(item.get("publishedAt")),
            "category": "global",
            "tags": [],
            "content": item.get("description") or item.get("content") or "",
        })
    return articles


async def _translate_article_titles(articles: list[dict]) -> list[dict]:
    """기사 목록의 영문 제목을 한국어로 일괄 번역한다."""
    if not articles:
        return articles
    en_titles = [a["title"] for a in articles]
    kr_titles = await _translate_titles_batch(en_titles)
    for a, kr in zip(articles, kr_titles):
        a["title"] = kr
    return articles


async def fetch_news_by_keywords(keyword_ids: list[str]) -> list[dict]:
    """키워드 ID 목록에 대해 NewsAPI 뉴스를 검색하고 병합하여 반환한다."""
    cache_key = "global:" + ",".join(sorted(keyword_ids))
    now = time.time()

    if cache_key in _cache:
        cached_time, cached_articles = _cache[cache_key]
        if now - cached_time < _CACHE_TTL:
            return cached_articles

    all_articles: list[dict] = []
    for kid in keyword_ids:
        query = KEYWORD_QUERY_MAP.get(kid)
        if not query:
            continue
        articles = await search_news(query, page_size=5)
        for a in articles:
            a["tags"] = [kid]
        all_articles.extend(articles)

    # 전체 기사를 모은 후 한번에 일괄 번역 (Gemini 1회 호출)
    all_articles = await _translate_article_titles(all_articles)

    all_articles.sort(key=lambda a: a.get("published_at", ""), reverse=True)
    _cache[cache_key] = (now, all_articles)
    return all_articles


async def fetch_default_news() -> list[dict]:
    """키워드 없이 기본 해외 주식 뉴스를 가져온다."""
    cache_key = "__global_default__"
    now = time.time()

    if cache_key in _cache:
        cached_time, cached_articles = _cache[cache_key]
        if now - cached_time < _CACHE_TTL:
            return cached_articles

    articles = await search_news(DEFAULT_QUERY, page_size=10)
    # 일괄 번역
    articles = await _translate_article_titles(articles)

    _cache[cache_key] = (now, articles)
    return articles
