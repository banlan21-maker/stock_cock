# Firebase Cloud Functions entry point for FastAPI
from firebase_functions import https_fn, params

# Firebase Secret Manager에 등록된 시크릿을 환경변수로 주입
SUPABASE_URL        = params.SecretParam("SUPABASE_URL")
SUPABASE_SERVICE_KEY = params.SecretParam("SUPABASE_SERVICE_KEY")
GEMINI_API_KEY      = params.SecretParam("GEMINI_API_KEY")
NAVER_CLIENT_ID     = params.SecretParam("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = params.SecretParam("NAVER_CLIENT_SECRET")
NEWS_API_KEY        = params.SecretParam("NEWS_API_KEY")
DART_API_KEY        = params.SecretParam("DART_API_KEY")
FRONTEND_URL        = params.SecretParam("FRONTEND_URL")

_SECRETS = [
    SUPABASE_URL, SUPABASE_SERVICE_KEY, GEMINI_API_KEY,
    NAVER_CLIENT_ID, NAVER_CLIENT_SECRET, NEWS_API_KEY,
    DART_API_KEY, FRONTEND_URL,
]

import logging
import sys

_logger = logging.getLogger(__name__)

# nest_asyncio를 제거: Firebase Functions Python 런타임은 동기(Flask 기반)이므로
# 중첩 이벤트 루프가 불필요하고, Python 3.12 에서 호환성 문제를 유발할 수 있음.

from app.main import app as _asgi_app
from a2wsgi import ASGIMiddleware

# ASGI(FastAPI) → WSGI 브릿지 (wait_time 늘림: 패키지 임포트 포함 콜드 스타트 대응)
_wsgi_app = ASGIMiddleware(_asgi_app, wait_time=60.0)

_logger.info("a2wsgi ASGIMiddleware 초기화 완료")


@https_fn.on_request(timeout_sec=120, memory=1024, secrets=_SECRETS)
def api(req: https_fn.Request) -> https_fn.Response:
    try:
        print(f"[api] {req.method} {req.path}", file=sys.stderr, flush=True)
        environ = req.environ
        status_code = [200]
        headers = [[]]

        def start_response(status, response_headers, exc_info=None):
            status_code[0] = int(status.split()[0])
            headers[0] = response_headers
            print(f"[api] start_response: {status}", file=sys.stderr, flush=True)

        print("[api] calling _wsgi_app", file=sys.stderr, flush=True)
        result = _wsgi_app(environ, start_response)
        print(f"[api] _wsgi_app returned: {type(result).__name__}", file=sys.stderr, flush=True)

        chunks = []
        for chunk in result:
            chunks.append(chunk)

        if hasattr(result, "close"):
            result.close()

        body = b"".join(chunks)
        print(f"[api] response {status_code[0]}, {len(body)} bytes", file=sys.stderr, flush=True)
        return https_fn.Response(
            response=body,
            status=status_code[0],
            headers=dict(headers[0]),
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"[api] EXCEPTION: {e}", file=sys.stderr, flush=True)
        return https_fn.Response(response=f"Internal Server Error: {str(e)}", status=500)


if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port)
