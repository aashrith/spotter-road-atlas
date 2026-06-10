"""Import the OPIS fuel-price CSV and geocode stations offline.

Usage: python manage.py import_stations [--csv path/to/file.csv]
"""
from __future__ import annotations

import csv
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from routes.infrastructure.offline_geocoder import US_STATES, OfflineCityGeocoder
from routes.infrastructure.station_repository import DjangoStationRepository
from routes.models import FuelStationRecord

DEFAULT_CSV = settings.BASE_DIR / "data" / "fuel-prices-for-be-assessment.csv"


class Command(BaseCommand):
    help = "Load fuel stations from the OPIS CSV, geocoding cities offline."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)

    @transaction.atomic
    def handle(self, *args, **options) -> None:
        geocoder = OfflineCityGeocoder()
        records: dict[int, FuelStationRecord] = {}
        skipped_non_us = skipped_unlocated = 0

        with open(options["csv"], newline="", encoding="utf-8-sig") as fh:
            for row in csv.DictReader(fh):
                opis_id = int(row["OPIS Truckstop ID"])
                state = row["State"].strip().upper()
                price = Decimal(row["Retail Price"])

                if state not in US_STATES:
                    skipped_non_us += 1
                    continue

                existing = records.get(opis_id)
                if existing is not None:
                    # Duplicate listing of the same truckstop: keep lowest price.
                    existing.retail_price = min(existing.retail_price, price)
                    continue

                city = row["City"].strip()
                coord = geocoder.locate(city, state)
                if coord is None:
                    skipped_unlocated += 1
                    continue

                records[opis_id] = FuelStationRecord(
                    opis_id=opis_id,
                    name=row["Truckstop Name"].strip(),
                    address=row["Address"].strip(),
                    city=city,
                    state=state,
                    retail_price=price,
                    latitude=coord[0],
                    longitude=coord[1],
                )

        FuelStationRecord.objects.all().delete()
        FuelStationRecord.objects.bulk_create(records.values(), batch_size=1000)
        DjangoStationRepository.invalidate_cache()

        self.stdout.write(
            self.style.SUCCESS(
                f"Imported {len(records)} stations "
                f"(skipped {skipped_non_us} non-US rows, "
                f"{skipped_unlocated} unlocatable rows)."
            )
        )
