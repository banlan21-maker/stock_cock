"""설계서 6절: 통일된 에러 응답 형식 { error: { code, message, details? } }."""

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

# HTTP status -> (error_code, default_message)
ERROR_CODE_MAP = {
    401: ("AUTH_REQUIRED", "로그인이 필요합니다."),
    404: ("NOT_FOUND", "리소스를 찾을 수 없습니다."),
    429: ("RATE_LIMITED", "요청이 너무 많습니다. 잠시 후 다시 시도해 주세요."),
    502: ("NEWS_FETCH_FAILED", "뉴스를 가져올 수 없습니다."),
    503: ("AI_ANALYSIS_FAILED", "AI 분석 중 오류가 발생했습니다."),
}

# 메시지 일부로 세부 코드 결정 (detail 문자열 매칭)
DETAIL_TO_CODE = {
    "종목을 찾을 수 없습니다": "STOCK_NOT_FOUND",
    "차트 데이터를 가져올 수 없습니다": "CHART_NOT_FOUND",
    "뉴스를 찾을 수 없습니다": "NEWS_NOT_FOUND",
    "정책을 찾을 수 없습니다": "POLICY_NOT_FOUND",
    "AI 분석": "AI_ANALYSIS_FAILED",
}


def error_response(status_code: int, message: str, code: str | None = None, details: dict | None = None) -> dict:
    """설계서 형식의 error body."""
    if code is None:
        code, _ = ERROR_CODE_MAP.get(status_code, ("UNKNOWN", message))
    return {
        "error": {
            "code": code,
            "message": message,
            **({"details": details} if details is not None else {}),
        }
    }


def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """HTTPException을 설계서 형식의 JSON으로 변환."""
    code = None
    for fragment, detail_code in DETAIL_TO_CODE.items():
        if exc.detail and fragment in str(exc.detail):
            code = detail_code
            break
    if code is None:
        code, _ = ERROR_CODE_MAP.get(exc.status_code, ("UNKNOWN", str(exc.detail)))
    message = str(exc.detail) if exc.detail else ERROR_CODE_MAP.get(exc.status_code, ("", ""))[1]
    body = error_response(exc.status_code, message, code=code)
    return JSONResponse(status_code=exc.status_code, content=body)
