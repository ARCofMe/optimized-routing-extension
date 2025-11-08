"""
manager/base.py

Core routing abstractions and data models shared across routing providers.
This module defines:
- ServiceWindow (AM/PM/ALL_DAY)
- RouteStop dataclass (individual job stop)
- BaseRoutingManager (abstract base for routing backends)

Extending this:
    Subclass BaseRoutingManager and implement `build_route_url()` for your mapping API.
    Example: GoogleMapsRoutingManager, MapboxRoutingManager, etc.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List
from collections import defaultdict

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# ENUMS
# ---------------------------------------------------------------------------

class ServiceWindow(Enum):
    """Defines technician scheduling windows."""
    AM = auto()        # 7 AM – 12 PM
    PM = auto()        # 12 PM – 5 PM
    ALL_DAY = auto()   # 8 AM – 4 PM


# ---------------------------------------------------------------------------
# DATA MODELS
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class RouteStop:
    """
    Represents a single stop on a technician's route.

    Attributes:
        address (str): Full address of the stop.
        window (ServiceWindow): The service window (AM, PM, ALL_DAY).
        label (str | None): Optional identifier (e.g. ticket number, customer name).
        job_count (int): Number of jobs at this location (after deduplication).
    """
    address: str
    window: ServiceWindow
    label: str | None = None
    job_count: int = 1


# ---------------------------------------------------------------------------
# BASE CLASS
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class BaseRoutingManager(ABC):
    """
    Abstract base class for building route optimizers.

    Attributes:
        origin (str): Starting address for the route.
        stops (List[RouteStop]): Collection of route stops.
        end_at_origin (bool): Whether to return to origin at end of route.
    """

    origin: str
    stops: List[RouteStop] = field(default_factory=list)
    end_at_origin: bool = True

    # ----------------------------
    # Add / Manage Stops
    # ----------------------------

    def add_stop(self, stop: RouteStop) -> None:
        """Add a single stop to the route."""
        self.stops.append(stop)

    def add_stops(self, stops: List[RouteStop]) -> None:
        """Add multiple stops to the route."""
        self.stops.extend(stops)

    # ----------------------------
    # Abstract Interface
    # ----------------------------

    @abstractmethod
    def build_route_url(self) -> str:
        """
        Return a routing URL specific to the provider (e.g., Google Maps).

        Must:
            - Respect `origin`
            - Include all `stops` as waypoints
            - Optionally include labels or metadata
        """
        ...

    # ----------------------------
    # Ordering & Grouping
    # ----------------------------

    def ordered_stops(self) -> List[RouteStop]:
        """
        Order stops based on their service window priority.

        Priority:
            AM (0)
            ALL_DAY (1)
            PM (2)

        TODO: Replace with TSP heuristic considering distances and time windows.
        """
        priority = {
            ServiceWindow.AM: 0,
            ServiceWindow.ALL_DAY: 1,
            ServiceWindow.PM: 2,
        }
        return sorted(self.stops, key=lambda s: priority[s.window])

    def grouped_stops(self) -> list[list[RouteStop]]:
        """
        Group stops into service windows (AM → ALL_DAY → PM).

        Returns:
            List of grouped stop lists in chronological order.
        """
        groups = {ServiceWindow.AM: [], ServiceWindow.PM: [], ServiceWindow.ALL_DAY: []}
        for stop in self.ordered_stops():
            groups[stop.window].append(stop)
        return [
            groups[w]
            for w in [ServiceWindow.AM, ServiceWindow.ALL_DAY, ServiceWindow.PM]
            if groups[w]
        ]

    # ----------------------------
    # Deduplication
    # ----------------------------

    def deduplicate_stops(self) -> list[RouteStop]:
        """
        Combine stops that share the same address (case-insensitive).

        Rules:
            - Retains the earliest service window among duplicates.
            - Combines all labels into a comma-separated string.
            - Increments `job_count`.
            - Adds “(x jobs)” annotation to the label.

        Returns:
            A new list of unique RouteStop instances.
        """
        grouped = defaultdict(list)

        # Group stops by normalized address
        for stop in self.stops:
            key = stop.address.strip().lower()
            grouped[key].append(stop)

        unique_stops: list[RouteStop] = []
        for key, stops in grouped.items():
            if len(stops) == 1:
                unique_stops.append(stops[0])
                continue

            base = stops[0]
            combined_labels = [s.label for s in stops if s.label]
            base.label = ", ".join(combined_labels) if combined_labels else base.label
            base.job_count = len(stops)

            # Determine earliest window
            window_priority = {
                ServiceWindow.AM: 0,
                ServiceWindow.ALL_DAY: 1,
                ServiceWindow.PM: 2,
            }
            base.window = min(stops, key=lambda s: window_priority[s.window]).window

            base.label = f"{base.label or 'Jobs'} ({base.job_count} jobs)"
            unique_stops.append(base)

        if len(unique_stops) != len(self.stops):
            logger.info(
                f"[ROUTING] Deduplicated {len(self.stops) - len(unique_stops)} redundant stops "
                f"→ {len(unique_stops)} unique locations."
            )

        return unique_stops
