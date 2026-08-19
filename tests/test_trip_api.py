"""Trip-plan API tests with stubbed external providers."""
from __future__ import annotations

from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIClient

from routes.domain.exceptions import GeocodingError
from routes.domain.services.geometry import haversine_miles, sample_route
from routes.domain.value_objects import Coordinate
from routes.infrastructure.station_repository import DjangoStationRepository
from routes.models import FuelStationRecord
from trips.application.plan_trip import PlanTrip
from trips.application.ports import TripLeg, TripRoute
from trips.container import build_plan_trip


class StubGeocoder:
    KNOWN = {
        "current city": Coordinate(35.0, -106.0),
        "pickup city": Coordinate(35.0, -104.0),
        "dropoff city": Coordinate(35.0, -84.0),
    }

    def geocode(self, query: str) -> Coordinate:
        try:
            return self.KNOWN[query.lower()]
        except KeyError:
            raise GeocodingError(f"Could not find a US location for '{query}'.")


class StubTripRouter:
    """Straight east-west line through the waypoints at ~55mph."""

    def get_trip_route(self, waypoints) -> TripRoute:
        geometry: list[Coordinate] = []
        legs: list[TripLeg] = []
        for a, b in zip(waypoints, waypoints[1:]):
            steps = 100
            piece = [
                Coordinate(
                    a.lat + (b.lat - a.lat) * i / steps,
                    a.lng + (b.lng - a.lng) * i / steps,
                )
                for i in range(steps + 1)
            ]
            distance = sum(
                haversine_miles(p, q) for p, q in zip(piece, piece[1:])
            )
            legs.append(
                TripLeg(distance_miles=distance, duration_hours=distance / 55.0)
            )
            geometry.extend(piece if not geometry else piece[1:])
        return TripRoute(
            geometry=tuple(geometry),
            sampled_points=sample_route(geometry, 3.0),
            legs=tuple(legs),
        )


def _stubbed_use_case() -> PlanTrip:
    real = build_plan_trip()
    return PlanTrip(
        geocoder=StubGeocoder(),
        router=StubTripRouter(),
        stations=DjangoStationRepository(),
        fuel_planner=real._fuel_planner,
        scheduler=real._scheduler,
        corridor_radius_miles=real._corridor_radius_miles,
    )


class PlanTripApiTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        # Stations along the line every ~2 deg of longitude (~113 mi).
        for i, lng in enumerate(range(-105, -84, 2)):
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
        patcher = patch("trips.api.views.build_plan_trip", _stubbed_use_case)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(DjangoStationRepository.invalidate_cache)

    def _request(self, **overrides):
        payload = {
            "current_location": "Current City",
            "pickup_location": "Pickup City",
            "dropoff_location": "Dropoff City",
            "current_cycle_used_hours": 0,
            "start_time": "2026-06-15T08:00:00",
            **overrides,
        }
        return self.client.post("/api/v1/trip-plan", payload, format="json")

    def test_long_trip_returns_logs_stops_and_map(self) -> None:
        response = self._request()
        self.assertEqual(response.status_code, 200)
        body = response.json()

        # ~1,244 miles total at 55mph -> ~22.6h driving + stops: 3+ days.
        self.assertAlmostEqual(
            body["trip"]["total_distance_miles"], 1244, delta=15
        )
        self.assertGreaterEqual(len(body["daily_logs"]), 3)

        kinds = {s["kind"] for s in body["stops"]}
        self.assertIn("pickup", kinds)
        self.assertIn("dropoff", kinds)
        self.assertIn("fuel", kinds)  # >1,000 miles must include fueling
        self.assertIn("overnight_rest", kinds)

        for sheet in body["daily_logs"]:
            # Statuses on each sheet always sum to <= 24h, and segments tile
            # the day contiguously.
            total = sum(sheet["totals"].values())
            self.assertLessEqual(total, 24.01)
            segs = sheet["segments"]
            for a, b in zip(segs, segs[1:]):
                self.assertAlmostEqual(a["end_hour"], b["start_hour"], places=2)

        # Driving on any sheet never exceeds 11 hours.
        for sheet in body["daily_logs"]:
            self.assertLessEqual(sheet["totals"]["driving"], 11.01)

        kinds_on_map = {
            f["properties"]["kind"] for f in body["map"]["features"]
        }
        self.assertIn("route", kinds_on_map)
        self.assertIn("fuel", kinds_on_map)

    def test_cycle_hours_input_is_respected(self) -> None:
        fresh = self._request(current_cycle_used_hours=0).json()
        tired = self._request(current_cycle_used_hours=69).json()
        # A nearly-exhausted cycle forces a 34h restart -> longer trip
        # (the restart also absorbs a 10h overnight rest, so net ~+24h).
        self.assertGreater(
            tired["trip"]["total_duration_hours"],
            fresh["trip"]["total_duration_hours"] + 20,
        )
        self.assertIn(
            "cycle_restart", {s["kind"] for s in tired["stops"]}
        )

    def test_validation_errors(self) -> None:
        response = self._request(current_cycle_used_hours=80)
        self.assertEqual(response.status_code, 400)
        response = self.client.post("/api/v1/trip-plan", {}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_unknown_location_is_a_400(self) -> None:
        response = self._request(pickup_location="Nowhereville")
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())
