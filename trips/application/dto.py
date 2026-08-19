from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from routes.application.dto import ResolvedLocation
from routes.domain.entities import FuelPlan
from routes.domain.value_objects import Coordinate

from trips.domain.entities import DaySheet, TripSchedule, TripStop

from .ports import TripRoute


@dataclass(frozen=True, slots=True)
class LocatedStop:
    """A trip stop with its map coordinate (and nearest place) resolved."""

    stop: TripStop
    coord: Coordinate
    place: str | None = None  # "City, ST" of the nearest known truckstop


@dataclass(frozen=True, slots=True)
class TripPlanResult:
    current: ResolvedLocation
    pickup: ResolvedLocation
    dropoff: ResolvedLocation
    route: TripRoute
    schedule: TripSchedule
    day_sheets: tuple[DaySheet, ...]
    located_stops: tuple[LocatedStop, ...]
    fuel_plan: FuelPlan
    start_time: datetime
    cycle_used_hours: float
