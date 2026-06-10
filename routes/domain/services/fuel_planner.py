"""Cost-optimal fuel-stop planning.

Implements the classic "gas station problem" greedy strategy, which is
provably cost-optimal for a fixed set of stops along a line:

  At the current station, look at every station reachable on a full tank.
  - If a *cheaper* station is reachable, buy just enough fuel to get there.
  - Otherwise fill the tank and drive to the cheapest reachable station.

The vehicle starts with a full tank; every gallon bought en route is
purchased at the cheapest opportunity the range constraint allows.
"""
from __future__ import annotations

from collections.abc import Sequence

from ..entities import FuelPlan, FuelPurchase, StationOnRoute
from ..exceptions import RouteNotServiceableError
from ..value_objects import VehicleSpec

_EPS = 1e-6


class FuelPlanner:
    def __init__(self, vehicle: VehicleSpec) -> None:
        self._vehicle = vehicle

    def plan(
        self, stations: Sequence[StationOnRoute], trip_miles: float
    ) -> FuelPlan:
        vehicle = self._vehicle
        usable = sorted(
            (s for s in stations if 0.0 < s.position_miles < trip_miles),
            key=lambda s: s.position_miles,
        )

        position = 0.0
        fuel_miles = vehicle.max_range_miles  # full tank at the start
        purchases: list[FuelPurchase] = []

        for _ in range(len(usable) + 1):
            if position + fuel_miles + _EPS >= trip_miles:
                return FuelPlan(purchases=tuple(purchases))

            stop = self._cheapest_reachable(usable, position, fuel_miles)
            fuel_miles -= stop.position_miles - position
            position = stop.position_miles

            buy_miles = self._miles_to_buy(usable, stop, position, fuel_miles, trip_miles)
            if buy_miles > _EPS:
                gallons = buy_miles / vehicle.miles_per_gallon
                purchases.append(
                    FuelPurchase(
                        stop=stop,
                        gallons=gallons,
                        cost=gallons * stop.station.price_per_gallon,
                    )
                )
                fuel_miles += buy_miles

        raise RouteNotServiceableError("Fuel planning did not converge.")

    def _cheapest_reachable(
        self,
        usable: Sequence[StationOnRoute],
        position: float,
        fuel_miles: float,
    ) -> StationOnRoute:
        reachable = [
            s
            for s in usable
            if position < s.position_miles <= position + fuel_miles + _EPS
        ]
        if not reachable:
            raise RouteNotServiceableError(
                f"No fuel station reachable beyond mile {position:.0f} "
                f"with {fuel_miles:.0f} miles of range."
            )
        # Cheapest price wins; on ties prefer the station further along.
        return min(
            reachable,
            key=lambda s: (s.station.price_per_gallon, -s.position_miles),
        )

    def _miles_to_buy(
        self,
        usable: Sequence[StationOnRoute],
        stop: StationOnRoute,
        position: float,
        fuel_miles: float,
        trip_miles: float,
    ) -> float:
        """Buy just enough to reach the next cheaper station, else fill up
        (capped at what is needed to finish the trip)."""
        max_range = self._vehicle.max_range_miles
        next_cheaper = next(
            (
                s.position_miles
                for s in usable
                if position < s.position_miles <= position + max_range + _EPS
                and s.station.price_per_gallon < stop.station.price_per_gallon
            ),
            None,
        )
        target = min(next_cheaper or trip_miles, trip_miles)
        desired_fuel = min(target - position, max_range)
        return max(0.0, desired_fuel - fuel_miles)
