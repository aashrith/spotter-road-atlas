"""Pure geometric helpers: distances, route sampling, corridor matching.

Corridor matching uses a spatial hash grid so that matching ~7,000 stations
against a cross-country route stays well under 100ms without external deps.
"""
from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Iterable, Sequence

from ..entities import FuelStation, StationOnRoute
from ..value_objects import Coordinate, RoutePoint

EARTH_RADIUS_MILES = 3958.8
# ~0.2 deg latitude ≈ 13.8 miles; one cell ring around a point covers any
# corridor radius up to that size.
_GRID_CELL_DEGREES = 0.2


def haversine_miles(a: Coordinate, b: Coordinate) -> float:
    lat1, lng1, lat2, lng2 = map(math.radians, (a.lat, a.lng, b.lat, b.lng))
    h = (
        math.sin((lat2 - lat1) / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin((lng2 - lng1) / 2) ** 2
    )
    return 2 * EARTH_RADIUS_MILES * math.asin(math.sqrt(h))


def sample_route(
    geometry: Sequence[Coordinate], interval_miles: float
) -> tuple[RoutePoint, ...]:
    """Walk the polyline and emit a point roughly every `interval_miles`."""
    if not geometry:
        return ()
    points = [RoutePoint(geometry[0], 0.0)]
    travelled = 0.0
    last_emitted = 0.0
    for prev, cur in zip(geometry, geometry[1:]):
        travelled += haversine_miles(prev, cur)
        if travelled - last_emitted >= interval_miles:
            points.append(RoutePoint(cur, travelled))
            last_emitted = travelled
    if points[-1].coord != geometry[-1]:
        points.append(RoutePoint(geometry[-1], travelled))
    return tuple(points)


def coordinate_at_mile(
    sampled_points: Sequence[RoutePoint], mile: float
) -> Coordinate:
    """Interpolate the route coordinate at a given distance from the start."""
    if not sampled_points:
        raise ValueError("Empty route.")
    if mile <= sampled_points[0].position_miles:
        return sampled_points[0].coord
    for prev, cur in zip(sampled_points, sampled_points[1:]):
        if cur.position_miles >= mile:
            span = cur.position_miles - prev.position_miles
            t = (mile - prev.position_miles) / span if span > 0 else 0.0
            return Coordinate(
                lat=prev.coord.lat + (cur.coord.lat - prev.coord.lat) * t,
                lng=prev.coord.lng + (cur.coord.lng - prev.coord.lng) * t,
            )
    return sampled_points[-1].coord


class StationGrid:
    """Spatial hash of stations for O(1) neighbourhood lookups."""

    def __init__(self, stations: Iterable[FuelStation]) -> None:
        self._cells: dict[tuple[int, int], list[FuelStation]] = defaultdict(list)
        for station in stations:
            self._cells[self._cell(station.coord)].append(station)

    @staticmethod
    def _cell(coord: Coordinate) -> tuple[int, int]:
        return (
            int(math.floor(coord.lat / _GRID_CELL_DEGREES)),
            int(math.floor(coord.lng / _GRID_CELL_DEGREES)),
        )

    def near(
        self, coord: Coordinate, corridor_radius_miles: float = 10.0
    ) -> Iterable[FuelStation]:
        row, col = self._cell(coord)
        # One grid cell is ~14 mi of latitude; search far enough to cover the corridor.
        ring = max(1, math.ceil(corridor_radius_miles / (_GRID_CELL_DEGREES * 69.0)))
        for r in range(row - ring, row + ring + 1):
            for c in range(col - ring, col + ring + 1):
                yield from self._cells.get((r, c), ())


def find_stations_along_route(
    sampled_points: Sequence[RoutePoint],
    grid: StationGrid,
    corridor_radius_miles: float,
) -> list[StationOnRoute]:
    """Match stations within `corridor_radius_miles` of the route polyline.

    Each station keeps its closest approach to the route, which also fixes
    its position (distance from the route start) used by the fuel planner.
    """
    best: dict[int, StationOnRoute] = {}
    for point in sampled_points:
        for station in grid.near(point.coord, corridor_radius_miles):
            detour = haversine_miles(point.coord, station.coord)
            if detour > corridor_radius_miles:
                continue
            current = best.get(station.opis_id)
            if current is None or detour < current.detour_miles:
                best[station.opis_id] = StationOnRoute(
                    station=station,
                    position_miles=point.position_miles,
                    detour_miles=detour,
                )
    return sorted(best.values(), key=lambda s: s.position_miles)
