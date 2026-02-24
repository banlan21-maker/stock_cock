"""데이터 신선도 및 타임라인 필터. 모든 시간은 Asia/Seoul 기준."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Asia/Seoul")

# 평일: 24시간 / 월요일·휴장 다음날: 금요일 18시 이후
MARKET_CLOSE_FRIDAY_HOUR = 18


def now_seoul() -> datetime:
    """현재 시각 (Asia/Seoul)."""
    return datetime.now(TZ)


def get_time_window_cutoff(hours: int = 24) -> datetime:
    """
    수집·노출 기준 시각. 이 시각 이후 데이터만 허용.
    - 평일: 현재 - hours시간
    - 월요일 또는 휴장 다음날: 마지막 장 마감(금요일 18시) 이후
      단, hours > 24인 경우 hours 기준을 우선 적용.
    """
    now = now_seoul()
    wd = now.weekday()  # 0=월, 4=금, 6=일

    # hours가 기본값(24h)일 때만 주말/휴장 로직 적용
    if hours == 24:
        if wd == 0:  # 월요일
            last_friday = now - timedelta(days=3)
            return last_friday.replace(
                hour=MARKET_CLOSE_FRIDAY_HOUR, minute=0, second=0, microsecond=0, tzinfo=TZ
            )
        if wd == 6:  # 일요일
            last_friday = now - timedelta(days=2)
            return last_friday.replace(
                hour=MARKET_CLOSE_FRIDAY_HOUR, minute=0, second=0, microsecond=0, tzinfo=TZ
            )

    return now - timedelta(hours=hours)


def is_within_time_window(published_at: str | None, hours: int = 24) -> bool:
    """발행일이 타임윈도우 내인지 여부."""
    if not published_at:
        return False
    try:
        dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=ZoneInfo("UTC")).astimezone(TZ)
        else:
            dt = dt.astimezone(TZ)
        return dt >= get_time_window_cutoff(hours=hours)
    except Exception:
        return False
