"""정책 분석 서비스.

정책브리핑(korea.kr) RSS에서 주력 테마 보도자료를 수집하고,
Supabase policy_news 테이블에 저장·조회한다.
RSS 수집 실패 시 샘플 데이터로 폴백한다.
"""

import uuid
import json
import logging
from datetime import datetime, timedelta

from app.services import gemini_service
from app.services import policy_rss_service
from app.services import policy_news_db
from app.utils.freshness import is_within_time_window
from app.utils.policy_attachments import extract_attachment_links, extract_pdf_text

logger = logging.getLogger(__name__)

# 폴백용 샘플 정책 데이터 (Supabase/RSS 모두 실패 시)
SAMPLE_POLICIES = [
    {
        "id": str(uuid.uuid4()),
        "title": "2차전지 산업 육성 5개년 종합계획",
        "department": "산업통상자원부",
        "description": "총 10조원 규모 R&D 투자, 배터리 소재·부품 국산화, 차세대 전고체 배터리 개발 지원, 배터리 재활용 산업 육성, 세제 혜택 및 금융 지원",
        "effective_date": "2026-03-01",
        "tags": ["battery_recycle"],
        "link": "",
        "image_url": None,
        "created_at": (datetime.now() - timedelta(days=1)).isoformat(),
    },
    {
        "id": str(uuid.uuid4()),
        "title": "반도체 특별법 시행령 개정",
        "department": "과학기술정보통신부",
        "description": "반도체 설비투자 세액공제 확대(15%→25%), 반도체 클러스터 용지 확보, 전력 인프라 우선 공급, 해외 인력 유치 규제 완화",
        "effective_date": "2026-04-01",
        "tags": ["ai", "power_infra"],
        "link": "",
        "image_url": None,
        "created_at": (datetime.now() - timedelta(days=3)).isoformat(),
    },
    {
        "id": str(uuid.uuid4()),
        "title": "SMR(소형모듈원자로) 수출 및 인허가 지원",
        "department": "산업통상자원부",
        "description": "소형 모듈 원자로 해외 수출 인프라 구축, 인허가 단축 및 표준화 지원, 원전 밸류체인 강화",
        "effective_date": "2026-05-01",
        "tags": ["smr"],
        "link": "",
        "image_url": None,
        "created_at": (datetime.now() - timedelta(days=2)).isoformat(),
    },
    {
        "id": str(uuid.uuid4()),
        "title": "방위산업 육성 및 수출 지원 강화",
        "department": "방위사업청",
        "description": "K-방산 수출 금융 지원 확대, 방산 중소기업 R&D 투자, 수출 인프라 통합 지원",
        "effective_date": "2026-02-01",
        "tags": ["k_defense"],
        "link": "",
        "image_url": None,
        "created_at": (datetime.now() - timedelta(days=4)).isoformat(),
    },
    {
        "id": str(uuid.uuid4()),
        "title": "디지털 헬스케어 규제 샌드박스 확대",
        "department": "보건복지부",
        "description": "AI 의료기기 인허가 간소화, 원격의료 시범사업 확대, 디지털 치료제 급여 적용 추진, 의료 데이터 활용 규제 완화",
        "effective_date": "2026-06-01",
        "tags": ["silver_tech", "ai"],
        "link": "",
        "image_url": None,
        "created_at": (datetime.now() - timedelta(days=5)).isoformat(),
    },
]


def _sync_rss_to_db() -> None:
    """RSS 피드를 수집해서 DB에 저장한다 (1시간 캐시)."""
    try:
        items = policy_rss_service.fetch_and_filter()
        if items:
            policy_news_db.upsert_policies(items)
    except Exception as e:
        logger.warning("RSS→DB 동기화 실패: %s", e)


def get_policy_list(
    page: int = 1,
    limit: int = 10,
    keywords: str | None = None,
) -> dict:
    """정책 목록을 반환한다."""
    # RSS → DB 동기화 시도 (캐시 있으면 즉시 반환)
    _sync_rss_to_db()

    # 키워드 → 태그 변환
    tags = None
    if keywords:
        tags = [k.strip().lower() for k in keywords.split(",") if k.strip()]

    # Supabase에서 조회
    db_items, total = policy_news_db.get_policy_list(page=page, limit=limit, tags=tags)

    if db_items:
        items = []
        for p in db_items:
            items.append({
                "id": p["id"],
                "title": p["title"],
                "department": p.get("department", "정책브리핑"),
                "description": p.get("description", ""),
                "effective_date": None,
                "link": p.get("link", ""),
                "image_url": p.get("image_url"),
                "ai_analysis": p.get("ai_summary"),
                "beneficiary_stocks": p.get("ai_stocks") or [],
                "created_at": p.get("created_at"),
            })
        return {"items": items, "total": total, "page": page, "limit": limit}

    # 폴백: 샘플 데이터 (타임윈도우 적용)
    filtered = [
        p for p in SAMPLE_POLICIES
        if is_within_time_window(p.get("created_at"), hours=72)
    ]
    if tags:
        want = set(tags)
        filtered = [p for p in filtered if want & set(p.get("tags") or [])]

    total = len(filtered)
    start = (page - 1) * limit
    end = start + limit
    items = []
    for p in filtered[start:end]:
        items.append({
            "id": p["id"],
            "title": p["title"],
            "department": p["department"],
            "description": p["description"],
            "effective_date": p.get("effective_date"),
            "link": p.get("link", ""),
            "image_url": p.get("image_url"),
            "ai_analysis": None,
            "beneficiary_stocks": [],
            "created_at": p["created_at"],
        })
    return {"items": items, "total": total, "page": page, "limit": limit}


def get_policy_by_id(policy_id: str) -> dict | None:
    """ID로 정책을 찾는다."""
    # DB 먼저
    db_item = policy_news_db.get_policy_by_id(policy_id)
    if db_item:
        return db_item

    # 폴백: 샘플
    for p in SAMPLE_POLICIES:
        if p["id"] == policy_id:
            return p
    return None


async def get_policy_analysis(policy_id: str) -> dict | None:
    """정책 AI 분석을 생성한다."""
    policy = get_policy_by_id(policy_id)
    if not policy:
        return None

    # 이미 AI 분석이 저장되어 있으면 그대로 반환
    if policy.get("ai_summary") and policy.get("ai_stocks"):
        return {
            "id": policy["id"],
            "title": policy["title"],
            "department": policy.get("department", ""),
            "description": policy.get("description", ""),
            "effective_date": policy.get("effective_date"),
            "link": policy.get("link", ""),
            "image_url": policy.get("image_url"),
            "ai_analysis": policy["ai_summary"],
            "beneficiary_stocks": policy["ai_stocks"],
            "created_at": policy.get("created_at"),
        }

    try:
        title = policy["title"]
        desc = policy.get("description", "")
        link = policy.get("link", "")
        if link:
            att_links = extract_attachment_links(link)
            for att_url in att_links:
                if ".pdf" in att_url.lower():
                    pdf_text = extract_pdf_text(att_url)
                    if pdf_text:
                        desc += f"\n\n[첨부 PDF 내용]\n{pdf_text}"
                        break
        raw = await gemini_service.analyze_policy(title, desc)
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0]
        parsed = json.loads(cleaned)

        ai_summary = parsed.get("analysis", "")
        ai_stocks = parsed.get("beneficiary_stocks", [])

        # DB에 분석 결과 저장
        policy_news_db.update_ai_analysis(policy_id, ai_summary, ai_stocks)

        return {
            "id": policy["id"],
            "title": policy["title"],
            "department": policy.get("department", ""),
            "description": policy.get("description", ""),
            "effective_date": policy.get("effective_date"),
            "link": policy.get("link", ""),
            "image_url": policy.get("image_url"),
            "ai_analysis": ai_summary,
            "beneficiary_stocks": ai_stocks,
            "created_at": policy.get("created_at"),
        }
    except Exception as e:
        return {
            "id": policy["id"],
            "title": policy["title"],
            "department": policy.get("department", ""),
            "description": policy.get("description", ""),
            "effective_date": policy.get("effective_date"),
            "link": policy.get("link", ""),
            "image_url": policy.get("image_url"),
            "ai_analysis": f"AI 분석 중 오류가 발생했습니다: {str(e)}",
            "beneficiary_stocks": [],
            "created_at": policy.get("created_at"),
        }
