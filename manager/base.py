# manager/base.py

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List


class ServiceWindow(Enum):
    AM = auto()  # 7–12
    PM = auto()  # 12–17
    ALL_DAY = auto()  # 8–16


@dataclass(slots=True)
class RouteStop:
    address: str
    window: ServiceWindow
    label: str | None = None  # e.g. ticket number, customer last name


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
