from pathlib import Path
from typing import List, Literal

import yaml
from pydantic import BaseModel, Field, field_validator


class Schedule(BaseModel):
    """Single schedule definition."""

    time: str = Field(..., description="Time: 'HH:MM', 'sunrise', or 'sunset'")
    action: Literal["on", "off"] = Field(..., description="Turn switch on or off")
    offset: int = Field(0, description="Minutes offset for sunrise/sunset (+ after, - before)")


class ShellyConfig(BaseModel):
    """Configuration for Shelly automation. All fields required (fail-fast)."""

    shelly_ip: str = Field(..., description="Device IP address")
    switch_id: int = Field(..., description="Switch ID (usually 0)")

    latitude: float = Field(..., description="Location latitude")
    longitude: float = Field(..., description="Location longitude")
    timezone: str = Field(..., description="Timezone e.g. Europe/Tallinn")

    schedules: List[Schedule] = Field(..., description="List of schedule definitions")

    log_level: str = Field(..., description="DEBUG, INFO, WARNING, ERROR")
    log_file: str = Field(..., description="Path to log file")

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        allowed = ["DEBUG", "INFO", "WARNING", "ERROR"]
        if v.upper() not in allowed:
            raise ValueError(f"log_level must be one of {allowed}, got: {v}")
        return v.upper()

    @field_validator("latitude")
    @classmethod
    def validate_latitude(cls, v: float) -> float:
        """Validate latitude range."""
        if not -90 <= v <= 90:
            raise ValueError(f"latitude must be between -90 and 90, got: {v}")
        return v

    @field_validator("longitude")
    @classmethod
    def validate_longitude(cls, v: float) -> float:
        """Validate longitude range."""
        if not -180 <= v <= 180:
            raise ValueError(f"longitude must be between -180 and 180, got: {v}")
        return v

    @classmethod
    def from_yaml(cls, path: str = "config.yaml") -> "ShellyConfig":
        """Load configuration from YAML file."""
        config_path = Path(path)
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")

        with open(config_path, "r") as f:
            data = yaml.safe_load(f)

        return cls(**data)

    def get_schedules(self) -> List[Schedule]:
        """Return schedule list."""
        return self.schedules
