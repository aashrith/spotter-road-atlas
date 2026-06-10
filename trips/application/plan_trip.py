"""Use case: plan a HOS-compliant trip with ELD daily logs.

Pipeline:
1. Resolve current / pickup / dropoff (coords accepted, else geocoded).
2. ONE routing call through all three waypoints.
3. Pick real fuel stations along the corridor with the price optimizer
   (1,000-mile fueling range, per the assessment).
4. Simulate the HOS timeline (breaks, daily rests, cycle restarts).
5. Slice the timeline into driver's-daily-log sheets.
"""
from __future__ import annotations

import re
from datetime import datetime

from routes.application.dto import ResolvedLocation
from routes.application.ports import Geocoder, StationRepository
from routes.domain.entities import FuelPlan, FuelPurchase
from routes.domain.services.fuel_planner import FuelPlanner
from routes.domain.services.geometry import (
    coordinate_at_mile,
    find_stations_along_route,
    haversine_miles,
)
from routes.domain.value_objects import Coordinate

from trips.domain.services.hos_scheduler import HosScheduler
from trips.domain.services.log_sheets import build_day_sheets
from trips.domain.value_objects import (
    Activity,
    DriveActivity,
    StopActivity,
    StopKind,
)

from .dto import LocatedStop, TripPlanResult
from .ports import TripRoute, TripRouter

_COORD_RE = re.compile(r"^\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*$")
_SERVICE_STOP_HOURS = 1.0  # pickup and drop-off each take 1 hour
_FUEL_STOP_HOURS = 0.5


class PlanTrip:
    def __init__(
        self,
        geocoder: Geocoder,
        router: TripRouter,
        stations: StationRepository,
        fuel_planner: FuelPlanner,
        scheduler: HosScheduler,
        corridor_radius_miles: float,
    ) -> None:
        self._geocoder = geocoder
        self._router = router
        self._stations = stations
        self._fuel_planner = fuel_planner
        self._scheduler = scheduler
        self._corridor_radius_miles = corridor_radius_miles

    def execute(
        self,
        current_query: str,
        pickup_query: str,
        dropoff_query: str,
        cycle_used_hours: float,
        start_time: datetime,
    ) -> TripPlanResult:
        current = self._resolve(current_query)
        pickup = self._resolve(pickup_query)
        dropoff = self._resolve(dropoff_query)

        route = self._router.get_trip_route(
            [current.coord, pickup.coord, dropoff.coord]
        )

        fuel_plan = self._plan_fuel(route)
        activities = self._build_activities(route, pickup, dropoff, fuel_plan)
        schedule = self._scheduler.schedule(activities, start_time, cycle_used_hours)
        day_sheets = build_day_sheets(schedule)
        located = self._locate_stops(schedule, route, pickup, dropoff, fuel_plan)

        return TripPlanResult(
            current=current,
            pickup=pickup,
            dropoff=dropoff,
            route=route,
            schedule=schedule,
            day_sheets=day_sheets,
            located_stops=located,
            fuel_plan=fuel_plan,
            start_time=start_time,
            cycle_used_hours=cycle_used_hours,
        )

    # ----- fuel -----

    def _plan_fuel(self, route: TripRoute) -> FuelPlan:
        candidates = find_stations_along_route(
            route.sampled_points,
            self._stations.grid(),
            self._corridor_radius_miles,
        )
        return self._fuel_planner.plan(candidates, route.distance_miles)

    # ----- activity assembly -----

    def _build_activities(
        self,
        route: TripRoute,
        pickup: ResolvedLocation,
        dropoff: ResolvedLocation,
        fuel_plan: FuelPlan,
    ) -> list[Activity]:
        """Cut the route at the pickup and each fuel stop, in mile order."""
        leg_to_pickup, leg_to_dropoff = route.legs
        pickup_mile = leg_to_pickup.distance_miles
        total_miles = route.distance_miles

        cuts: list[tuple[float, StopActivity]] = [
            (
                pickup_mile,
                StopActivity(
                    kind=StopKind.PICKUP,
                    hours=_SERVICE_STOP_HOURS,
                    note=f"Pickup — {pickup.query}",
                ),
            ),
            *(
                (
                    purchase.stop.position_miles,
                    StopActivity(
                        kind=StopKind.FUEL,
                        hours=_FUEL_STOP_HOURS,
                        note=(
                            f"Fuel — {purchase.stop.station.name} "
                            f"({purchase.stop.station.city}, "
                            f"{purchase.stop.station.state})"
                        ),
                    ),
                )
                for purchase in fuel_plan.purchases
            ),
        ]
        cuts.sort(key=lambda c: c[0])

        activities: list[Activity] = []
        previous_mile = 0.0
        for mile, stop in cuts:
            self._append_drive(
                activities, route, previous_mile, mile, pickup_mile
            )
            activities.append(stop)
            previous_mile = mile
        self._append_drive(
            activities, route, previous_mile, total_miles, pickup_mile
        )
        activities.append(
            StopActivity(
                kind=StopKind.DROPOFF,
                hours=_SERVICE_STOP_HOURS,
                note=f"Drop-off — {dropoff.query}",
            )
        )
        return activities

    def _append_drive(
        self,
        activities: list[Activity],
        route: TripRoute,
        from_mile: float,
        to_mile: float,
        pickup_mile: float,
    ) -> None:
        """Append driving between two mile marks, split at the pickup
        boundary so each piece uses its own leg's average speed."""
        leg_to_pickup, leg_to_dropoff = route.legs
        pieces = []
        if from_mile < pickup_mile and to_mile > pickup_mile:
            pieces = [(from_mile, pickup_mile), (pickup_mile, to_mile)]
        else:
            pieces = [(from_mile, to_mile)]

        for start, end in pieces:
            miles = end - start
            if miles <= 0.01:
                continue
            leg = leg_to_pickup if start < pickup_mile else leg_to_dropoff
            speed = (
                leg.distance_miles / leg.duration_hours
                if leg.duration_hours > 0
                else 55.0
            )
            note = "Drive to pickup" if start < pickup_mile else "Drive to drop-off"
            activities.append(
                DriveActivity(miles=miles, hours=miles / speed, note=note)
            )

    # ----- stop coordinates -----

    def _locate_stops(
        self,
        schedule,
        route: TripRoute,
        pickup: ResolvedLocation,
        dropoff: ResolvedLocation,
        fuel_plan: FuelPlan,
    ) -> tuple[LocatedStop, ...]:
        fuel_by_note: dict[str, FuelPurchase] = {
            f"Fuel — {p.stop.station.name} "
            f"({p.stop.station.city}, {p.stop.station.state})": p
            for p in fuel_plan.purchases
        }
        located: list[LocatedStop] = []
        for stop in schedule.stops:
            place = None
            if stop.kind == StopKind.PICKUP:
                coord = pickup.coord
            elif stop.kind == StopKind.DROPOFF:
                coord = dropoff.coord
            elif stop.kind == StopKind.FUEL and stop.note in fuel_by_note:
                station = fuel_by_note[stop.note].stop.station
                coord = station.coord
                place = f"{station.city}, {station.state}"
            else:
                coord = coordinate_at_mile(
                    route.sampled_points, stop.miles_from_start
                )
                place = self._nearest_place(coord)
            located.append(LocatedStop(stop=stop, coord=coord, place=place))
        return tuple(located)

    def _nearest_place(self, coord: Coordinate) -> str | None:
        """Closest known truckstop city — names rest stops on the map."""
        best, best_distance = None, 30.0
        for station in self._stations.grid().near(coord, best_distance):
            distance = haversine_miles(coord, station.coord)
            if distance < best_distance:
                best, best_distance = station, distance
        return f"{best.city}, {best.state}" if best else None

    def _resolve(self, query: str) -> ResolvedLocation:
        if match := _COORD_RE.match(query):
            coord = Coordinate(lat=float(match.group(1)), lng=float(match.group(2)))
        else:
            coord = self._geocoder.geocode(query)
        return ResolvedLocation(query=query.strip(), coord=coord)
