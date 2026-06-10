"""OSRM routing adapter. Exactly one HTTP call per route request."""
from __future__ import annotations

import requests
from django.conf import settings

from routes.domain.entities import Route
from routes.domain.exceptions import RoutingError
from routes.domain.services.geometry import sample_route
from routes.domain.value_objects import Coordinate

_METERS_PER_MILE = 1609.344


class OSRMRouter:
    def __init__(self) -> None:
        cfg = settings.FUEL_ROUTING
        self._base_url = cfg["OSRM_BASE_URL"].rstrip("/")
        self._timeout = cfg["HTTP_TIMEOUT_SECONDS"]
        self._sample_interval = cfg["ROUTE_SAMPLE_INTERVAL_MILES"]
        self._user_agent = cfg["HTTP_USER_AGENT"]

    def get_route(self, start: Coordinate, finish: Coordinate) -> Route:
        url = (
            f"{self._base_url}/route/v1/driving/"
            f"{start.lng},{start.lat};{finish.lng},{finish.lat}"
        )
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
            raise RoutingError("No drivable route found between the given locations.")

        osrm_route = payload["routes"][0]
        geometry = tuple(
            Coordinate(lat=lat, lng=lng)
            for lng, lat in osrm_route["geometry"]["coordinates"]
        )
        return Route(
            geometry=geometry,
            sampled_points=sample_route(geometry, self._sample_interval),
            distance_miles=osrm_route["distance"] / _METERS_PER_MILE,
            duration_seconds=osrm_route["duration"],
        )
