"""Unit tests for geometric services (pure domain)."""
from django.test import SimpleTestCase

from routes.domain.entities import FuelStation
from routes.domain.services.geometry import (
    StationGrid,
    find_stations_along_route,
    haversine_miles,
    sample_route,
)
from routes.domain.value_objects import Coordinate


def _station(opis_id: int, lat: float, lng: float) -> FuelStation:
    return FuelStation(
        opis_id=opis_id,
        name=f"S{opis_id}",
        address="",
        city="",
        state="TX",
        price_per_gallon=3.0,
        coord=Coordinate(lat, lng),
    )


class GeometryTests(SimpleTestCase):
    def test_haversine_known_distance(self) -> None:
        la = Coordinate(34.0522, -118.2437)
        nyc = Coordinate(40.7128, -74.0060)
        self.assertAlmostEqual(haversine_miles(la, nyc), 2445, delta=15)

    def test_sample_route_spacing_and_endpoints(self) -> None:
        # Straight line ~207 miles north; 1 degree latitude ≈ 69.05 miles.
        geometry = [Coordinate(34.0 + i * 0.01, -100.0) for i in range(301)]
        sampled = sample_route(geometry, interval_miles=5.0)
        self.assertEqual(sampled[0].position_miles, 0.0)
        self.assertAlmostEqual(sampled[-1].position_miles, 207.2, delta=1.0)
        gaps = [
            b.position_miles - a.position_miles
            for a, b in zip(sampled, sampled[1:])
        ]
        self.assertTrue(all(4.0 <= g <= 7.0 for g in gaps[:-1]))

    def test_corridor_keeps_near_and_drops_far_stations(self) -> None:
        geometry = [Coordinate(34.0 + i * 0.01, -100.0) for i in range(301)]
        sampled = sample_route(geometry, interval_miles=3.0)
        near = _station(1, 35.0, -100.05)  # ~2.8 mi off-route
        far = _station(2, 35.0, -100.60)  # ~31 mi off-route
        grid = StationGrid([near, far])

        matches = find_stations_along_route(sampled, grid, corridor_radius_miles=10)

        self.assertEqual([m.station.opis_id for m in matches], [1])
        self.assertAlmostEqual(matches[0].position_miles, 69.05, delta=3.5)
        self.assertLess(matches[0].detour_miles, 3.5)

    def test_grid_searches_enough_cells_for_corridor(self) -> None:
        geometry = [Coordinate(34.0, -100.0 + i * 0.01) for i in range(301)]
        sampled = sample_route(geometry, interval_miles=3.0)
        # ~12.5 mi off-route; sits in a cell two steps east of the polyline.
        edge = _station(3, 34.0, -99.72)
        grid = StationGrid([edge])

        matches = find_stations_along_route(sampled, grid, corridor_radius_miles=15)

        self.assertEqual([m.station.opis_id for m in matches], [3])
