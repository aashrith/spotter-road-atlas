from django.db import models


class FuelStationRecord(models.Model):
    """Persistence model for a fuel station (geocoded once at import time)."""

    opis_id = models.IntegerField(unique=True, db_index=True)
    name = models.CharField(max_length=255)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=120)
    state = models.CharField(max_length=2, db_index=True)
    retail_price = models.DecimalField(max_digits=8, decimal_places=5)
    latitude = models.FloatField()
    longitude = models.FloatField()

    class Meta:
        db_table = "fuel_station"

    def __str__(self) -> str:
        return f"{self.name} ({self.city}, {self.state})"
