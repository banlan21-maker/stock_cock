import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.middleware import SlowAPIMiddleware
from slowapi.errors import RateLimitExceeded
from fastapi import HTTPException

from app.config import get_settings
from app.limiter import limiter
from app.routers import news, policy, stock, dashboard, cron, portfolio, disclosure
from app.errors import http_exception_handler, error_response

logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """서버 시작/종료 시 실행되는 lifespan 컨텍스트."""
    # ── 시작: 테마 캐시 warm-up + 백그라운드 자동 갱신 시작 ──
    bg_tasks: list[asyncio.Task] = []
    try:
        from app.services.warmup_service import warmup_all, start_background_tasks
        # warm-up은 별도 태스크로 띄워서 서버 시작을 블록하지 않음
        asyncio.create_task(warmup_all(), name="startup-warmup")
        bg_tasks = await start_background_tasks()
        logger.info("백그라운드 테마 갱신 태스크 시작 완료")
    except Exception as e:
        logger.warning("warm-up 서비스 초기화 실패 (서버는 정상 가동): %s", e)

    yield

    # ── 종료: 백그라운드 태스크 정리 ──
    for t in bg_tasks:
        t.cancel()
    if bg_tasks:
        await asyncio.gather(*bg_tasks, return_exceptions=True)
    logger.info("백그라운드 태스크 정리 완료")


app = FastAPI(
    title="Stock Cock API",
    description="주식콕 - 복잡한 주식 정보, 콕 집어 알려드려요",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(
    RateLimitExceeded,
    lambda req, exc: JSONResponse(
        status_code=429,
        content=error_response(429, "요청이 너무 많습니다. 잠시 후 다시 시도해 주세요.", code="RATE_LIMITED"),
    ),
)
app.add_exception_handler(
    ValueError,
    lambda req, exc: JSONResponse(
        status_code=503,
        content=error_response(503, str(exc), code="AI_ANALYSIS_FAILED"),
    ),
)
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.frontend_url,
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        # Firebase Hosting 도메인
        "https://banlan-stockcock.web.app",
        "https://banlan-stockcock.firebaseapp.com",
        # Firebase App Hosting 도메인
        "https://stock-cock-frontend--banlan-stockcock.asia-east1.hosted.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(news.router)
app.include_router(policy.router)
app.include_router(stock.router)
app.include_router(dashboard.router)
app.include_router(cron.router)
app.include_router(portfolio.router)
app.include_router(disclosure.router)


@app.get("/")
def read_root():
    return {"message": "Welcome to Stock Cock API", "version": "0.1.0"}
