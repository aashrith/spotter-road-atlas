"""Value objects for HOS (hours-of-service) trip scheduling."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class DutyStatus(str, Enum):
    OFF_DUTY = "off_duty"
    SLEEPER_BERTH = "sleeper_berth"
    DRIVING = "driving"
    ON_DUTY = "on_duty"  # on duty, not driving


class StopKind(str, Enum):
    PICKUP = "pickup"
    DROPOFF = "dropoff"
    FUEL = "fuel"
    REST_BREAK = "rest_break"  # 30-minute break
    OVERNIGHT_REST = "overnight_rest"  # 10-hour daily reset
    CYCLE_RESTART = "cycle_restart"  # 34-hour restart


@dataclass(frozen=True, slots=True)
class HosRules:
    """FMCSA property-carrying driver limits (70hr/8day, no adverse conditions)."""

    max_driving_per_shift_hours: float = 11.0
    driving_window_hours: float = 14.0
    driving_before_break_hours: float = 8.0
    rest_break_hours: float = 0.5
    daily_rest_hours: float = 10.0
    cycle_on_duty_limit_hours: float = 70.0
    cycle_restart_hours: float = 34.0


@dataclass(frozen=True, slots=True)
class DriveActivity:
    """A stretch of driving at constant average speed."""

    miles: float
    hours: float
    note: str


@dataclass(frozen=True, slots=True)
class StopActivity:
    """Planned on-duty (not driving) work: pickup, drop-off, fueling."""

    kind: StopKind
    hours: float
    note: str


Activity = DriveActivity | StopActivity
