"""Hybrid geocoding adapter with local-first resolution and caching.

Repeated queries for the same place (common while demoing) hit the cache,
keeping external calls per request at the 2-3 the assessment allows.
"""
from __future__ import annotations

import hashlib
import re

import requests
from django.conf import settings
from django.core.cache import cache

from routes.domain.exceptions import GeocodingError
from routes.domain.value_objects import Coordinate

from .offline_geocoder import OfflineCityGeocoder

_CITY_STATE_RE = re.compile(
    r"^\s*(?P<city>[A-Za-z][A-Za-z .'-]+?)\s*,?\s+(?P<state>[A-Za-z]{2})\s*$"
)


class NominatimGeocoder:
    def __init__(self) -> None:
        cfg = settings.FUEL_ROUTING
        self._base_url = cfg["NOMINATIM_BASE_URL"].rstrip("/")
        self._timeout = cfg["HTTP_TIMEOUT_SECONDS"]
        self._user_agent = cfg["HTTP_USER_AGENT"]
        self._offline = OfflineCityGeocoder()

    def geocode(self, query: str) -> Coordinate:
        normalized = " ".join(query.lower().split())
        cache_key = f"geocode:{hashlib.sha256(normalized.encode('utf-8')).hexdigest()}"
        if cached := cache.get(cache_key):
            return Coordinate(*cached)

        if offline := self._geocode_offline(normalized):
            cache.set(cache_key, (offline.lat, offline.lng))
            return offline

        try:
            response = requests.get(
                f"{self._base_url}/search",
                params={
                    "q": normalized,
                    "format": "jsonv2",
                    "limit": 1,
                    "countrycodes": "us",
                },
                headers={"User-Agent": self._user_agent},
                timeout=self._timeout,
            )
            response.raise_for_status()
            results = response.json()
        except requests.RequestException as exc:
            raise GeocodingError(f"Geocoding provider unavailable: {exc}") from exc

        if not results:
            raise GeocodingError(f"Could not find a US location for '{query}'.")

        coord = Coordinate(lat=float(results[0]["lat"]), lng=float(results[0]["lon"]))
        cache.set(cache_key, (coord.lat, coord.lng))
        return coord

    def _geocode_offline(self, normalized_query: str) -> Coordinate | None:
        match = _CITY_STATE_RE.match(normalized_query)
        if not match:
            return None

        located = self._offline.locate(match.group("city"), match.group("state"))
        if located is None:
            return None
        return Coordinate(lat=located[0], lng=located[1])
