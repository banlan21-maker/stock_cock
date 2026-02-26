"""뉴스 수집 서비스.

네이버 뉴스 검색 API(국내) + NewsAPI.org(해외)를 사용하여
키워드 기반 뉴스를 제공한다. API 호출 실패 시 샘플 데이터로 폴백한다.

[데이터 신선도] Asia/Seoul 기준 타임윈도우, 중복 제거, 가짜/광고 차단 적용.
"""

import asyncio
import uuid
import logging
import json
from datetime import datetime, timedelta

from app.services import gemini_service
from app.services import naver_news_service
from app.services import newsapi_service
from app.services import news_cache_db
from app.utils.freshness import is_within_time_window
from app.utils.news_filter import should_skip_article, deduplicate_by_similarity, sort_by_priority

logger = logging.getLogger(__name__)


def _apply_freshness_pipeline(articles: list[dict], max_hours: int = 24) -> list[dict]:
    """타임윈도우 필터 → 가짜/광고 차단 → 중복 제거."""
    if max_hours == 24:
        filtered = [a for a in articles if is_within_time_window(a.get("published_at"))]
    else:
        # 커스텀 시간 윈도우 (해외뉴스 등)
        from datetime import timezone
        from zoneinfo import ZoneInfo
        cutoff = datetime.now(ZoneInfo("Asia/Seoul")) - timedelta(hours=max_hours)
        filtered = []
        for a in articles:
            pa = a.get("published_at")
            if not pa:
                continue
            try:
                dt = datetime.fromisoformat(pa.replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                if dt >= cutoff:
                    filtered.append(a)
            except Exception:
                pass
    filtered = [a for a in filtered if not should_skip_article(
        a.get("title", ""), a.get("content", a.get("description", ""))
    )]
    return deduplicate_by_similarity(filtered, threshold=0.8)


# 관심 키워드 태그: ai, robot, quantum, superconductor, bio, space, smr, power_infra, k_defense, battery_recycle, silver_tech
# 폴백용 샘플 뉴스 데이터
SAMPLE_NEWS = [
    {
        "id": str(uuid.uuid4()),
        "title": "美 연준, 금리 인하 시사... 글로벌 증시 상승",
        "source": "Reuters",
        "url": "https://example.com/news/1",
        "published_at": (datetime.now() - timedelta(hours=2)).isoformat(),
        "category": "global",
        "tags": [],
        "content": "미국 연방준비제도(Fed)가 올해 하반기 금리 인하를 시사했다. 이에 따라 글로벌 증시가 일제히 상승세를 보이고 있으며, 특히 기술주와 성장주가 강세를 보이고 있다. 시장 전문가들은 금리 인하가 현실화될 경우 한국 수출 기업들의 수혜가 예상된다고 분석했다.",
    },
    {
        "id": str(uuid.uuid4()),
        "title": "중국 경기부양책 발표, 아시아 시장 반등",
        "source": "Bloomberg",
        "url": "https://example.com/news/2",
        "published_at": (datetime.now() - timedelta(hours=5)).isoformat(),
        "category": "global",
        "tags": [],
        "content": "중국 정부가 대규모 경기부양책을 발표하면서 아시아 증시가 일제히 반등했다. 부동산 규제 완화와 소비 진작 정책이 포함되어 있으며, 한국의 중국 관련 수출주들이 수혜를 받을 것으로 전망된다.",
    },
    {
        "id": str(uuid.uuid4()),
        "title": "AI 반도체 수요 폭증, 삼성·SK 수혜 전망",
        "source": "한국경제",
        "url": "https://example.com/news/3",
        "published_at": (datetime.now() - timedelta(hours=8)).isoformat(),
        "category": "domestic",
        "tags": ["ai"],
        "content": "글로벌 AI 열풍으로 반도체 수요가 폭증하면서 삼성전자와 SK하이닉스의 HBM(고대역폭메모리) 수주가 크게 늘어나고 있다. 전문가들은 AI 반도체 시장이 2027년까지 연평균 30% 이상 성장할 것으로 전망했다.",
    },
    {
        "id": str(uuid.uuid4()),
        "title": "유럽 탄소국경세 본격 시행, 철강·화학업계 영향",
        "source": "Financial Times",
        "url": "https://example.com/news/4",
        "published_at": (datetime.now() - timedelta(hours=12)).isoformat(),
        "category": "global",
        "tags": ["battery_recycle"],
        "content": "유럽연합(EU)의 탄소국경조정메커니즘(CBAM)이 본격 시행되면서 한국 철강 및 화학 업계에 영향이 예상된다. 친환경 공정 전환에 투자한 기업은 수혜, 그렇지 못한 기업은 비용 증가가 불가피하다.",
    },
    {
        "id": str(uuid.uuid4()),
        "title": "정부, 2차전지 산업 육성 5개년 계획 발표",
        "source": "연합뉴스",
        "url": "https://example.com/news/5",
        "published_at": (datetime.now() - timedelta(hours=15)).isoformat(),
        "category": "policy",
        "tags": ["battery_recycle"],
        "content": "정부가 2차전지 산업 육성을 위한 5개년 종합계획을 발표했다. 총 10조원 규모의 R&D 투자와 세제 혜택이 포함되어 있으며, LG에너지솔루션, 삼성SDI, SK이노베이션 등 국내 배터리 3사의 수혜가 예상된다.",
    },
    {
        "id": str(uuid.uuid4()),
        "title": "산업로봇 수출 3년 연속 최대, 자동화 확대 전망",
        "source": "매일경제",
        "url": "https://example.com/news/6",
        "published_at": (datetime.now() - timedelta(hours=1)).isoformat(),
        "category": "domestic",
        "tags": ["robot"],
        "content": "국내 산업용 로봇 수출이 3년 연속 사상 최대를 기록했다. 전기차·2차전지 공정 확대에 따른 자동화 수요가 주된 원인으로 꼽힌다.",
    },
    {
        "id": str(uuid.uuid4()),
        "title": "원자력 SMR 건설 본격화, 소형원전 수주 경쟁",
        "source": "한국경제",
        "url": "https://example.com/news/7",
        "published_at": (datetime.now() - timedelta(hours=4)).isoformat(),
        "category": "domestic",
        "tags": ["smr"],
        "content": "소형 모듈 원자로(SMR) 건설이 본격화되며 국내 원자력 기업들의 수주 경쟁이 치열해지고 있다. 정부의 원전 수출 지원 정책과 맞물려 성장이 기대된다.",
    },
    {
        "id": str(uuid.uuid4()),
        "title": "전력망 투자 확대, 변압기·구리 수요 급증",
        "source": "연합뉴스",
        "url": "https://example.com/news/8",
        "published_at": (datetime.now() - timedelta(hours=6)).isoformat(),
        "category": "policy",
        "tags": ["power_infra"],
        "content": "정부와 한전의 전력 인프라 투자가 확대되면서 변압기, 구리 케이블 등 관련 기자재 수요가 급증하고 있다.",
    },
    {
        "id": str(uuid.uuid4()),
        "title": "방산 수출 3년 연속 100억불, K-방산 주목",
        "source": "조선비즈",
        "url": "https://example.com/news/9",
        "published_at": (datetime.now() - timedelta(hours=10)).isoformat(),
        "category": "domestic",
        "tags": ["k_defense"],
        "content": "국가 방위산업 수출이 3년 연속 100억 달러를 돌파했다. K-방산 브랜드가 글로벌 시장에서 인정받고 있다.",
    },
    {
        "id": str(uuid.uuid4()),
        "title": "디지털 헬스케어·안티에이징 시장 연 15% 성장",
        "source": "헬스조선",
        "url": "https://example.com/news/10",
        "published_at": (datetime.now() - timedelta(hours=3)).isoformat(),
        "category": "domestic",
        "tags": ["silver_tech"],
        "content": "실버 테크와 디지털 헬스케어 시장이 연평균 15% 성장 중이다. 안티에이징·원격의료 관련 기업에 투자 관심이 쏠린다.",
    },
]


async def get_news_list(
    category: str = "all",
    page: int = 1,
    limit: int = 10,
    keywords: str | None = None,
) -> dict:
    """뉴스 목록을 반환한다. 네이버(국내) + NewsAPI(해외)를 병렬 호출하여 병합한다."""
    articles: list[dict] = []

    if keywords:
        keyword_list = [k.strip().lower() for k in keywords.split(",") if k.strip()]
        if keyword_list:
            # 국내 + 해외 병렬 호출
            naver_task = naver_news_service.fetch_news_by_keywords(keyword_list)
            global_task = newsapi_service.fetch_news_by_keywords(keyword_list)
            try:
                naver_results, global_results = await asyncio.gather(
                    naver_task, global_task, return_exceptions=True,
                )
            except Exception as e:
                logger.warning("뉴스 병렬 조회 실패: %s", e)
                naver_results, global_results = [], []

            if isinstance(naver_results, Exception):
                logger.warning("네이버 뉴스 조회 실패: %s", naver_results)
                naver_results = []
            if isinstance(global_results, Exception):
                logger.warning("NewsAPI 조회 실패: %s", global_results)
                global_results = []

            articles = list(naver_results) + list(global_results)

            # 타임윈도우·광고 차단·중복 제거·우선순위
            articles = _apply_freshness_pipeline(articles)

            # 폴백: API 결과가 없으면 SAMPLE_NEWS에서 필터링
            if not articles:
                want = set(keyword_list)
                articles = _apply_freshness_pipeline([
                    n for n in SAMPLE_NEWS if want & set(n.get("tags") or [])
                ])
    else:
        # 국내 + 해외 기본 뉴스 병렬 호출
        naver_task = naver_news_service.fetch_default_news()
        global_task = newsapi_service.fetch_default_news()
        try:
            naver_results, global_results = await asyncio.gather(
                naver_task, global_task, return_exceptions=True,
            )
        except Exception as e:
            logger.warning("기본 뉴스 병렬 조회 실패: %s", e)
            naver_results, global_results = [], []

        if isinstance(naver_results, Exception):
            logger.warning("네이버 기본 뉴스 조회 실패: %s", naver_results)
            naver_results = []
        if isinstance(global_results, Exception):
            logger.warning("NewsAPI 기본 뉴스 조회 실패: %s", global_results)
            global_results = []

        # 국내/해외 별도 신선도 적용 (해외는 72시간으로 완화)
        domestic = _apply_freshness_pipeline(list(naver_results), max_hours=24)
        global_articles = _apply_freshness_pipeline(list(global_results), max_hours=72)
        articles = domestic + global_articles

        if not articles:
            articles = SAMPLE_NEWS

    # 우선순위 정렬 (정책 > 해외 주요 > 국내) + 동일 그룹 내 최신순
    articles = sort_by_priority(articles)

    # 카테고리 필터 (정책은 정책돋보기 전용이므로 뉴스 목록에서 제외)
    if category == "all":
        articles = [n for n in articles if n.get("category") != "policy"]
    else:
        articles = [n for n in articles if n.get("category") == category]

    # 카테고리 필터 후 결과 없으면 샘플에서 폴백
    if not articles:
        fallback = [n for n in SAMPLE_NEWS if n.get("category") != "policy"] if category == "all" else [n for n in SAMPLE_NEWS if n.get("category") == category]
        articles = fallback

    total = len(articles)
    start = (page - 1) * limit
    end = start + limit
    items = []
    for n in articles[start:end]:
        items.append({
            "id": n["id"],
            "title": n["title"],
            "source": n["source"],
            "url": n["url"],
            "published_at": n["published_at"],
            "category": n.get("category", "news"),
            "ai_summary": None,
            "related_stocks": [],
        })

    return {"items": items, "total": total, "page": page, "limit": limit}


def get_news_by_id(news_id: str) -> dict | None:
    """ID로 뉴스를 찾는다. 샘플, 네이버 캐시, NewsAPI 캐시에서 검색한다."""
    # 샘플 뉴스에서 검색
    for n in SAMPLE_NEWS:
        if n["id"] == news_id:
            return n

    # 네이버 뉴스 캐시에서 검색 (ID = URL)
    for _key, (_ts, cached_articles) in naver_news_service._cache.items():
        for a in cached_articles:
            if a["id"] == news_id or a["url"] == news_id:
                return a

    # NewsAPI 캐시에서 검색
    for _key, (_ts, cached_articles) in newsapi_service._cache.items():
        for a in cached_articles:
            if a["id"] == news_id or a["url"] == news_id:
                return a

    return None


async def get_news_summary(news_id: str) -> dict | None:
    """뉴스 AI 요약을 생성한다. 캐시 우선 조회, 없으면 Gemini 호출 후 캐시 저장."""
    news = get_news_by_id(news_id)
    if not news:
        return None

    # 가짜/광고성 기사는 AI 분석 생략
    if should_skip_article(news.get("title", ""), news.get("content", news.get("description", ""))):
        return {
            "id": news["id"],
            "title": news["title"],
            "url": news.get("url"),
            "ai_summary": "해당 기사는 [포토]/[인사]/[부고] 또는 광고성 기사로 분류되어 AI 분석을 제공하지 않습니다.",
            "related_stocks": [],
        }

    # 캐시 우선 조회 (Gemini 호출 절감)
    cached = news_cache_db.get_cached_summary(news_id)
    if cached:
        return cached

    try:
        # 해외뉴스이면 번역+요약, 국내뉴스이면 기존 요약
        if news.get("category") == "global":
            raw = await gemini_service.translate_and_summarize_news(
                news["title"], news["content"],
            )
        else:
            raw = await gemini_service.summarize_news(
                news["title"], news["content"],
            )

        # JSON 파싱 시도
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0]
        parsed = json.loads(cleaned)

        impact = (parsed.get("impact_strength") or "보통").strip()
        result = {
            "id": news["id"],
            "title": news["title"],
            "url": news.get("url"),
            "ai_summary": parsed.get("summary", ""),
            "related_stocks": parsed.get("related_stocks", []),
            "impact_strength": impact,
        }

        # 캐시 저장 (다음 요청 시 Gemini 호출 생략)
        news_cache_db.upsert_summary(
            news_id=news["id"],
            title=news["title"],
            ai_summary=result["ai_summary"],
            related_stocks=result["related_stocks"],
            source=news.get("source", ""),
            url=news.get("url"),
            published_at=news.get("published_at"),
            category=news.get("category", "news"),
            impact_strength=impact,
        )
        return result
    except Exception as e:
        return {
            "id": news["id"],
            "title": news["title"],
            "url": news.get("url"),
            "ai_summary": f"AI 요약 생성 중 오류가 발생했습니다: {str(e)}",
            "related_stocks": [],
        }
