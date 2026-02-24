"""정책 기사에서 PDF/HWP 첨부파일 링크 추출 및 텍스트 수집.

korea.kr 보도자료에 첨부된 PDF/HWP를 가져와 Gemini에 던져 진짜 내용 분석.
"""

import logging
import re
from io import BytesIO

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

_ATTACH_RE = re.compile(r"\.(pdf|hwp)(\?|$)", re.I)
_BASE = "https://www.korea.kr"


def extract_attachment_links(article_url: str) -> list[str]:
    """기사 페이지 HTML에서 PDF/HWP 첨부 링크를 추출한다."""
    links: list[str] = []
    try:
        with httpx.Client(timeout=15.0, follow_redirects=True) as client:
            resp = client.get(article_url)
            resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if not _ATTACH_RE.search(href):
                continue
            if href.startswith("/"):
                href = f"{_BASE}{href}"
            if href not in links:
                links.append(href)
    except Exception as e:
        logger.debug("첨부파일 링크 추출 실패: %s", e)
    return links[:3]


def extract_pdf_text(url: str) -> str:
    """PDF URL에서 텍스트를 추출한다."""
    try:
        with httpx.Client(timeout=20.0, follow_redirects=True) as client:
            resp = client.get(url)
            resp.raise_for_status()
        from pypdf import PdfReader
        reader = PdfReader(BytesIO(resp.content))
        parts = []
        for i, page in enumerate(reader.pages[:10]):
            if i >= 10:
                break
            text = page.extract_text()
            if text:
                parts.append(text.strip())
        return "\n\n".join(parts)[:8000] if parts else ""
    except Exception as e:
        logger.debug("PDF 텍스트 추출 실패 %s: %s", url[:50], e)
        return ""
