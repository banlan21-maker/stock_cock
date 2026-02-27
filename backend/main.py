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

import nest_asyncio
nest_asyncio.apply()

from app.main import app as _asgi_app
from a2wsgi import ASGIMiddleware

# ASGI(FastAPI) → WSGI 브릿지
_wsgi_app = ASGIMiddleware(_asgi_app, wait_time=10.0)


@https_fn.on_request(timeout_sec=120, memory=1024, secrets=_SECRETS)
def api(req: https_fn.Request) -> https_fn.Response:
    try:
        environ = req.environ
        status_code = [200]
        headers = [[]]

        def start_response(status, response_headers, exc_info=None):
            status_code[0] = int(status.split()[0])
            headers[0] = response_headers

        result = _wsgi_app(environ, start_response)

        chunks = []
        for chunk in result:
            chunks.append(chunk)

        if hasattr(result, "close"):
            result.close()

        return https_fn.Response(
            response=b"".join(chunks),
            status=status_code[0],
            headers=dict(headers[0]),
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return https_fn.Response(response=f"Internal Server Error: {str(e)}", status=500)


if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port)
