from django.urls import include, path

from routes.views import RoutePlannerPageView

urlpatterns = [
    path("", RoutePlannerPageView.as_view(), name="route-planner"),
    path("api/v1/", include("routes.api.urls")),
]
