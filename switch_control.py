#!/usr/bin/env python3
import sys
from typing import Literal

from loguru import logger
from tenacity import stop_after_attempt, wait_fixed, retry_if_result, before_sleep_log, Retrying

from config import ShellyConfig
from logging_config import init_logging
from shelly_client import ShellyClient

SWITCH_ID = 0


def get_switch_state(client: ShellyClient) -> bool | None:
    try:
        result = client._rpc_call("Switch.GetStatus", {"id": SWITCH_ID})
        return result.get("output", False)
    except Exception as e:
        logger.error(f"Failed to get switch state: {e}")
        return None


def set_switch_and_verify(client: ShellyClient, desired_state: bool, action_name: str) -> bool:
    try:
        client._rpc_call("Switch.Set", {"id": SWITCH_ID, "on": desired_state})
        logger.info(f"Command sent: Turn {action_name}")

        new_state = get_switch_state(client)
        if new_state == desired_state:
            logger.success(f"✓ Lights turned {action_name} successfully!")
            return True
        else:
            logger.warning(f"State not changed yet, will retry...")
            return False

    except Exception as e:
        logger.error(f"Failed to set switch state: {e}")
        return False


def attempt_switch_control(client: ShellyClient, desired_state: bool, action_name: str, max_retries: int, retry_wait: int) -> bool:
    retryer = Retrying(
        stop=stop_after_attempt(max_retries),
        wait=wait_fixed(retry_wait),
        retry=retry_if_result(lambda result: result is False),
        before_sleep=before_sleep_log(logger, "WARNING")
    )

    return retryer(set_switch_and_verify, client, desired_state, action_name)


def connect_and_check(client: ShellyClient, desired_state: bool, action_name: str, max_retries: int, retry_wait: int) -> int:
    retryer = Retrying(
        stop=stop_after_attempt(max_retries),
        wait=wait_fixed(retry_wait),
        retry=retry_if_result(lambda r: r is None),
        before_sleep=before_sleep_log(logger, "WARNING")
    )

    current_state = retryer(get_switch_state, client)
    if current_state is None:
        logger.error(f"Cannot determine switch state after {max_retries} attempts")
        return 2

    if current_state == desired_state:
        logger.info(f"Lights already {action_name} - no action needed")
        return 1

    return -1


def control_switch(action: Literal["on", "off"]) -> int:
    config = ShellyConfig.from_yaml()
    client = ShellyClient(config.shelly_ip)

    desired_state = (action == "on")
    action_name = "ON" if desired_state else "OFF"

    logger.info(f"Target: Turn lights {action_name}")

    check_result = connect_and_check(client, desired_state, action_name, config.max_retries, config.retry_wait)
    if check_result >= 0:
        return check_result

    try:
        success = attempt_switch_control(client, desired_state, action_name, config.max_retries, config.retry_wait)
        return 0 if success else 2
    except Exception:
        logger.error(f"Failed to turn lights {action_name} after {config.max_retries} attempts")
        return 2


def main():
    if len(sys.argv) < 2:
        print("Usage: switch_control.py [on|off]")
        sys.exit(1)

    action = sys.argv[1].lower()
    if action not in ["on", "off"]:
        print("Error: Action must be 'on' or 'off'")
        sys.exit(1)

    config = ShellyConfig.from_yaml()
    init_logging(level=config.log_level, log_file=config.log_file)

    exit_code = control_switch(action)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
