from __future__ import annotations

from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from routes.container import build_plan_fuel_route
from routes.domain.exceptions import (
    GeocodingError,
    RouteNotServiceableError,
    RoutingError,
)

from .serializers import PlanFuelRouteRequestSerializer, present, present_unserviceable

_ERROR_STATUS = {
    GeocodingError: status.HTTP_400_BAD_REQUEST,
    RouteNotServiceableError: status.HTTP_422_UNPROCESSABLE_ENTITY,
    RoutingError: status.HTTP_502_BAD_GATEWAY,
}


class PlanFuelRouteView(APIView):
    """GET/POST /api/v1/fuel-route — plan a cost-optimal fuel route."""

    def get(self, request: Request) -> Response:
        return self._plan(request.query_params)

    def post(self, request: Request) -> Response:
        return self._plan(request.data)

    def _plan(self, data) -> Response:
        serializer = PlanFuelRouteRequestSerializer(data=data)
        serializer.is_valid(raise_exception=True)

        use_case = build_plan_fuel_route()
        try:
            result = use_case.execute(
                serializer.validated_data["start"],
                serializer.validated_data["finish"],
            )
        except RouteNotServiceableError as exc:
            body = {"error": str(exc)}
            if exc.start and exc.finish and exc.route:
                body.update(present_unserviceable(exc.start, exc.finish, exc.route))
            return Response(body, status=_ERROR_STATUS[type(exc)])
        except (GeocodingError, RoutingError) as exc:
            return Response(
                {"error": str(exc)}, status=_ERROR_STATUS[type(exc)]
            )
        return Response(present(result))
