#!/usr/bin/env python3
import os
import subprocess
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from astral import Observer
from astral.sun import sun
from loguru import logger

from config import ShellyConfig, Schedule
from logging_config import init_logging


def calculate_sun_times(latitude: float, longitude: float, timezone: str, date: datetime | None = None) -> dict[str, datetime]:
    observer = Observer(latitude=latitude, longitude=longitude)
    tz = ZoneInfo(timezone)
    target_date = date if date else datetime.now(tz)
    s = sun(observer, date=target_date, tzinfo=tz)
    return {"sunrise": s["sunrise"], "sunset": s["sunset"]}


def calculate_schedule_time(schedule: Schedule, sun_times: dict[str, datetime], timezone: str) -> datetime:
    tz = ZoneInfo(timezone)

    if schedule.time in ["sunrise", "sunset"]:
        base_time = sun_times[schedule.time]
        return base_time + timedelta(minutes=schedule.offset)
    else:
        hour, minute = map(int, schedule.time.split(":"))
        return datetime.now(tz).replace(hour=hour, minute=minute, second=0, microsecond=0)

def schedule_with_at(time_str: str, command: str, description: str):
    try:
        at_command = f"echo '{command}' | at {time_str}"
        subprocess.run(at_command, shell=True, capture_output=True, text=True, check=True)
        logger.info(f"✓ Scheduled: {description} at {time_str}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to schedule {description}: {e.stderr}")
        return False


def main():
    config = ShellyConfig.from_yaml()
    init_logging(level=config.log_level, log_file=config.log_file)

    logger.info("=== SCHEDULING TODAY'S JOBS ===")
    tz = ZoneInfo(config.timezone)

    sun_times = calculate_sun_times(config.latitude, config.longitude, config.timezone)
    logger.info(f"Today's sun times: Sunrise {sun_times['sunrise'].strftime('%H:%M')}, Sunset {sun_times['sunset'].strftime('%H:%M')}")
    logger.info("")

    project_path = os.path.dirname(os.path.abspath(__file__))
    python_path = os.path.join(project_path, ".venv/bin/python")

    schedules = config.get_schedules()
    scheduled_count = 0

    for idx, schedule in enumerate(schedules):
        target_time = calculate_schedule_time(schedule, sun_times, config.timezone)

        now = datetime.now(tz)
        if target_time < now:
            logger.warning(f"Skipping schedule {idx}: {target_time.strftime('%H:%M')} already passed")
            continue

        time_str = target_time.strftime("%H:%M")
        switch_cmd = f"cd {project_path} && {python_path} switch_control.py {schedule.action} >> logs/at.log 2>&1"

        desc = f"Lights {schedule.action.upper()} ({schedule.time}+{schedule.offset})"
        if schedule_with_at(time_str, switch_cmd, desc):
            scheduled_count += 1

    logger.info("")
    logger.success(f"✓ Scheduled {scheduled_count} job(s) for today")
    logger.info("Run 'atq' to see scheduled jobs")
    logger.info("Run 'atrm <job_id>' to remove a job")


if __name__ == "__main__":
    main()
