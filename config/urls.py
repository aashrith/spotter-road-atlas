from django.http import JsonResponse
from django.urls import include, path


def api_index(_request):
    """Django is a pure API; the React app (frontend/) is the UI."""
    return JsonResponse(
        {
            "service": "spotter-road-atlas API",
            "endpoints": {
                "fuel_route": "/api/v1/fuel-route?start=...&finish=...",
                "trip_plan": "POST /api/v1/trip-plan",
            },
        }
    )


urlpatterns = [
    path("", api_index, name="api-index"),
    path("api/v1/", include("routes.api.urls")),
    path("api/v1/", include("trips.api.urls")),
]
