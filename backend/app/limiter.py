"""API Rate limiting (slowapi). AI 엔드포인트 보호용."""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
