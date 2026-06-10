"""Request validation and response presentation (GeoJSON assembly)."""
from __future__ import annotations

from django.conf import settings
from rest_framework import serializers

from routes.application.dto import FuelRoutePlan


class PlanFuelRouteRequestSerializer(serializers.Serializer):
    start = serializers.CharField(
        max_length=200,
        help_text='Start location: free text ("Los Angeles, CA") or "lat,lng".',
    )
    finish = serializers.CharField(
        max_length=200,
        help_text='Finish location: free text ("New York, NY") or "lat,lng".',
    )


def present(result: FuelRoutePlan) -> dict:
    cfg = settings.FUEL_ROUTING
    route, plan = result.route, result.fuel_plan

    stops = [
        {
            "name": p.stop.station.name,
            "address": p.stop.station.address,
            "city": p.stop.station.city,
            "state": p.stop.station.state,
            "location": {
                "lat": p.stop.station.coord.lat,
                "lng": p.stop.station.coord.lng,
            },
            "distance_from_start_miles": round(p.stop.position_miles, 1),
            "price_per_gallon": round(p.stop.station.price_per_gallon, 3),
            "gallons_purchased": round(p.gallons, 2),
            "cost": round(p.cost, 2),
        }
        for p in plan.purchases
    ]

    return {
        "start": _location(result.start.query, result.start.coord),
        "finish": _location(result.finish.query, result.finish.coord),
        "route": {
            "distance_miles": round(route.distance_miles, 1),
            "duration_hours": round(route.duration_seconds / 3600, 1),
        },
        "fuel_plan": {
            "stops": stops,
            "total_gallons": round(plan.total_gallons, 2),
            "total_fuel_cost": round(plan.total_cost, 2),
            "assumptions": {
                "vehicle_range_miles": cfg["VEHICLE_MAX_RANGE_MILES"],
                "miles_per_gallon": cfg["VEHICLE_MPG"],
                "starts_with_full_tank": True,
            },
        },
        "map": _map_geojson(result.start, result.finish, route, stops),
    }


def present_unserviceable(start, finish, route) -> dict:
    """Route context returned alongside a 422 when fuel planning fails."""
    return {
        "start": _location(start.query, start.coord),
        "finish": _location(finish.query, finish.coord),
        "route": {
            "distance_miles": round(route.distance_miles, 1),
            "duration_hours": round(route.duration_seconds / 3600, 1),
        },
        "map": _map_geojson(start, finish, route, stops=[]),
    }


def _location(query: str, coord) -> dict:
    return {"query": query, "lat": coord.lat, "lng": coord.lng}


def _map_geojson(start, finish, route, stops: list[dict]) -> dict:
    """GeoJSON FeatureCollection: paste into geojson.io to see the map."""
    features = [
        {
            "type": "Feature",
            "properties": {"kind": "route"},
            "geometry": {
                "type": "LineString",
                "coordinates": [
                    [c.lng, c.lat] for c in route.geometry
                ],
            },
        },
        _point_feature("start", start.query, start.coord),
        _point_feature("finish", finish.query, finish.coord),
    ]
    features += [
        {
            "type": "Feature",
            "properties": {
                "kind": "fuel_stop",
                "stop_number": i,
                "name": s["name"],
                "price_per_gallon": s["price_per_gallon"],
                "gallons_purchased": s["gallons_purchased"],
                "cost": s["cost"],
            },
            "geometry": {
                "type": "Point",
                "coordinates": [s["location"]["lng"], s["location"]["lat"]],
            },
        }
        for i, s in enumerate(stops, start=1)
    ]
    return {"type": "FeatureCollection", "features": features}


def _point_feature(kind: str, label: str, coord) -> dict:
    return {
        "type": "Feature",
        "properties": {"kind": kind, "name": label},
        "geometry": {"type": "Point", "coordinates": [coord.lng, coord.lat]},
    }
