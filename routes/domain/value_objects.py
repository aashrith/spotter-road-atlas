"""Immutable value objects shared across the routing domain."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Coordinate:
    lat: float
    lng: float

    def __post_init__(self) -> None:
        if not (-90.0 <= self.lat <= 90.0 and -180.0 <= self.lng <= 180.0):
            raise ValueError(f"Invalid coordinate ({self.lat}, {self.lng})")


@dataclass(frozen=True, slots=True)
class RoutePoint:
    """A point on a route with its cumulative distance from the start."""

    coord: Coordinate
    position_miles: float


@dataclass(frozen=True, slots=True)
class VehicleSpec:
    max_range_miles: float
    miles_per_gallon: float

    @property
    def tank_capacity_gallons(self) -> float:
        return self.max_range_miles / self.miles_per_gallon
