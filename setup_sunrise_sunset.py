import sys
from datetime import datetime, timedelta

from astral import LocationInfo
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
    logger.info(f"  Sunrise offset: {config.sunrise_offset} minutes")
    logger.info(f"  Enable sunset automation: {config.enable_sunset_automation}")
    logger.info(f"  Log level: {config.log_level}")


def show_existing_schedules(client: ShellyClient) -> list:
    logger.info("=== BEFORE CHANGES ===")
    schedules = client.list_schedules()
    if len(schedules) == 0:
        logger.info("No existing schedules on device")
    else:
        logger.info(f"Found {len(schedules)} existing schedule(s):")
        for schedule in schedules:
            schedule_id = schedule.get('id')
            timespec = schedule.get('timespec')
            enabled = schedule.get('enable')
            call = schedule.get('calls', [{}])[0]
            switch_id = call.get('params', {}).get('id')
            turn_on = call.get('params', {}).get('on')
            action = 'ON' if turn_on else 'OFF'
            status = 'enabled' if enabled else 'disabled'
            logger.info(f"  - ID {schedule_id}: {timespec} → Switch {switch_id} = {action} ({status})")
    return schedules


def calculate_sunrise_sunset_times(config: ShellyConfig) -> tuple[datetime, datetime]:
    location = LocationInfo("Home", "Estonia", config.timezone, config.latitude, config.longitude)

    logger.info("Calculating today's sunrise/sunset times...")
    logger.info("")

    today = datetime.now()
    s = sun(location.observer, date=today)

    sunrise_time = s['sunrise'] + timedelta(minutes=config.sunrise_offset)
    sunset_time = s['sunset']

    logger.info(f"Today's times: Sunrise {s['sunrise'].strftime('%H:%M')} → Sunset {s['sunset'].strftime('%H:%M')}")
    logger.info(f"With offset: Sunrise+{config.sunrise_offset}min = {sunrise_time.strftime('%H:%M')}")
    logger.info("")

    return sunrise_time, sunset_time


def create_recurring_schedules(client: ShellyClient, config: ShellyConfig, sunrise_time: datetime, sunset_time: datetime) -> None:
    if config.enable_sunset_automation:
        sunset_cron = f"{sunset_time.minute} {sunset_time.hour} * * *"
        sunset_id = client.create_schedule(
            timespec=sunset_cron,
            switch_id=config.switch_id,
            turn_on=True
        )
        logger.success(f"Created recurring sunset schedule: {sunset_time.strftime('%H:%M')} → Turn ON daily (ID: {sunset_id})")

    sunrise_cron = f"{sunrise_time.minute} {sunrise_time.hour} * * *"
    sunrise_id = client.create_schedule(
        timespec=sunrise_cron,
        switch_id=config.switch_id,
        turn_on=False
    )
    logger.success(f"Created recurring sunrise schedule: {sunrise_time.strftime('%H:%M')} → Turn OFF daily (ID: {sunrise_id})")


def verify_schedules(client: ShellyClient, config: ShellyConfig) -> None:
    logger.info("")
    logger.info("=== AFTER CHANGES ===")
    schedules_after = client.list_schedules()
    logger.info(f"Configured {len(schedules_after)} schedule(s) on device")

    logger.info("")
    logger.info("=== VERIFICATION ===")
    expected_count = 2 if config.enable_sunset_automation else 1
    if len(schedules_after) != expected_count:
        logger.error(f"Expected {expected_count} schedule(s) but found {len(schedules_after)}!")
        sys.exit(1)

    logger.info(f"✓ All {len(schedules_after)} schedules verified on device")
    logger.info(f"✓ Schedules are recurring daily (will trigger every day at the same time)")


def show_summary(config: ShellyConfig, sunrise_time: datetime, sunset_time: datetime) -> None:
    logger.info("")
    logger.success("✓ Configuration complete!")
    logger.info("")
    logger.info("=== SCHEDULE SUMMARY ===")

    logger.info("Recurring daily schedules:")
    if config.enable_sunset_automation:
        logger.info(f"  • {sunset_time.strftime('%H:%M')} - Turn lights ON (every day)")
    logger.info(f"  • {sunrise_time.strftime('%H:%M')} - Turn lights OFF (every day)")

    logger.info("")
    logger.info("Note: Times will drift ~2 minutes per day as sunrise/sunset changes")
    logger.warning("Run this script weekly or monthly to update schedule times!")
    logger.info("Add to crontab: 0 1 * * 0 cd /path/to/shelly-automation && .venv/bin/python setup_sunrise_sunset.py")


def main() -> None:
    try:
        logger.info("Loading configuration...")
        config = ShellyConfig()

        log_configuration(config)

        client = ShellyClient(config.shelly_ip)
        client.get_device_info()

        show_existing_schedules(client)

        client.configure_location(config.latitude, config.longitude, config.timezone)
        client.delete_all_schedules()

        sunrise_time, sunset_time = calculate_sunrise_sunset_times(config)

        create_recurring_schedules(client, config, sunrise_time, sunset_time)

        verify_schedules(client, config)

        show_summary(config, sunrise_time, sunset_time)

    except Exception as e:
        logger.exception(f"Configuration failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    colorama_init(autoreset=True)

    try:
        config = ShellyConfig()
        init_logging(config.log_level, config.log_file)
    except Exception as e:
        init_logging("INFO")
        logger.error(f"Failed to load configuration: {e}")
        logger.error("Make sure you have created a .env file with all required settings.")
        logger.error("Copy .env.example to .env and fill in your values.")
        sys.exit(1)

    main()
