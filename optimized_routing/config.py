"""
config.py

Configuration models used throughout the routing extension.

Defines Pydantic models that provide structured, validated configuration data
for customizing route behavior and origin/destination overrides.
"""

from typing import Optional
from pydantic import BaseModel, Field


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
