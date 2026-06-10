"""Use case: plan a fuel-optimal route between two US locations."""
from __future__ import annotations

import re

from routes.domain.exceptions import RouteNotServiceableError
from routes.domain.services.fuel_planner import FuelPlanner
from routes.domain.services.geometry import find_stations_along_route
from routes.domain.value_objects import Coordinate

from .dto import FuelRoutePlan, ResolvedLocation
from .ports import Geocoder, Router, StationRepository

_COORD_RE = re.compile(
    r"^\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*$"
)


class PlanFuelRoute:
    def __init__(
        self,
        geocoder: Geocoder,
        router: Router,
        stations: StationRepository,
        planner: FuelPlanner,
        corridor_radius_miles: float,
    ) -> None:
        self._geocoder = geocoder
        self._router = router
        self._stations = stations
        self._planner = planner
        self._corridor_radius_miles = corridor_radius_miles

    def execute(self, start_query: str, finish_query: str) -> FuelRoutePlan:
        start = self._resolve(start_query)
        finish = self._resolve(finish_query)

        route = self._router.get_route(start.coord, finish.coord)

        candidates = find_stations_along_route(
            route.sampled_points,
            self._stations.grid(),
            self._corridor_radius_miles,
        )
        try:
            fuel_plan = self._planner.plan(candidates, route.distance_miles)
        except RouteNotServiceableError as exc:
            raise RouteNotServiceableError(
                str(exc),
                start=start,
                finish=finish,
                route=route,
            ) from exc

        return FuelRoutePlan(start=start, finish=finish, route=route, fuel_plan=fuel_plan)

    def _resolve(self, query: str) -> ResolvedLocation:
        """Accept "lat,lng" directly (zero external calls) or geocode."""
        if match := _COORD_RE.match(query):
            coord = Coordinate(lat=float(match.group(1)), lng=float(match.group(2)))
        else:
            coord = self._geocoder.geocode(query)
        return ResolvedLocation(query=query.strip(), coord=coord)
