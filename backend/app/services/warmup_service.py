import asyncio
import logging
from app.routers import dashboard

logger = logging.getLogger(__name__)

async def warmup_all():
    """Startup routine to pre-fetch heavy data."""
    logger.info("🔥 Warming up cache...")
    try:
        # 1. Warm up Theme Trends (Daily)
        # This might take time due to Gemini call if not cached.
        await dashboard.get_theme_trend(sort="change_rate", period="daily")
        logger.info("✅ Theme Trend (Daily) warmed up.")
        
        # 2. Warm up Dashboard Summary
        await dashboard.get_dashboard()
        logger.info("✅ Dashboard Summary warmed up.")
        
    except Exception as e:
        logger.error(f"⚠️ Warmup failed: {e}")

async def start_background_tasks() -> list[asyncio.Task]:
    """Start background tasks for periodic updates."""
    # Currently no persistent background tasks needed as we use cache expiration
    # to trigger refreshes on next request. 
    # If needed, we can add a loop here to call warmup_all() every X minutes.
    return []
