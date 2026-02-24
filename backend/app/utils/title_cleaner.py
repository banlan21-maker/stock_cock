"""뉴스 제목 정제. HTML 엔티티 디코딩, 불필요한 특수문자/코드 제거."""

import html
import re

# 선행 [xxx] 패턴 (언론사/출처 태그)
_LEADING_TAG_RE = re.compile(r"^[\s\u3000]*\[[^\]]*\]\s*")
# 연속 공백
_MULTI_SPACE_RE = re.compile(r"\s+")


def clean_news_title(raw: str) -> str:
    """뉴스 제목만 추출. HTML 엔티티 디코딩(&quot;→"), 불필요한 [태그] 제거."""
    if not raw or not isinstance(raw, str):
        return ""
    s = raw.strip()
    s = html.unescape(s)
    s = _LEADING_TAG_RE.sub("", s)
    s = _MULTI_SPACE_RE.sub(" ", s)
    return s.strip()
