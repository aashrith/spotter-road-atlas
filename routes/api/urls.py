from django.urls import path

from .views import PlanFuelRouteView

urlpatterns = [
    path("fuel-route", PlanFuelRouteView.as_view(), name="fuel-route"),
]
