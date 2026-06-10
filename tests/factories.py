"""Test helpers for building domain objects."""
from __future__ import annotations

from routes.domain.entities import FuelStation, StationOnRoute
from routes.domain.value_objects import Coordinate


def station_on_route(
    position_miles: float,
    price: float,
    opis_id: int | None = None,
    detour_miles: float = 1.0,
) -> StationOnRoute:
    opis_id = opis_id or int(position_miles)
    return StationOnRoute(
        station=FuelStation(
            opis_id=opis_id,
            name=f"Station {opis_id}",
            address="I-00 EXIT 1",
            city="Testville",
            state="TX",
            price_per_gallon=price,
            coord=Coordinate(lat=35.0, lng=-100.0),
        ),
        position_miles=position_miles,
        detour_miles=detour_miles,
    )
