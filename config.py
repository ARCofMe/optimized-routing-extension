"""
config.py
----------

Configuration module for route generation and optimization.

This file defines lightweight configuration objects used by the routing
extension. These objects allow you to specify technician‑specific or
context‑specific routing options such as starting and ending locations
without altering BlueFolder’s core user models.

Example:
    >>> from config import RouteConfig
    >>> config = RouteConfig(
    ...     start_location="180 E Hebron Rd, Hebron, ME",
    ...     end_location="46 Elm St, Topsham, ME"
    ... )
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class RouteConfig:
    """
    Configuration for route generation.

    This dataclass holds optional parameters that define where a route
    should start and end. These are typically set per user (technician),
    but can be overridden at runtime to support custom routing logic.

    Attributes:
        start_location (Optional[str]):
            The starting address for the day’s route (e.g., a warehouse or
            storage unit). If None, the first job address is used as the origin.

        end_location (Optional[str]):
            The ending address for the day’s route (e.g., the technician’s
            home). If None, the last job address is used as the destination.
    """

    start_location: Optional[str] = None
    end_location: Optional[str] = None
