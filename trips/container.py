"""Composition root for the trips context."""
from __future__ import annotations

from django.conf import settings

from routes.domain.services.fuel_planner import FuelPlanner
from routes.domain.value_objects import VehicleSpec
from routes.infrastructure.nominatim import NominatimGeocoder
from routes.infrastructure.station_repository import DjangoStationRepository

from trips.application.plan_trip import PlanTrip
from trips.domain.services.hos_scheduler import HosScheduler
from trips.domain.value_objects import HosRules
from trips.infrastructure.osrm_trip import OSRMTripRouter


def build_plan_trip() -> PlanTrip:
    cfg = settings.FUEL_ROUTING
    trip_cfg = settings.TRIP_PLANNING
    fueling_vehicle = VehicleSpec(
        max_range_miles=trip_cfg["FUELING_RANGE_MILES"],
        miles_per_gallon=cfg["VEHICLE_MPG"],
    )
    return PlanTrip(
        geocoder=NominatimGeocoder(),
        router=OSRMTripRouter(),
        stations=DjangoStationRepository(),
        fuel_planner=FuelPlanner(fueling_vehicle),
        scheduler=HosScheduler(HosRules()),
        corridor_radius_miles=cfg["CORRIDOR_RADIUS_MILES"],
    )
