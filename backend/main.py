# Firebase Cloud Functions entry point for FastAPI
from firebase_functions import https_fn
from app.main import app

# FastAPI 앱을 Firebase https 함수로 노출
# timeout=120: AI 분석 시간을 고려하여 2분으로 설정
# memory=1024: 분석 라이브러리 실행을 위해 1GB 할당
@https_fn.on_request(timeout_sec=120, memory=1024)
def api(req: https_fn.Request) -> https_fn.Response:
    return https_fn.handle_asgi_request(app, req)
