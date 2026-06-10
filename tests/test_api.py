"""API integration tests with stubbed external providers.

External HTTP (Nominatim/OSRM) is stubbed at the port level; everything
else — use case, corridor matching, planner, ORM repository, serializers —
runs for real against a seeded test database.
"""
from __future__ import annotations

from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIClient

from routes.application.plan_fuel_route import PlanFuelRoute
from routes.container import build_plan_fuel_route
from routes.domain.entities import Route
from routes.domain.exceptions import GeocodingError
from routes.domain.services.geometry import haversine_miles, sample_route
from routes.domain.value_objects import Coordinate
from routes.infrastructure.station_repository import DjangoStationRepository
from routes.models import FuelStationRecord

START = Coordinate(35.0, -106.0)


class StubGeocoder:
    KNOWN = {
        "start city": START,
        "finish city": Coordinate(35.0, -90.0),
    }

    def geocode(self, query: str) -> Coordinate:
        try:
            return self.KNOWN[query.lower()]
        except KeyError:
            raise GeocodingError(f"Could not find a US location for '{query}'.")


class StubRouter:
    """Straight east-west line: 1 deg lng at lat 35 ≈ 56.55 miles."""

    def get_route(self, start: Coordinate, finish: Coordinate) -> Route:
        steps = 200
        geometry = tuple(
            Coordinate(
                start.lat + (finish.lat - start.lat) * i / steps,
                start.lng + (finish.lng - start.lng) * i / steps,
            )
            for i in range(steps + 1)
        )
        distance = sum(
            haversine_miles(a, b) for a, b in zip(geometry, geometry[1:])
        )
        return Route(
            geometry=geometry,
            sampled_points=sample_route(geometry, 3.0),
            distance_miles=distance,
            duration_seconds=distance / 60 * 3600,
        )


def _stubbed_use_case() -> PlanFuelRoute:
    real = build_plan_fuel_route()
    return PlanFuelRoute(
        geocoder=StubGeocoder(),
        router=StubRouter(),
        stations=DjangoStationRepository(),
        planner=real._planner,
        corridor_radius_miles=real._corridor_radius_miles,
    )


class PlanFuelRouteApiTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        # Stations every ~2 degrees of longitude along the stub route
        # (~113 miles apart); price varies so the planner has choices.
        for i, lng in enumerate(range(-105, -90, 2)):
            FuelStationRecord.objects.create(
                opis_id=i + 1,
                name=f"TRUCKSTOP {i + 1}",
                address=f"I-40 EXIT {i + 1}",
                city="Testville",
                state="NM",
                retail_price=2.80 + (i % 4) * 0.30,
                latitude=35.02,
                longitude=lng,
            )

    def setUp(self) -> None:
        DjangoStationRepository.invalidate_cache()
        self.client = APIClient()
        patcher = patch(
            "routes.api.views.build_plan_fuel_route", _stubbed_use_case
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(DjangoStationRepository.invalidate_cache)

    def _request(self, **params):
        return self.client.get("/api/v1/fuel-route", params)

    def test_long_route_returns_stops_cost_and_map(self) -> None:
        response = self._request(start="Start City", finish="Finish City")
        self.assertEqual(response.status_code, 200)
        body = response.json()

        self.assertAlmostEqual(body["route"]["distance_miles"], 905, delta=10)
        stops = body["fuel_plan"]["stops"]
        self.assertGreaterEqual(len(stops), 1)
        self.assertGreater(body["fuel_plan"]["total_fuel_cost"], 0)

        # Cost must reconcile: sum of stop costs == total.
        self.assertAlmostEqual(
            sum(s["cost"] for s in stops),
            body["fuel_plan"]["total_fuel_cost"],
            places=1,
        )
        # Total gallons >= fuel needed beyond the initial full tank.
        self.assertGreaterEqual(
            body["fuel_plan"]["total_gallons"],
            (body["route"]["distance_miles"] - 500) / 10 - 0.5,
        )
        # Stops are ordered and within vehicle range of each other.
        positions = [0.0] + [s["distance_from_start_miles"] for s in stops]
        self.assertEqual(positions, sorted(positions))
        for a, b in zip(positions, positions[1:]):
            self.assertLessEqual(b - a, 500)

        kinds = {f["properties"]["kind"] for f in body["map"]["features"]}
        self.assertEqual(kinds, {"route", "start", "finish", "fuel_stop"})

    def test_short_route_needs_no_stops(self) -> None:
        response = self._request(start="Start City", finish="35.0,-99.0")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["fuel_plan"]["stops"], [])
        self.assertEqual(body["fuel_plan"]["total_fuel_cost"], 0)

    def test_coordinates_skip_geocoding(self) -> None:
        response = self._request(start="35.0,-106.0", finish="35.0,-90.0")
        self.assertEqual(response.status_code, 200)

    def test_unknown_location_is_a_400(self) -> None:
        response = self._request(start="Nowhereville", finish="Finish City")
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())

    def test_missing_params_fail_validation(self) -> None:
        response = self._request(start="Start City")
        self.assertEqual(response.status_code, 400)

    def test_unserviceable_route_returns_route_context(self) -> None:
        class FarRouter(StubRouter):
            def get_route(self, start: Coordinate, finish: Coordinate) -> Route:
                geometry = tuple(
                    Coordinate(10.0 + i * 0.01, -50.0) for i in range(901)
                )
                distance = sum(
                    haversine_miles(a, b) for a, b in zip(geometry, geometry[1:])
                )
                return Route(
                    geometry=geometry,
                    sampled_points=sample_route(geometry, 3.0),
                    distance_miles=distance,
                    duration_seconds=distance / 60 * 3600,
                )

        def far_use_case() -> PlanFuelRoute:
            real = build_plan_fuel_route()
            return PlanFuelRoute(
                geocoder=StubGeocoder(),
                router=FarRouter(),
                stations=DjangoStationRepository(),
                planner=real._planner,
                corridor_radius_miles=real._corridor_radius_miles,
            )

        with patch("routes.api.views.build_plan_fuel_route", far_use_case):
            response = self._request(start="Start City", finish="Finish City")

        self.assertEqual(response.status_code, 422)
        body = response.json()
        self.assertIn("error", body)
        self.assertIn("route", body)
        self.assertIn("map", body)
        self.assertNotIn("fuel_plan", body)
        kinds = {f["properties"]["kind"] for f in body["map"]["features"]}
        self.assertEqual(kinds, {"route", "start", "finish"})
