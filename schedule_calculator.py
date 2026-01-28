from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from astral import Observer
from astral.sun import sun

from config import Schedule


def calculate_sun_times(latitude: float, longitude: float, timezone: str, date: datetime | None = None) -> dict[str, datetime]:
    """Calculate sunrise and sunset times for given location and date. Pure function."""
    observer = Observer(latitude=latitude, longitude=longitude)
    tz = ZoneInfo(timezone)
    target_date = date if date else datetime.now(tz)
    s = sun(observer, date=target_date, tzinfo=tz)

    return {"sunrise": s["sunrise"], "sunset": s["sunset"]}


def calculate_schedule_time(schedule: Schedule, sun_times: dict[str, datetime], timezone: str) -> datetime:
    """Calculate actual time for a schedule. Pure function."""
    tz = ZoneInfo(timezone)

    if schedule.time in ["sunrise", "sunset"]:
        base_time = sun_times[schedule.time]
        return base_time + timedelta(minutes=schedule.offset)
    else:
        hour, minute = map(int, schedule.time.split(":"))
        return datetime.now(tz).replace(hour=hour, minute=minute, second=0, microsecond=0)


def time_to_cron(dt: datetime) -> str:
    """Convert datetime to Shelly cron format. Pure function."""
    return f"0 {dt.minute} {dt.hour} * * *"


def get_schedule_description(schedule: Schedule, actual_time: datetime) -> str:
    """Get human-readable description of schedule. Pure function."""
    time_desc = f"{schedule.time}+{schedule.offset}min" if schedule.offset != 0 else schedule.time
    if schedule.time not in ["sunrise", "sunset"]:
        time_desc = schedule.time
    action_desc = "Turn ON" if schedule.action == "on" else "Turn OFF"
    return f"{actual_time.strftime('%H:%M')} ({time_desc}) → {action_desc}"
