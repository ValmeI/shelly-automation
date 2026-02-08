from typing import Any, Dict

import requests
from loguru import logger


class ShellyClient:
    def __init__(self, ip: str, timeout: int = 10):
        self.ip = ip
        self.timeout = timeout
        self.base_url = f"http://{ip}/rpc"

    def _rpc_call(self, method: str, params: Dict[str, Any] | None = None) -> Dict[str, Any]:
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
