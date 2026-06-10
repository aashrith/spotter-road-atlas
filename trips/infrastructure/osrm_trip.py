"""OSRM adapter for multi-waypoint trips. One HTTP call per trip."""
from __future__ import annotations

from collections.abc import Sequence

import requests
from django.conf import settings

from routes.domain.exceptions import RoutingError
from routes.domain.services.geometry import sample_route
from routes.domain.value_objects import Coordinate

from trips.application.ports import TripLeg, TripRoute

_METERS_PER_MILE = 1609.344


class OSRMTripRouter:
    def __init__(self) -> None:
        cfg = settings.FUEL_ROUTING
        self._base_url = cfg["OSRM_BASE_URL"].rstrip("/")
        self._timeout = cfg["HTTP_TIMEOUT_SECONDS"]
        self._sample_interval = cfg["ROUTE_SAMPLE_INTERVAL_MILES"]
        self._user_agent = cfg["HTTP_USER_AGENT"]

    def get_trip_route(self, waypoints: Sequence[Coordinate]) -> TripRoute:
        path = ";".join(f"{w.lng},{w.lat}" for w in waypoints)
        url = f"{self._base_url}/route/v1/driving/{path}"
        try:
            response = requests.get(
                url,
                params={"overview": "full", "geometries": "geojson"},
                headers={"User-Agent": self._user_agent},
                timeout=self._timeout,
            )
            response.raise_for_status()
            payload = response.json()
        except requests.RequestException as exc:
            raise RoutingError(f"Routing provider unavailable: {exc}") from exc

        if payload.get("code") != "Ok" or not payload.get("routes"):
            raise RoutingError("No drivable route found through the given locations.")

        osrm_route = payload["routes"][0]
        geometry = tuple(
            Coordinate(lat=lat, lng=lng)
            for lng, lat in osrm_route["geometry"]["coordinates"]
        )
        return TripRoute(
            geometry=geometry,
            sampled_points=sample_route(geometry, self._sample_interval),
            legs=tuple(
                TripLeg(
                    distance_miles=leg["distance"] / _METERS_PER_MILE,
                    duration_hours=leg["duration"] / 3600.0,
                )
                for leg in osrm_route["legs"]
            ),
        )
