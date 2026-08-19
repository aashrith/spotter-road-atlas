"""Ports specific to the trips context (routing with waypoints)."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from routes.domain.value_objects import Coordinate, RoutePoint


@dataclass(frozen=True, slots=True)
class TripLeg:
    distance_miles: float
    duration_hours: float


@dataclass(frozen=True, slots=True)
class TripRoute:
    """A multi-waypoint route: combined geometry plus per-leg stats."""

    geometry: tuple[Coordinate, ...]
    sampled_points: tuple[RoutePoint, ...]
    legs: tuple[TripLeg, ...]

    @property
    def distance_miles(self) -> float:
        return sum(leg.distance_miles for leg in self.legs)

    @property
    def duration_hours(self) -> float:
        return sum(leg.duration_hours for leg in self.legs)


class TripRouter(Protocol):
    def get_trip_route(self, waypoints: Sequence[Coordinate]) -> TripRoute:
        """Fetch one driving route through all waypoints (single API call)."""
