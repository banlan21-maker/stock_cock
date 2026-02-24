"""뉴스 필터: 가짜/광고 차단, 중복 제거, 우선순위 정렬."""

import re
from difflib import SequenceMatcher

# 제목에 포함되면 제외
SKIP_TITLE_PATTERNS = [
    re.compile(r"\[포토\]", re.I),
    re.compile(r"\[인사\]", re.I),
    re.compile(r"\[부고\]", re.I),
]

# 본문 최소 길이 (이하면 광고성 의심)
MIN_BODY_LEN = 50

# 메이저 언론사 (중복 시 우선)
MAJOR_SOURCES = frozenset([
    "연합뉴스", "Reuters", "Bloomberg", "한겨레", "조선일보", "매일경제", "한국경제",
    "경향신문", "동아일보", "Financial Times", "WSJ", "AP", "AFP", "조선비즈",
])

# 우선순위 순서 (정책 > 해외 > 국내)
CATEGORY_PRIORITY = {"policy": 0, "global": 1, "domestic": 2, "news": 2}


def _title_similarity(a: str, b: str) -> float:
    """두 제목의 유사도 0~1."""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def should_skip_article(title: str, content: str) -> bool:
    """가짜/광고성 기사 여부. True면 제외."""
    for pat in SKIP_TITLE_PATTERNS:
        if pat.search(title):
            return True
    content = (content or "").strip()
    if len(content) < MIN_BODY_LEN:
        return True
    return False


def deduplicate_by_similarity(articles: list[dict], threshold: float = 0.8) -> list[dict]:
    """
    제목 유사도 80% 이상이거나 동일 사건 뉴스를 그룹화하여,
    메이저 언론사 또는 조회수(없으면 먼저 나온 것) 1개만 유지.
    """
    if not articles:
        return []

    result: list[dict] = []
    used = [False] * len(articles)

    for i, a in enumerate(articles):
        if used[i]:
            continue
        group = [i]
        title_a = (a.get("title") or "").strip()
        for j in range(i + 1, len(articles)):
            if used[j]:
                continue
            b = articles[j]
            title_b = (b.get("title") or "").strip()
            if _title_similarity(title_a, title_b) >= threshold:
                group.append(j)
                used[j] = True

        # 그룹 내에서 1개 선택: 메이저 우선, 같으면 첫 번째
        best_idx = group[0]
        best_src = (articles[best_idx].get("source") or "").strip()
        best_is_major = best_src in MAJOR_SOURCES

        for idx in group[1:]:
            src = (articles[idx].get("source") or "").strip()
            is_major = src in MAJOR_SOURCES
            if is_major and not best_is_major:
                best_idx = idx
                best_src = src
                best_is_major = True
            elif is_major == best_is_major and src > best_src:
                best_idx = idx

        result.append(articles[best_idx])
    return result


def sort_by_priority(articles: list[dict]) -> list[dict]:
    """정책 원문 > 해외 주요 > 국내 일반 순 정렬. 동일 그룹 내 최신순."""
    out = list(articles)
    out.sort(key=lambda a: (a.get("published_at") or ""), reverse=True)  # 최신순
    out.sort(
        key=lambda a: (
            CATEGORY_PRIORITY.get((a.get("category") or "news").lower(), 2),
            0 if ((a.get("source") or "").strip() in MAJOR_SOURCES) else 1,
        )
    )
    return out
