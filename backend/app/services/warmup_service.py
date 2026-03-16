import logging
from app.routers import dashboard

logger = logging.getLogger(__name__)

async def warmup_all():
    """테마트렌드(4가지 조합) + 대시보드 캐시를 미리 계산해서 저장."""
    logger.info("캐시 워밍업 시작...")
    try:
        # 일간 데이터 (TTL: 1시간) - 2가지 정렬
        await dashboard.get_theme_trend(sort="change_rate", period="daily")
        logger.info("일간 상승률 워밍업 완료")
        await dashboard.get_theme_trend(sort="volume", period="daily")
        logger.info("일간 거래대금 워밍업 완료")
    except Exception as e:
        logger.error("일간 워밍업 실패: %s", e)

    try:
        # 주간 데이터 (TTL: 24시간) - 2가지 정렬
        await dashboard.get_theme_trend(sort="change_rate", period="weekly")
        logger.info("주간 상승률 워밍업 완료")
        await dashboard.get_theme_trend(sort="volume", period="weekly")
        logger.info("주간 거래대금 워밍업 완료")
    except Exception as e:
        logger.error("주간 워밍업 실패: %s", e)

    try:
        # 대시보드 요약 (TTL: 5분)
        await dashboard.get_dashboard()
        logger.info("대시보드 워밍업 완료")
    except Exception as e:
        logger.error("대시보드 워밍업 실패: %s", e)

    logger.info("캐시 워밍업 전체 완료")


async def warmup_daily_only():
    """일간 데이터만 갱신 (장중 매 시간용)."""
    logger.info("일간 캐시 워밍업 시작...")
    try:
        await dashboard.get_theme_trend(sort="change_rate", period="daily")
        await dashboard.get_theme_trend(sort="volume", period="daily")
        await dashboard.get_dashboard()
        logger.info("일간 캐시 워밍업 완료")
    except Exception as e:
        logger.error("일간 워밍업 실패: %s", e)
