"""Domain entities for the scheduled trip."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from .value_objects import DutyStatus, StopKind


@dataclass(frozen=True, slots=True)
class DutySegment:
    status: DutyStatus
    start: datetime
    end: datetime
    note: str
    miles_from_start: float  # odometer position when the segment starts

    @property
    def hours(self) -> float:
        return (self.end - self.start).total_seconds() / 3600.0


@dataclass(frozen=True, slots=True)
class TripStop:
    kind: StopKind
    note: str
    arrival: datetime
    departure: datetime
    miles_from_start: float


@dataclass(frozen=True, slots=True)
class DaySheet:
    """One driver's-daily-log sheet: a calendar day of duty segments."""

    day: date
    segments: tuple[DutySegment, ...]
    miles_driven: float

    def total_hours(self, status: DutyStatus) -> float:
        return sum(s.hours for s in self.segments if s.status == status)


@dataclass(frozen=True, slots=True)
class TripSchedule:
    segments: tuple[DutySegment, ...]
    stops: tuple[TripStop, ...]
    total_miles: float
    cycle_used_at_end_hours: float

    @property
    def start(self) -> datetime:
        return self.segments[0].start

    @property
    def end(self) -> datetime:
        return self.segments[-1].end
