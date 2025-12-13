"""
config.py

Configuration models used throughout the routing extension.

Defines Pydantic models that provide structured, validated configuration data
for customizing route behavior and origin/destination overrides.
"""

from typing import Optional
from pydantic import BaseModel, Field, validator
import os

VALID_PROVIDERS = {"geoapify", "google", "mapbox", "osm"}


class RouteConfig(BaseModel):
    """
    Configuration model for customizing a route's origin and destination.

    This model allows overriding the default behavior of the routing manager,
    which typically uses the first and last addresses as the origin and
    destination respectively.

    Attributes:
        start_location (Optional[str]):
            Custom starting point for the route.
            If not provided, the first stop's address is used.

        end_location (Optional[str]):
            Custom ending point for the route.
            If not provided, the last stop's address is used.
    """

    start_location: Optional[str] = Field(
        default=None, description="Custom starting point for the route."
    )
    end_location: Optional[str] = Field(
        default=None, description="Custom ending point for the route."
    )


class Settings(BaseModel):
    """Typed configuration loaded from environment variables."""

    bluefolder_api_key: str = Field(default_factory=lambda: os.getenv("BLUEFOLDER_API_KEY", ""))
    bluefolder_base_url: str = Field(
        default_factory=lambda: os.getenv(
            "BLUEFOLDER_BASE_URL", "https://your.bluefolder.com/api/2.0"
        )
    )

    geoapify_api_key: str = Field(default_factory=lambda: os.getenv("GEOAPIFY_API_KEY", ""))
    google_api_key: str = Field(default_factory=lambda: os.getenv("GOOGLE_MAPS_API_KEY", ""))
    mapbox_api_key: str = Field(default_factory=lambda: os.getenv("MAPBOX_API_KEY", ""))
    osm_base_url: str = Field(
        default_factory=lambda: os.getenv("OSM_BASE_URL", "https://router.project-osrm.org")
    )

    cf_shortener_url: str = Field(default_factory=lambda: os.getenv("CF_SHORTENER_URL", ""))

    default_origin: str = Field(default_factory=lambda: os.getenv("DEFAULT_ORIGIN", "South Paris, ME"))
    default_provider: str = Field(default_factory=lambda: os.getenv("DEFAULT_PROVIDER", "geoapify").lower())

    @validator("default_provider", pre=True, always=True)
    def validate_default_provider(cls, v):
        provider = (v or "").lower()
        if provider not in VALID_PROVIDERS:
            raise ValueError(f"DEFAULT_PROVIDER must be one of {sorted(VALID_PROVIDERS)}")
        return provider

    class Config:
        arbitrary_types_allowed = True


settings = Settings()
