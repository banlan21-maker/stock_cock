from supabase import create_client, Client
from app.config import get_settings

_client: Client | None = None


def get_supabase() -> Client:
    """Supabase 클라이언트 싱글턴. 매번 새 연결을 만들지 않는다."""
    global _client
    if _client is not None:
        return _client
    settings = get_settings()
    _client = create_client(settings.supabase_url, settings.supabase_service_key)
    return _client


def reset_supabase() -> None:
    """유휴 연결 오류 시 싱글턴을 초기화해 다음 호출에서 새 클라이언트를 생성하도록 한다."""
    global _client
    _client = None
