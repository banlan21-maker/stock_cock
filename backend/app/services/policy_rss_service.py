"""정책브리핑(korea.kr) RSS 피드 수집 서비스.

RSS를 파싱해서 주력 테마 키워드에 해당하는 보도자료만 필터링하고,
Supabase policy_news 테이블에 중복 없이 저장한다.
"""

import re
import time
import logging
import hashlib
from datetime import datetime, timezone

import feedparser

logger = logging.getLogger(__name__)

RSS_URL = "https://www.korea.kr/rss/policy.xml"

# 주력 테마 키워드 (제목+설명에서 매칭)
THEME_KEYWORDS: list[str] = [
    # AI / 반도체
    "AI", "인공지능", "반도체", "반도체 특별법", "GPU", "HBM",
    # 로봇
    "로봇", "자동화", "스마트팩토리",
    # 양자컴퓨터
    "양자", "양자컴퓨터", "양자기술",
    # 초전도체
    "초전도", "초전도체",
    # 바이오
    "바이오", "의약", "제약", "헬스케어", "의료기기", "임상",
    # 우주
    "우주", "항공", "위성", "발사체",
    # SMR / 원전
    "SMR", "소형원자로", "소형모듈원자로", "원전", "원자력",
    # 변압기 / 구리 / 전력
    "변압기", "구리", "전력", "송전", "전력망", "전력인프라",
    # 방산
    "방산", "방위", "무기체계", "국방",
    # 폐배터리 / 2차전지
    "폐배터리", "배터리", "2차전지", "이차전지", "리튬", "전기차",
    # 실버테크
    "실버", "고령", "치매", "원격의료", "디지털치료", "안티에이징",
]

# 키워드 → 태그 매핑 (여러 키워드가 하나의 태그에 대응)
_KEYWORD_TAG_MAP: dict[str, str] = {
    "AI": "ai", "인공지능": "ai", "반도체": "ai", "GPU": "ai", "HBM": "ai",
    "반도체 특별법": "ai",
    "로봇": "robot", "자동화": "robot", "스마트팩토리": "robot",
    "양자": "quantum", "양자컴퓨터": "quantum", "양자기술": "quantum",
    "초전도": "superconductor", "초전도체": "superconductor",
    "바이오": "bio", "의약": "bio", "제약": "bio", "헬스케어": "bio",
    "의료기기": "bio", "임상": "bio",
    "우주": "space", "항공": "space", "위성": "space", "발사체": "space",
    "SMR": "smr", "소형원자로": "smr", "소형모듈원자로": "smr",
    "원전": "smr", "원자력": "smr",
    "변압기": "power_infra", "구리": "power_infra", "전력": "power_infra",
    "송전": "power_infra", "전력망": "power_infra", "전력인프라": "power_infra",
    "방산": "k_defense", "방위": "k_defense", "무기체계": "k_defense",
    "국방": "k_defense",
    "폐배터리": "battery_recycle", "배터리": "battery_recycle",
    "2차전지": "battery_recycle", "이차전지": "battery_recycle",
    "리튬": "battery_recycle", "전기차": "battery_recycle",
    "실버": "silver_tech", "고령": "silver_tech", "치매": "silver_tech",
    "원격의료": "silver_tech", "디지털치료": "silver_tech",
    "안티에이징": "silver_tech",
}

# HTML 태그 제거 정규식
_TAG_RE = re.compile(r"<[^>]+>")
# 이미지 URL 추출 정규식
_IMG_RE = re.compile(r'<img[^>]+src=["\']([^"\']+)["\']', re.IGNORECASE)

# 메모리 캐시 (마지막 fetch 시각)
_last_fetch_time: float = 0
_FETCH_INTERVAL = 3600  # 1시간
_cached_items: list[dict] = []


def _strip_html(text: str) -> str:
    return _TAG_RE.sub("", text).strip()


def _extract_image(html: str) -> str | None:
    """HTML description에서 실제 기사 이미지 URL을 추출한다.
    RSS 기본 아이콘(btn_textview.gif, icon_logo.gif)은 제외.
    """
    skip = {"btn_textview.gif", "icon_logo.gif"}
    for m in _IMG_RE.finditer(html):
        url = m.group(1)
        if any(s in url for s in skip):
            continue
        if url.startswith("/"):
            url = f"https://www.korea.kr{url}"
        return url
    return None


def _make_id(link: str) -> str:
    """링크에서 newsId를 추출하거나 해시 기반 ID를 생성한다."""
    m = re.search(r"newsId=(\d+)", link)
    if m:
        return f"policy-{m.group(1)}"
    return f"policy-{hashlib.md5(link.encode()).hexdigest()[:12]}"


def _match_tags(text: str) -> list[str]:
    """텍스트에서 키워드를 매칭하고 해당 태그 목록을 반환한다."""
    tags: set[str] = set()
    for keyword, tag in _KEYWORD_TAG_MAP.items():
        if keyword in text:
            tags.add(tag)
    return sorted(tags)


def fetch_and_filter() -> list[dict]:
    """RSS 피드를 가져와서 주력 테마 키워드에 해당하는 기사만 반환한다.
    1시간 캐시를 사용한다.
    """
    global _last_fetch_time, _cached_items

    now = time.time()
    if _cached_items and (now - _last_fetch_time) < _FETCH_INTERVAL:
        return _cached_items

    logger.info("정책브리핑 RSS 피드 수집 시작")
    try:
        feed = feedparser.parse(RSS_URL)
    except Exception as e:
        logger.error("RSS 파싱 실패: %s", e)
        return _cached_items  # 이전 캐시 반환

    items: list[dict] = []
    for entry in feed.entries:
        title = entry.get("title", "")
        description_html = entry.get("description", "")
        description_text = _strip_html(description_html)
        link = entry.get("link", "")

        # 키워드 매칭 (제목 + 설명)
        combined = title + " " + description_text
        tags = _match_tags(combined)
        if not tags:
            continue  # 테마와 무관한 기사 스킵

        # 이미지 추출
        image_url = _extract_image(description_html)

        # 발행일 파싱
        pub_date = entry.get("published", "")
        try:
            from email.utils import parsedate_to_datetime
            dt = parsedate_to_datetime(pub_date)
            published_at = dt.isoformat()
        except Exception:
            published_at = datetime.now(timezone.utc).isoformat()

        # department 추출 (korea.kr은 별도 필드 없으므로 빈 문자열)
        items.append({
            "id": _make_id(link),
            "title": title,
            "link": link,
            "description": description_text[:500],  # 요약용 텍스트 500자 제한
            "image_url": image_url,
            "published_at": published_at,
            "tags": tags,
            "department": "정책브리핑",
        })

    logger.info("RSS 피드에서 %d건 중 %d건 테마 매칭", len(feed.entries), len(items))
    _cached_items = items
    _last_fetch_time = now
    return items
