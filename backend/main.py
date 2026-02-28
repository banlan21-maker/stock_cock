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

import asyncio
import logging
import sys

_logger = logging.getLogger(__name__)

from app.main import app as _asgi_app

# ── 직접 asyncio 브릿지 (a2wsgi 대체) ───────────────────────────────────────
# a2wsgi 1.x의 배경 스레드 + 제너레이터 방식이 Cloud Functions에서 응답을
# 반환하지 않는 문제가 있어 asyncio.run() 기반의 직접 호출로 교체.
# Firebase Functions Python 런타임은 동기(Flask/Werkzeug)이므로
# 이벤트 루프가 없는 상태에서 asyncio.run()을 안전하게 호출할 수 있음.
# asyncio.run()은 스레드별로 독립적인 이벤트 루프를 생성하므로 동시성 안전.
#
# lifespan은 app/main.py에서 단순 yield만 하므로 생략해도 무방.


async def _handle_http(scope: dict, body: bytes) -> dict:
    """ASGI HTTP 요청을 처리하고 {status, headers, body}를 반환한다."""
    received = False

    async def receive():
        nonlocal received
        if not received:
            received = True
            return {"type": "http.request", "body": body, "more_body": False}
        # 실제 disconnect 신호 전까지 대기 (timeout 방지용 짧은 대기)
        await asyncio.sleep(0.1)
        return {"type": "http.disconnect"}

    resp: dict = {"status": 200, "headers": [], "body": b""}

    async def send(message: dict) -> None:
        if message["type"] == "http.response.start":
            resp["status"] = message["status"]
            resp["headers"] = list(message.get("headers", []))
        elif message["type"] == "http.response.body":
            chunk = message.get("body", b"")
            if chunk:
                resp["body"] += chunk

    await _asgi_app(scope, receive, send)
    return resp


@https_fn.on_request(timeout_sec=120, memory=1024, secrets=_SECRETS)
def api(req: https_fn.Request) -> https_fn.Response:
    try:
        print(f"[api] {req.method} {req.path}", file=sys.stderr, flush=True)

        # ASGI HTTP scope 구성
        headers = [
            (k.lower().encode("latin-1"), v.encode("latin-1"))
            for k, v in req.headers.items()
        ]
        host = req.host or "localhost"
        scope = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": req.method.upper(),
            "headers": headers,
            "path": req.path or "/",
            "query_string": req.query_string or b"",
            "root_path": "",
            "scheme": req.scheme or "https",
            "server": (host.split(":")[0], 443),
        }
        body = req.get_data()

        # asyncio.run()은 매 요청마다 새 이벤트 루프를 생성/파괴함.
        # 각 스레드가 독립적인 이벤트 루프를 가지므로 동시 요청에 안전.
        resp = asyncio.run(_handle_http(scope, body))

        # 헤더 변환
        headers_dict: dict[str, str] = {}
        for k, v in resp["headers"]:
            if isinstance(k, bytes):
                k = k.decode("latin-1")
            if isinstance(v, bytes):
                v = v.decode("latin-1")
            headers_dict[k] = v

        print(f"[api] response {resp['status']}, {len(resp['body'])} bytes", file=sys.stderr, flush=True)
        return https_fn.Response(
            response=resp["body"],
            status=resp["status"],
            headers=headers_dict,
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
