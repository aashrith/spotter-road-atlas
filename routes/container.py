"""Composition root: wires infrastructure adapters into the use case."""
from __future__ import annotations

from django.conf import settings

from routes.application.plan_fuel_route import PlanFuelRoute
from routes.domain.services.fuel_planner import FuelPlanner
from routes.domain.value_objects import VehicleSpec
from routes.infrastructure.nominatim import NominatimGeocoder
from routes.infrastructure.osrm import OSRMRouter
from routes.infrastructure.station_repository import DjangoStationRepository


def build_plan_fuel_route() -> PlanFuelRoute:
    cfg = settings.FUEL_ROUTING
    vehicle = VehicleSpec(
        max_range_miles=cfg["VEHICLE_MAX_RANGE_MILES"],
        miles_per_gallon=cfg["VEHICLE_MPG"],
    )
    return PlanFuelRoute(
        geocoder=NominatimGeocoder(),
        router=OSRMRouter(),
        stations=DjangoStationRepository(),
        planner=FuelPlanner(vehicle),
        corridor_radius_miles=cfg["CORRIDOR_RADIUS_MILES"],
    )
