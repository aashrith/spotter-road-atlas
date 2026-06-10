"""Unit tests for the cost-optimal fuel planner (pure domain)."""
from django.test import SimpleTestCase

from routes.domain.exceptions import RouteNotServiceableError
from routes.domain.services.fuel_planner import FuelPlanner
from routes.domain.value_objects import VehicleSpec

from .factories import station_on_route

VEHICLE = VehicleSpec(max_range_miles=500.0, miles_per_gallon=10.0)


class FuelPlannerTests(SimpleTestCase):
    def setUp(self) -> None:
        self.planner = FuelPlanner(VEHICLE)

    def test_no_stops_needed_within_range(self) -> None:
        plan = self.planner.plan([station_on_route(100, 3.0)], trip_miles=400)
        self.assertEqual(plan.purchases, ())
        self.assertEqual(plan.total_cost, 0)

    def test_single_stop_buys_exactly_whats_needed(self) -> None:
        # 600-mile trip, full 500-mile tank: needs 100 more miles = 10 gal.
        plan = self.planner.plan([station_on_route(450, 3.0)], trip_miles=600)
        self.assertEqual(len(plan.purchases), 1)
        purchase = plan.purchases[0]
        self.assertAlmostEqual(purchase.gallons, 10.0, places=3)
        self.assertAlmostEqual(plan.total_cost, 30.0, places=3)

    def test_prefers_cheaper_station_within_reach(self) -> None:
        cheap = station_on_route(400, 2.80, opis_id=1)
        pricey = station_on_route(250, 3.60, opis_id=2)
        plan = self.planner.plan([pricey, cheap], trip_miles=700)
        self.assertEqual(
            [p.stop.station.opis_id for p in plan.purchases], [1]
        )

    def test_buys_minimum_at_expensive_station_to_bridge_to_cheap(self) -> None:
        # Cheap station at mile 600 is beyond initial range. Arriving at the
        # expensive stop (mile 450) with 50 miles of fuel left, the planner
        # should top up only the 100-mile shortfall (10 gal) to reach it.
        expensive = station_on_route(450, 4.00, opis_id=1)
        cheap = station_on_route(600, 2.50, opis_id=2)
        plan = self.planner.plan([expensive, cheap], trip_miles=1000)
        by_station = {p.stop.station.opis_id: p for p in plan.purchases}
        self.assertAlmostEqual(by_station[1].gallons, 10.0, places=3)
        # Remaining 400 miles bought at the cheap station.
        self.assertAlmostEqual(by_station[2].gallons, 40.0, places=3)
        self.assertAlmostEqual(plan.total_cost, 10 * 4.0 + 40 * 2.5, places=3)

    def test_fills_tank_when_no_cheaper_station_ahead(self) -> None:
        # Cheapest station first; everything ahead is pricier -> fill up there.
        cheap = station_on_route(300, 2.50, opis_id=1)
        pricey = station_on_route(700, 3.50, opis_id=2)
        plan = self.planner.plan([cheap, pricey], trip_miles=1100)
        by_station = {p.stop.station.opis_id: p for p in plan.purchases}
        # Fill at cheap: arrives with 200mi left, buys 300mi worth = 30 gal.
        self.assertAlmostEqual(by_station[1].gallons, 30.0, places=3)
        # 1100 total - 800 reachable after fill = 300 more miles at pricey.
        self.assertAlmostEqual(by_station[2].gallons, 30.0, places=3)

    def test_total_equals_fuel_needed_beyond_initial_tank(self) -> None:
        stations = [
            station_on_route(p, 3.0 + (p % 7) * 0.1, opis_id=int(p))
            for p in range(100, 2800, 120)
        ]
        plan = self.planner.plan(stations, trip_miles=2800)
        # Must buy at least (2800 - 500) / 10 gallons; never finish with
        # more than a full tank's worth purchased beyond that.
        self.assertGreaterEqual(plan.total_gallons, 229.999)
        self.assertLessEqual(plan.total_gallons, 280.0)

    def test_unreachable_gap_raises(self) -> None:
        stations = [station_on_route(100, 3.0), station_on_route(900, 3.0)]
        with self.assertRaises(RouteNotServiceableError):
            self.planner.plan(stations, trip_miles=1200)

    def test_no_stations_at_all_raises_for_long_trip(self) -> None:
        with self.assertRaises(RouteNotServiceableError):
            self.planner.plan([], trip_miles=600)
