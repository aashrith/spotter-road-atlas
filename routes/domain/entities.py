"""Domain entities for fuel-aware routing."""
from __future__ import annotations

from dataclasses import dataclass

from .value_objects import Coordinate, RoutePoint


@dataclass(frozen=True, slots=True)
class FuelStation:
    opis_id: int
    name: str
    address: str
    city: str
    state: str
    price_per_gallon: float
    coord: Coordinate


@dataclass(frozen=True, slots=True)
class StationOnRoute:
    """A fuel station matched to a route corridor."""

    station: FuelStation
    position_miles: float  # distance from route start
    detour_miles: float  # straight-line distance from the route polyline


@dataclass(frozen=True, slots=True)
class Route:
    geometry: tuple[Coordinate, ...]
    sampled_points: tuple[RoutePoint, ...]
    distance_miles: float
    duration_seconds: float


@dataclass(frozen=True, slots=True)
class FuelPurchase:
    stop: StationOnRoute
    gallons: float
    cost: float


@dataclass(frozen=True, slots=True)
class FuelPlan:
    purchases: tuple[FuelPurchase, ...]

    @property
    def total_gallons(self) -> float:
        return sum(p.gallons for p in self.purchases)

    @property
    def total_cost(self) -> float:
        return sum(p.cost for p in self.purchases)
