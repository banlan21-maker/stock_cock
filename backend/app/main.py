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
    """서버 시작/종료 시 실행되는 lifespan 컨텍스트.

    NOTE: warmup_all()은 동기 Supabase 호출(get_generic_cache)을 내부적으로 수행하므로
    asyncio 이벤트 루프를 블록하여 첫 번째 요청이 무한 대기 상태에 빠지는 문제가 있습니다.
    캐시 pre-warm은 제거하고 첫 실제 요청 시 on-demand로 채워지도록 합니다.
    """
    yield


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
        # 로컬 개발 (항상 명시적으로 포함)
        "http://localhost:3000",
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


@app.get("/health")
async def health_check():
    """데이터 소스 연결 상태 진단 엔드포인트."""
    result: dict = {"status": "ok", "checks": {}}
    try:
        import FinanceDataReader as fdr
        df = fdr.StockListing("KRX")
        result["checks"]["fdr_listing"] = {
            "ok": not df.empty,
            "rows": len(df),
            "columns": df.columns.tolist(),
        }
    except Exception as e:
        result["checks"]["fdr_listing"] = {"ok": False, "error": str(e)}
        result["status"] = "degraded"

    try:
        import FinanceDataReader as fdr
        df = fdr.DataReader("005930", "2025-01-01", "2025-01-10")
        result["checks"]["fdr_price"] = {
            "ok": not df.empty,
            "rows": len(df),
            "columns": df.columns.tolist(),
        }
    except Exception as e:
        result["checks"]["fdr_price"] = {"ok": False, "error": str(e)}
        result["status"] = "degraded"

    try:
        from pykrx import stock as pykrx_stock
        result["checks"]["pykrx"] = {"ok": True}
    except Exception as e:
        result["checks"]["pykrx"] = {"ok": False, "error": str(e)}
        result["status"] = "degraded"

    # 종목 목록 상태 추가
    from app.services import stock_service as _ss
    result["checks"]["stock_list"] = {
        "ok": bool(_ss.STOCK_LIST_CACHE),
        "count": len(_ss.STOCK_LIST_CACHE) if _ss.STOCK_LIST_CACHE else 0,
        "sample": [s["name"] for s in (_ss.STOCK_LIST_CACHE or [])[:3]],
    }
    return result


@app.post("/admin/reload-stock-list")
async def reload_stock_list():
    """종목 목록 캐시를 강제 초기화 후 재로딩한다 (재시작 없이 갱신)."""
    from app.services import stock_service as _ss
    _ss.STOCK_LIST_CACHE = None
    result = await asyncio.to_thread(_ss.get_stock_list)
    return {"count": len(result), "sample": [s["name"] for s in result[:5]]}
