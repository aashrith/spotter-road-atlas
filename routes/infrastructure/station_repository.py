"""ORM-backed station repository with a process-level cache.

Station data is static reference data (imported once), so the domain
entities and the spatial grid are built once per process and reused —
every API request after the first pays zero DB cost for stations.
"""
from __future__ import annotations

import threading

from routes.domain.entities import FuelStation
from routes.domain.services.geometry import StationGrid
from routes.domain.value_objects import Coordinate
from routes.models import FuelStationRecord


class DjangoStationRepository:
    _lock = threading.Lock()
    _stations: tuple[FuelStation, ...] | None = None
    _grid: StationGrid | None = None

    def all(self) -> tuple[FuelStation, ...]:
        self._ensure_loaded()
        assert self._stations is not None
        return self._stations

    def grid(self) -> StationGrid:
        self._ensure_loaded()
        assert self._grid is not None
        return self._grid

    @classmethod
    def _ensure_loaded(cls) -> None:
        if cls._stations is not None:
            return
        with cls._lock:
            if cls._stations is not None:
                return
            stations = tuple(
                FuelStation(
                    opis_id=record.opis_id,
                    name=record.name,
                    address=record.address,
                    city=record.city,
                    state=record.state,
                    price_per_gallon=float(record.retail_price),
                    coord=Coordinate(lat=record.latitude, lng=record.longitude),
                )
                for record in FuelStationRecord.objects.all().iterator()
            )
            cls._grid = StationGrid(stations)
            cls._stations = stations

    @classmethod
    def invalidate_cache(cls) -> None:
        with cls._lock:
            cls._stations = None
            cls._grid = None
