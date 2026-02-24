"""SSE 이벤트 포맷 유틸."""

import json


def sse_event(event: str, data: dict) -> str:
    """SSE 이벤트 포맷 문자열 반환."""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
