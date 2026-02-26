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

from app.main import app

# FastAPI 앱을 Firebase https 함수로 노출
# timeout=120: AI 분석 시간을 고려하여 2분으로 설정
# memory=1024: 분석 라이브러리 실행을 위해 1GB 할당
@https_fn.on_request(timeout_sec=120, memory=1024, secrets=_SECRETS)
def api(req: https_fn.Request) -> https_fn.Response:
    return https_fn.handle_asgi_request(app, req)
