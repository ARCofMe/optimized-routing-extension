# manager/base.py

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


class ServiceWindow(Enum):
    AM = auto()  # 7–12
    PM = auto()  # 12–17
    ALL_DAY = auto()  # 8–16


@dataclass(slots=True)
class RouteStop:
    address: str
    window: ServiceWindow
    label: str | None = None  # e.g. ticket number, customer last name
    job_count: int = 1

@dataclass(slots=True)
class BaseRoutingManager(ABC):
    origin: str
    stops: List[RouteStop] = field(default_factory=list)
    end_at_origin: bool = True

    def add_stop(self, stop: RouteStop) -> None:
        self.stops.append(stop)

    def add_stops(self, stops: List[RouteStop]) -> None:
        self.stops.extend(stops)

    @abstractmethod
    def build_route_url(self) -> str:
        """Return a mapping-provider-specific routing URL.

        Implementations should:
        - Respect `origin`
        - Include `stops` as waypoints
        - Optionally include labels in query params
        """

    def ordered_stops(self) -> List[RouteStop]:
        """Very simple ordering respecting AM/PM/ALL_DAY.
            @todo: In future, replace with a proper TSP heuristic that also respects service windows
        """
        priority = {
            ServiceWindow.AM: 0,
            ServiceWindow.ALL_DAY: 1,
            ServiceWindow.PM: 2,
        }
        return sorted(self.stops, key=lambda s: priority[s.window])

    def grouped_stops(self):
        """Group stops by service window (AM → PM → ALL_DAY)."""
        groups = {ServiceWindow.AM: [], ServiceWindow.PM: [], ServiceWindow.ALL_DAY: []}
        for stop in self.ordered_stops():
            groups[stop.window].append(stop)
        return [groups[w] for w in [ServiceWindow.AM, ServiceWindow.ALL_DAY, ServiceWindow.PM] if groups[w]]
    
    def deduplicate_stops(self) -> list[RouteStop]:
        """
        Combine stops with identical addresses (case-insensitive).
        - Keeps the earliest service window among duplicates.
        - Combines labels and increments job_count.
        - Returns a list of unique RouteStop instances.
        """
        grouped = defaultdict(list)

        # Group stops by normalized address
        for stop in self.stops:
            key = stop.address.strip().lower()
            grouped[key].append(stop)

        unique_stops = []
        for key, stops in grouped.items():
            if len(stops) == 1:
                unique_stops.append(stops[0])
                continue

            # Combine duplicates
            base = stops[0]
            combined_labels = [s.label for s in stops if s.label]
            base.label = ", ".join(combined_labels) if combined_labels else base.label
            base.job_count = len(stops)

            # Earliest window priority (AM < ALL_DAY < PM)
            window_priority = {ServiceWindow.AM: 0, ServiceWindow.ALL_DAY: 1, ServiceWindow.PM: 2}
            base.window = min(stops, key=lambda s: window_priority[s.window]).window

            # Append label annotation for visibility
            base.label = f"{base.label or 'Jobs'} ({base.job_count} jobs)"

            unique_stops.append(base)

        if len(unique_stops) != len(self.stops):
            logger.info(
                f"[ROUTING] Deduplicated {len(self.stops) - len(unique_stops)} redundant stops "
                f"→ {len(unique_stops)} unique locations."
            )

        return unique_stops