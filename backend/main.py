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

from app.main import app as _asgi_app
from a2wsgi import ASGIMiddleware

# ASGI(FastAPI) → WSGI 브릿지 (handle_asgi_request 버전 호환 문제 우회)
_wsgi_app = ASGIMiddleware(_asgi_app)


@https_fn.on_request(timeout_sec=120, memory=1024, secrets=_SECRETS)
def api(req: https_fn.Request) -> https_fn.Response:
    chunks: list[bytes] = []
    status_info: list = [200, []]

    def start_response(status: str, headers: list, exc_info=None):
        status_info[0] = int(status.split(" ", 1)[0])
        status_info[1] = headers

    for chunk in _wsgi_app(req.environ, start_response):
        chunks.append(chunk)

    return https_fn.Response(
        response=b"".join(chunks),
        status=status_info[0],
        headers=dict(status_info[1]),
    )

if __name__ == "__main__":
    import uvicorn
    import os
    # Cloud Run/App Hosting은 PORT 환경변수를 제공함 (기본 8080)
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port)
