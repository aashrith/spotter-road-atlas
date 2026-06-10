"""Offline city/state -> centroid geocoder used only at import time.

Combines two datasets bundled in pip packages (no network, no API keys):
- geonamescache: GeoNames cities with population >= 500
- zipcodes: US ZIP centroids keyed by city/state

City-centroid precision (a few miles) is sufficient for selecting fuel
stops along a highway corridor.
"""
from __future__ import annotations

import re
from functools import lru_cache

import geonamescache
import zipcodes

US_STATES = frozenset(
    "AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS "
    "MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WV WI "
    "WY DC".split()
)


def _normalize(city: str) -> str:
    city = re.sub(r"[.']", "", city.lower().strip())
    return " ".join(city.split())


def _variants(city: str) -> list[str]:
    """Spelling variants to maximise match rate (e.g. 'de forest' -> 'deforest')."""
    seen: list[str] = []
    for candidate in (
        city,
        city.replace(" ", ""),
        city.replace("saint ", "st "),
        city.replace("st ", "saint "),
        city.replace("mount ", "mt "),
        city.replace("mt ", "mount "),
    ):
        if candidate not in seen:
            seen.append(candidate)
    return seen


class OfflineCityGeocoder:
    def __init__(self) -> None:
        self._geonames = self._build_geonames_index()
        self._zips = self._build_zip_index()

    def locate(self, city: str, state: str) -> tuple[float, float] | None:
        state = state.strip().upper()
        if state not in US_STATES:
            return None
        for candidate in _variants(_normalize(city)):
            if coord := self._geonames.get((candidate, state)):
                return coord
            if coord := self._zips.get((candidate, state)):
                return coord
        return None

    @staticmethod
    @lru_cache(maxsize=1)
    def _build_geonames_index() -> dict[tuple[str, str], tuple[float, float]]:
        cities = geonamescache.GeonamesCache(min_city_population=500).get_cities()
        index: dict[tuple[str, str], tuple[float, float]] = {}
        for city in cities.values():
            if city["countrycode"] != "US":
                continue
            key = (_normalize(city["name"]), city["admin1code"])
            # Keep the most populous city on name collisions within a state.
            if key not in index:
                index[key] = (city["latitude"], city["longitude"])
        return index

    @staticmethod
    @lru_cache(maxsize=1)
    def _build_zip_index() -> dict[tuple[str, str], tuple[float, float]]:
        index: dict[tuple[str, str], tuple[float, float]] = {}
        for zip_record in zipcodes.list_all():
            if not (zip_record.get("lat") and zip_record.get("city")):
                continue
            key = (_normalize(zip_record["city"]), zip_record["state"])
            index.setdefault(
                key, (float(zip_record["lat"]), float(zip_record["long"]))
            )
        return index
