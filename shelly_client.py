from typing import Any, Dict, List

import requests
from loguru import logger


class ShellyClient:
    """Client for interacting with Shelly Gen 3 devices via RPC API."""

    def __init__(self, ip: str, timeout: int = 10):
        """Initialize Shelly client."""
        self.ip = ip
        self.timeout = timeout
        self.base_url = f"http://{ip}/rpc"

    def _rpc_call(self, method: str, params: Dict[str, Any] | None = None) -> Dict[str, Any]:
        """
        Make an RPC call to the Shelly device.

        Args:
            method: RPC method name (e.g., 'Shelly.GetDeviceInfo')
            params: Optional parameters dictionary

        Returns:
            Response JSON as dictionary

        Raises:
            requests.RequestException: If request fails
            ValueError: If response contains error
        """
        url = f"{self.base_url}/{method}"

        try:
            if params:
                logger.info(f"Calling {method} with params: {params}")
                response = requests.post(url, json=params, timeout=self.timeout)
            else:
                logger.info(f"Calling {method}")
                response = requests.get(url, timeout=self.timeout)

            response.raise_for_status()
            data = response.json()

            if isinstance(data, dict) and "error" in data:
                error_msg = data["error"].get("message", "Unknown error")
                raise ValueError(f"RPC error: {error_msg}")

            logger.info(f"Response from {method}: {data}")
            return data

        except requests.RequestException as e:
            logger.error(f"Failed to connect to Shelly device at {self.ip}: {e}")
            raise
        except ValueError as e:
            logger.error(f"Invalid response from Shelly device: {e}")
            raise

    def list_schedules(self) -> List[Dict[str, Any]]:
        """List all schedules."""
        result = self._rpc_call("Schedule.List")
        return result.get("jobs", [])

    def delete_schedule(self, schedule_id: int) -> None:
        """Delete a schedule by ID."""
        self._rpc_call("Schedule.Delete", {"id": schedule_id})

    def delete_all_schedules(self, schedules: List[Dict[str, Any]] | None = None) -> int:
        """Delete all existing schedules. Returns number of schedules deleted."""
        if schedules is None:
            schedules = self.list_schedules()

        if not schedules:
            return 0

        deleted_count = 0
        for schedule in schedules:
            schedule_id = schedule.get("id")
            if schedule_id is not None:
                try:
                    self.delete_schedule(schedule_id)
                    deleted_count += 1
                except (requests.RequestException, ValueError) as e:
                    logger.warning(f"Failed to delete schedule {schedule_id}: {e}")

        return deleted_count

    def create_schedule(self, timespec: str, switch_id: int, turn_on: bool, enabled: bool = True, condition_if_on: bool = False) -> int:
        """Create a new schedule. Returns created schedule ID."""
        params = {"enable": enabled, "timespec": timespec, "calls": [{"method": "Switch.Set", "params": {"id": switch_id, "on": turn_on}}]}

        if condition_if_on:
            params["condition"] = {"cmp": {"a": f"switch:{switch_id}.output", "b": True, "op": "=="}}

        result = self._rpc_call("Schedule.Create", params)
        return result.get("id", -1)
