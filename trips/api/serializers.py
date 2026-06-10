"""Request validation and response presentation for trip planning."""
from __future__ import annotations

from rest_framework import serializers

from trips.application.dto import TripPlanResult
from trips.domain.value_objects import DutyStatus


class PlanTripRequestSerializer(serializers.Serializer):
    current_location = serializers.CharField(max_length=200)
    pickup_location = serializers.CharField(max_length=200)
    dropoff_location = serializers.CharField(max_length=200)
    current_cycle_used_hours = serializers.FloatField(min_value=0, max_value=70)
    start_time = serializers.DateTimeField(required=False, allow_null=True)


def present(result: TripPlanResult) -> dict:
    return {
        "trip": {
            "current": _location(result.current),
            "pickup": _location(result.pickup),
            "dropoff": _location(result.dropoff),
            "start_time": result.start_time.isoformat(),
            "arrival_time": result.schedule.end.isoformat(),
            "total_distance_miles": round(result.route.distance_miles, 1),
            "total_duration_hours": round(
                (result.schedule.end - result.schedule.start).total_seconds()
                / 3600.0,
                1,
            ),
            "driving_hours": round(result.route.duration_hours, 1),
            "cycle_used_before_hours": result.cycle_used_hours,
            "cycle_used_after_hours": round(
                result.schedule.cycle_used_at_end_hours, 1
            ),
        },
        "stops": [_stop(located) for located in result.located_stops],
        "fuel": {
            "total_gallons": round(result.fuel_plan.total_gallons, 2),
            "total_cost": round(result.fuel_plan.total_cost, 2),
        },
        "daily_logs": [_day_sheet(sheet) for sheet in result.day_sheets],
        "map": _map_geojson(result),
    }


def _location(resolved) -> dict:
    return {
        "query": resolved.query,
        "lat": resolved.coord.lat,
        "lng": resolved.coord.lng,
    }


def _stop(located) -> dict:
    stop = located.stop
    return {
        "kind": stop.kind.value,
        "note": stop.note,
        "place": located.place,
        "arrival": stop.arrival.isoformat(),
        "departure": stop.departure.isoformat(),
        "duration_hours": round(
            (stop.departure - stop.arrival).total_seconds() / 3600.0, 2
        ),
        "miles_from_start": round(stop.miles_from_start, 1),
        "location": {"lat": located.coord.lat, "lng": located.coord.lng},
    }


def _day_sheet(sheet) -> dict:
    return {
        "date": sheet.day.isoformat(),
        "miles_driven": round(sheet.miles_driven, 1),
        "segments": [
            {
                "status": seg.status.value,
                "start_hour": _hour_of_day(seg.start, sheet.day),
                "end_hour": _hour_of_day(seg.end, sheet.day, end=True),
                "note": seg.note,
            }
            for seg in sheet.segments
        ],
        "totals": {
            status.value: round(sheet.total_hours(status), 2)
            for status in DutyStatus
        },
    }


def _hour_of_day(moment, day, end: bool = False) -> float:
    hours = (
        moment - moment.replace(hour=0, minute=0, second=0, microsecond=0)
    ).total_seconds() / 3600.0
    if end and moment.date() != day:
        return 24.0  # segment runs through midnight
    return round(hours, 3)


def _map_geojson(result: TripPlanResult) -> dict:
    features = [
        {
            "type": "Feature",
            "properties": {"kind": "route"},
            "geometry": {
                "type": "LineString",
                "coordinates": [[c.lng, c.lat] for c in result.route.geometry],
            },
        },
        _point("current", result.current.query, result.current.coord),
        _point("pickup", result.pickup.query, result.pickup.coord),
        _point("dropoff", result.dropoff.query, result.dropoff.coord),
    ]
    features += [
        {
            "type": "Feature",
            "properties": {
                "kind": located.stop.kind.value,
                "name": located.stop.note,
                "arrival": located.stop.arrival.isoformat(),
                "departure": located.stop.departure.isoformat(),
            },
            "geometry": {
                "type": "Point",
                "coordinates": [located.coord.lng, located.coord.lat],
            },
        }
        for located in result.located_stops
        if located.stop.kind.value not in ("pickup", "dropoff")
    ]
    return {"type": "FeatureCollection", "features": features}


def _point(kind: str, name: str, coord) -> dict:
    return {
        "type": "Feature",
        "properties": {"kind": kind, "name": name},
        "geometry": {"type": "Point", "coordinates": [coord.lng, coord.lat]},
    }
