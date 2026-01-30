import sys
from datetime import datetime

from colorama import init as colorama_init
from loguru import logger

from config import ShellyConfig
from logging_config import init_logging
from schedule_calculator import calculate_schedule_time, calculate_sun_times, get_schedule_description, time_to_cron
from shelly_client import ShellyClient

SWITCH_ID = 0


def log_configuration(config: ShellyConfig) -> None:
    logger.info("Configuration loaded successfully:")
    logger.info(f"  Device IP: {config.shelly_ip}")
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


def create_schedules(
    client: ShellyClient, config: ShellyConfig, sun_times: dict[str, datetime]
) -> list[tuple[datetime, str]]:
    """Create schedules on device and return resolved times/actions."""
    resolved: list[tuple[datetime, str]] = []
    for schedule in config.get_schedules():
        schedule_time = calculate_schedule_time(schedule, sun_times, config.timezone)
        cron = time_to_cron(schedule_time)
        turn_on = schedule.action == "on"

        schedule_id = client.create_schedule(timespec=cron, switch_id=SWITCH_ID, turn_on=turn_on)
        description = get_schedule_description(schedule, schedule_time)
        logger.success(f"Created: {description} (ID: {schedule_id})")
        action = "ON" if turn_on else "OFF"
        resolved.append((schedule_time, action))
    return resolved


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


def show_summary(
    config: ShellyConfig, sun_times: dict[str, datetime], resolved_times: list[tuple[datetime, str]]
) -> None:
    logger.info("")
    logger.success("✓ Configuration complete!")
    logger.info("")
    logger.info("=== SCHEDULE SUMMARY ===")

    logger.info(f"Sun times today: Sunrise {sun_times['sunrise'].strftime('%H:%M')}, Sunset {sun_times['sunset'].strftime('%H:%M')}")
    logger.info("")
    logger.info(f"Created {len(config.get_schedules())} recurring daily schedules")
    if resolved_times:
        logger.info("Added schedule times (today):")
        for schedule_time, action in resolved_times:
            logger.success(f"  - {schedule_time.strftime('%H:%M')} → Lights {action}")
    logger.info("Note: Times will drift ~2 minutes per day as sunrise/sunset changes")


def main() -> None:
    try:
        logger.info("Loading configuration...")
        config = ShellyConfig.from_yaml()

        log_configuration(config)

        client = ShellyClient(config.shelly_ip)

        existing_schedules = show_existing_schedules(client)

        if existing_schedules:
            deleted_count = client.delete_all_schedules(existing_schedules)
            logger.info(f"Deleted {deleted_count} existing schedule(s)")
            logger.info("")

        logger.info("Calculating sunrise/sunset times...")
        sun_times = calculate_sun_times(config.latitude, config.longitude, config.timezone)
        logger.info(f"  Sunrise: {sun_times['sunrise'].strftime('%H:%M')}")
        logger.info(f"  Sunset: {sun_times['sunset'].strftime('%H:%M')}")
        logger.info("")

        logger.info("Creating schedules...")
        resolved_times = create_schedules(client, config, sun_times)

        verify_schedules(client, config)

        show_summary(config, sun_times, resolved_times)

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
