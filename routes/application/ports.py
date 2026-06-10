"""Ports (interfaces) the application layer depends on.

Infrastructure provides the adapters; the domain stays framework-free.
"""
from __future__ import annotations

from typing import Protocol

from routes.domain.entities import FuelStation, Route
from routes.domain.services.geometry import StationGrid
from routes.domain.value_objects import Coordinate


class Geocoder(Protocol):
    def geocode(self, query: str) -> Coordinate:
        """Resolve a free-form US location query to coordinates."""


class Router(Protocol):
    def get_route(self, start: Coordinate, finish: Coordinate) -> Route:
        """Fetch a driving route between two coordinates."""


class StationRepository(Protocol):
    def all(self) -> tuple[FuelStation, ...]: ...

    def grid(self) -> StationGrid:
        """Spatial index over all stations (cached per process)."""
