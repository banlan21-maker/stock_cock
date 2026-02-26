import os
from pathlib import Path
from pydantic_settings import BaseSettings
from functools import lru_cache

# 백엔드 루트(backend/) 기준 .env 경로 (프로젝트 루트에서 실행해도 로드되도록)
_BACKEND_DIR = Path(__file__).resolve().parent.parent
# 우선순위: .env.local (로컬 개발용) -> .env (배포 시 Firebase가 자동 생성할 수도 있음)
_ENV_FILE_LOCAL = _BACKEND_DIR / ".env.local"
_ENV_FILE_DEFAULT = _BACKEND_DIR / ".env"
_ENV_FILE = _ENV_FILE_LOCAL if _ENV_FILE_LOCAL.exists() else _ENV_FILE_DEFAULT


def _load_env_file():
    if not _ENV_FILE.exists():
        return
    # utf-8-sig: BOM 자동 제거 (Windows에서 .env 저장 시 BOM 붙는 경우 대비)
    for line in _ENV_FILE.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        key = k.strip().lstrip("\ufeff")  # BOM 등 invisibles 제거
        val = v.strip()
        if key:
            if val.startswith('"') and val.endswith('"') or val.startswith("'") and val.endswith("'"):
                val = val[1:-1]
            os.environ[key] = val  # backend/.env 값을 항상 적용(기존 환경변수 덮어씀)
    if not os.environ.get("GEMINI_API_KEY") and os.environ.get("GOOGLE_API_KEY"):
        os.environ["GEMINI_API_KEY"] = os.environ["GOOGLE_API_KEY"]


# 모듈 로드 시 backend/.env를 환경변수에 주입 (uvicorn cwd가 루트여도 적용)
_load_env_file()


class Settings(BaseSettings):
    # FastAPI
    app_title: str = "Stock Cock API"
    debug: bool = True

    # CORS
    frontend_url: str = "http://localhost:3000"

    # Gemini (GEMINI_API_KEY 또는 GOOGLE_API_KEY)
    gemini_api_key: str = ""

    # Naver Search API
    naver_client_id: str = ""
    naver_client_secret: str = ""

    # NewsAPI.org
    news_api_key: str = ""

    # Supabase
    supabase_url: str = ""
    supabase_service_key: str = ""

    # DART 전자공시
    dart_api_key: str = ""

    model_config = {
        "env_file": _ENV_FILE if _ENV_FILE.exists() else ".env",
        "env_file_encoding": "utf-8-sig",
        "extra": "ignore",
    }


@lru_cache
def get_settings() -> Settings:
    # Pydantic이 os.environ과 env_file 모두 참조하므로, 위 _load_env_file()에서 이미 주입됨
    return Settings()
