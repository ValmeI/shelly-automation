from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class ShellyConfig(BaseSettings):
    """Configuration for Shelly automation. All fields required (fail-fast)."""

    shelly_ip: str = Field(..., description="Device IP address")
    switch_id: int = Field(..., description="Switch ID (usually 0)")

    latitude: float = Field(..., description="Location latitude")
    longitude: float = Field(..., description="Location longitude")
    timezone: str = Field(..., description="Timezone e.g. Europe/Tallinn")

    sunrise_offset: int = Field(..., description="Minutes offset: + after, - before")
    enable_sunset_automation: bool = Field(..., description="Enable automatic turn ON at sunset")

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

    class Config:
        env_file = ".env"
