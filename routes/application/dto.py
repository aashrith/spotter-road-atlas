from __future__ import annotations

from dataclasses import dataclass

from routes.domain.entities import FuelPlan, Route
from routes.domain.value_objects import Coordinate


@dataclass(frozen=True, slots=True)
class ResolvedLocation:
    query: str
    coord: Coordinate


@dataclass(frozen=True, slots=True)
class FuelRoutePlan:
    start: ResolvedLocation
    finish: ResolvedLocation
    route: Route
    fuel_plan: FuelPlan
