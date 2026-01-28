import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from astral import Observer
from astral.sun import sun
from colorama import init as colorama_init
from loguru import logger

from config import ShellyConfig
from logging_config import init_logging
from shelly_client import ShellyClient


def log_configuration(config: ShellyConfig) -> None:
    logger.info("Configuration loaded successfully:")
    logger.info(f"  Device IP: {config.shelly_ip}")
    logger.info(f"  Switch ID: {config.switch_id}")
    logger.info(f"  Location: {config.latitude}, {config.longitude}")
    logger.info(f"  Timezone: {config.timezone}")
    logger.info(f"  Schedules: {len(config.get_schedules())} defined")
    logger.info(f"  Log level: {config.log_level}")


def show_existing_schedules(client: ShellyClient) -> list:
    logger.info("=== BEFORE CHANGES ===")
    schedules = client.list_schedules()
    if len(schedules) == 0:
        logger.info("No existing schedules on device")
    else:
        logger.info(f"Found {len(schedules)} existing schedule(s):")
        for schedule in schedules:
            schedule_id = schedule.get("id")
            timespec = schedule.get("timespec")
            enabled = schedule.get("enable")
            call = schedule.get("calls", [{}])[0]
            switch_id = call.get("params", {}).get("id")
            turn_on = call.get("params", {}).get("on")
            action = "ON" if turn_on else "OFF"
            status = "enabled" if enabled else "disabled"
            logger.info(f"  - ID {schedule_id}: {timespec} → Switch {switch_id} = {action} ({status})")
    return schedules


def calculate_schedule_times(config: ShellyConfig) -> dict[str, datetime]:
    observer = Observer(latitude=config.latitude, longitude=config.longitude)
    tz = ZoneInfo(config.timezone)
    today = datetime.now(tz)
    s = sun(observer, date=today, tzinfo=tz)

    logger.info("Calculating sunrise/sunset times...")
    logger.info(f"  Sunrise: {s['sunrise'].strftime('%H:%M')}")
    logger.info(f"  Sunset: {s['sunset'].strftime('%H:%M')}")
    logger.info("")

    return {"sunrise": s["sunrise"], "sunset": s["sunset"]}


def create_recurring_schedules(client: ShellyClient, config: ShellyConfig, times: dict[str, datetime]) -> None:
    schedules = config.get_schedules()
    tz = ZoneInfo(config.timezone)

    for schedule in schedules:
        if schedule.time in ["sunrise", "sunset"]:
            base_time = times[schedule.time]
            schedule_time = base_time + timedelta(minutes=schedule.offset)
            time_desc = f"{schedule.time}+{schedule.offset}min" if schedule.offset != 0 else schedule.time
        else:
            hour, minute = map(int, schedule.time.split(":"))
            schedule_time = datetime.now(tz).replace(hour=hour, minute=minute, second=0, microsecond=0)
            time_desc = schedule.time

        cron = f"0 {schedule_time.minute} {schedule_time.hour} * * *"
        turn_on = schedule.action == "on"
        action_desc = "Turn ON" if turn_on else "Turn OFF"

        schedule_id = client.create_schedule(timespec=cron, switch_id=config.switch_id, turn_on=turn_on)

        logger.success(f"Created schedule: {schedule_time.strftime('%H:%M')} ({time_desc}) → {action_desc} (ID: {schedule_id})")


def verify_schedules(client: ShellyClient, config: ShellyConfig) -> None:
    logger.info("")
    logger.info("=== AFTER CHANGES ===")
    schedules_after = client.list_schedules()
    logger.info(f"Configured {len(schedules_after)} schedule(s) on device")

    logger.info("")
    logger.info("=== VERIFICATION ===")
    expected_count = len(config.get_schedules())
    if len(schedules_after) != expected_count:
        logger.error(f"Expected {expected_count} schedule(s) but found {len(schedules_after)}!")
        sys.exit(1)

    logger.info(f"✓ All {len(schedules_after)} schedules verified on device")
    logger.info(f"✓ Schedules are recurring daily (will trigger every day at the same time)")


def show_summary(config: ShellyConfig, times: dict[str, datetime]) -> None:
    logger.info("")
    logger.success("✓ Configuration complete!")
    logger.info("")
    logger.info("=== SCHEDULE SUMMARY ===")

    schedules = config.get_schedules()
    tz = ZoneInfo(config.timezone)

    logger.info("Recurring daily schedules:")
    for schedule in schedules:
        if schedule.time in ["sunrise", "sunset"]:
            base_time = times[schedule.time]
            schedule_time = base_time + timedelta(minutes=schedule.offset)
            time_desc = f"{schedule.time}+{schedule.offset}min" if schedule.offset != 0 else schedule.time
        else:
            hour, minute = map(int, schedule.time.split(":"))
            schedule_time = datetime.now(tz).replace(hour=hour, minute=minute, second=0, microsecond=0)
            time_desc = schedule.time

        action_desc = "Turn ON" if schedule.action == "on" else "Turn OFF"
        logger.info(f"  • {schedule_time.strftime('%H:%M')} ({time_desc}) - {action_desc}")

    logger.info("")
    logger.info("Note: Times will drift ~2 minutes per day as sunrise/sunset changes")


def main() -> None:
    try:
        logger.info("Loading configuration...")
        config = ShellyConfig.from_yaml()

        log_configuration(config)

        client = ShellyClient(config.shelly_ip)
        client.get_device_info()

        show_existing_schedules(client)

        client.delete_all_schedules()

        times = calculate_schedule_times(config)

        create_recurring_schedules(client, config, times)

        verify_schedules(client, config)

        show_summary(config, times)

    except Exception as e:
        logger.exception(f"Configuration failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    colorama_init(autoreset=True)

    try:
        config = ShellyConfig.from_yaml()
        init_logging(config.log_level, config.log_file)
    except Exception as e:
        init_logging("INFO")
        logger.error(f"Failed to load configuration: {e}")
        logger.error("Make sure you have created a config.yaml file with all required settings.")
        logger.error("Copy config.yaml.example to config.yaml and fill in your values.")
        sys.exit(1)

    main()
