from __future__ import annotations

from unittest.mock import Mock, patch

import requests
from django.core.cache import cache
from django.test import SimpleTestCase

from routes.domain.exceptions import GeocodingError
from routes.infrastructure.nominatim import NominatimGeocoder


class NominatimGeocoderTests(SimpleTestCase):
    def setUp(self) -> None:
        cache.clear()
        self.geocoder = NominatimGeocoder()

    @patch("routes.infrastructure.nominatim.requests.get")
    def test_city_state_queries_resolve_offline_without_http(self, mock_get: Mock) -> None:
        coord = self.geocoder.geocode("Dallas, TX")

        self.assertAlmostEqual(coord.lat, 32.78306, places=3)
        self.assertAlmostEqual(coord.lng, -96.80667, places=3)
        mock_get.assert_not_called()

    @patch("routes.infrastructure.nominatim.requests.get")
    def test_non_city_state_queries_fall_back_to_http(self, mock_get: Mock) -> None:
        response = Mock()
        response.json.return_value = [{"lat": "39.7392", "lon": "-104.9903"}]
        response.raise_for_status.return_value = None
        mock_get.return_value = response

        coord = self.geocoder.geocode("1600 Pennsylvania Ave NW, Washington, DC")

        self.assertAlmostEqual(coord.lat, 39.7392, places=4)
        self.assertAlmostEqual(coord.lng, -104.9903, places=4)
        mock_get.assert_called_once()

    @patch("routes.infrastructure.nominatim.requests.get")
    def test_failed_http_geocoding_raises_domain_error(self, mock_get: Mock) -> None:
        mock_get.side_effect = requests.RequestException("boom")

        with self.assertRaises(GeocodingError):
            self.geocoder.geocode("Someplace complex")
