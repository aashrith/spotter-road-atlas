from __future__ import annotations

from datetime import datetime, time

from django.conf import settings
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from routes.domain.exceptions import (
    GeocodingError,
    RouteNotServiceableError,
    RoutingError,
)
from trips.container import build_plan_trip
from trips.domain.services.hos_scheduler import TripTooLongError

from .serializers import PlanTripRequestSerializer, present


class PlanTripView(APIView):
    """POST /api/v1/trip-plan — route + HOS schedule + ELD daily logs."""

    def post(self, request: Request) -> Response:
        serializer = PlanTripRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        start_time = data.get("start_time") or self._default_start()
        if start_time.tzinfo is not None:
            start_time = start_time.replace(tzinfo=None)

        try:
            result = build_plan_trip().execute(
                current_query=data["current_location"],
                pickup_query=data["pickup_location"],
                dropoff_query=data["dropoff_location"],
                cycle_used_hours=data["current_cycle_used_hours"],
                start_time=start_time,
            )
        except GeocodingError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except (RouteNotServiceableError, TripTooLongError) as exc:
            return Response(
                {"error": str(exc)}, status=status.HTTP_422_UNPROCESSABLE_ENTITY
            )
        except RoutingError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        return Response(present(result))

    @staticmethod
    def _default_start() -> datetime:
        hour = settings.TRIP_PLANNING["DEFAULT_START_HOUR"]
        return datetime.combine(datetime.now().date(), time(hour=hour))
