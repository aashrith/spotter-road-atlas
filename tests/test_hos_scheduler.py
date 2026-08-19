"""Unit tests for the HOS scheduler (pure domain)."""
from datetime import datetime

from django.test import SimpleTestCase

from trips.domain.services.hos_scheduler import HosScheduler
from trips.domain.services.log_sheets import build_day_sheets
from trips.domain.value_objects import (
    DriveActivity,
    DutyStatus,
    StopActivity,
    StopKind,
)

START = datetime(2026, 6, 15, 8, 0)


def _drive(miles: float, mph: float = 55.0, note: str = "Drive") -> DriveActivity:
    return DriveActivity(miles=miles, hours=miles / mph, note=note)


def _pickup() -> StopActivity:
    return StopActivity(kind=StopKind.PICKUP, hours=1.0, note="Pickup")


def _dropoff() -> StopActivity:
    return StopActivity(kind=StopKind.DROPOFF, hours=1.0, note="Drop-off")


class HosSchedulerTests(SimpleTestCase):
    def setUp(self) -> None:
        self.scheduler = HosScheduler()

    def _statuses(self, schedule):
        return [s.status for s in schedule.segments]

    def test_short_trip_fits_one_shift(self) -> None:
        schedule = self.scheduler.schedule(
            [_drive(110), _pickup(), _drive(220), _dropoff()], START, 0.0
        )
        self.assertEqual(
            self._statuses(schedule),
            [
                DutyStatus.DRIVING,
                DutyStatus.ON_DUTY,
                DutyStatus.DRIVING,
                DutyStatus.ON_DUTY,
            ],
        )
        # 6h driving + 2h stops
        self.assertAlmostEqual(
            (schedule.end - schedule.start).total_seconds() / 3600, 8.0, places=2
        )

    def test_break_after_8h_driving(self) -> None:
        # 9 hours of continuous driving must include a 30-min break at 8h.
        schedule = self.scheduler.schedule([_drive(495)], START, 0.0)
        statuses = self._statuses(schedule)
        self.assertEqual(
            statuses,
            [DutyStatus.DRIVING, DutyStatus.OFF_DUTY, DutyStatus.DRIVING],
        )
        self.assertAlmostEqual(schedule.segments[0].hours, 8.0, places=3)
        self.assertAlmostEqual(schedule.segments[1].hours, 0.5, places=3)

    def test_on_duty_stop_resets_break_clock(self) -> None:
        # 7h drive + 1h pickup + 7h drive: pickup interrupts driving,
        # so no 30-minute break is required at all.
        schedule = self.scheduler.schedule(
            [_drive(385), _pickup(), _drive(165)], START, 0.0
        )
        statuses = self._statuses(schedule)
        self.assertNotIn(DutyStatus.OFF_DUTY, statuses)

    def test_daily_driving_limit_forces_10h_rest(self) -> None:
        # 12 hours of driving cannot fit in one shift (11h max).
        schedule = self.scheduler.schedule([_drive(660)], START, 0.0)
        statuses = self._statuses(schedule)
        self.assertIn(DutyStatus.SLEEPER_BERTH, statuses)
        rest = next(
            s for s in schedule.segments if s.status == DutyStatus.SLEEPER_BERTH
        )
        self.assertAlmostEqual(rest.hours, 10.0, places=3)
        # Driving before the rest totals exactly 11 hours.
        driven_before = sum(
            s.hours
            for s in schedule.segments
            if s.status == DutyStatus.DRIVING and s.end <= rest.start
        )
        self.assertAlmostEqual(driven_before, 11.0, places=3)

    def test_cycle_exhaustion_forces_34h_restart(self) -> None:
        # Only 2 cycle hours left: a 5-hour drive needs a restart.
        schedule = self.scheduler.schedule([_drive(275)], START, 68.0)
        restart = [
            s
            for s in schedule.segments
            if s.status == DutyStatus.OFF_DUTY and s.hours >= 34.0 - 1e-6
        ]
        self.assertEqual(len(restart), 1)
        self.assertAlmostEqual(
            schedule.cycle_used_at_end_hours, 3.0, places=2
        )

    def test_14h_window_blocks_driving_after_long_stops(self) -> None:
        # 6h drive, three 2h stops (=12h window used), then 6h more drive:
        # window closes mid-second-drive, forcing a 10h rest even though
        # only 6h of the 11h daily driving was used.
        long_stop = StopActivity(kind=StopKind.FUEL, hours=2.0, note="Dock wait")
        schedule = self.scheduler.schedule(
            [_drive(330), long_stop, long_stop, long_stop, _drive(330)],
            START,
            0.0,
        )
        self.assertIn(DutyStatus.SLEEPER_BERTH, self._statuses(schedule))

    def test_odometer_total_matches_input(self) -> None:
        schedule = self.scheduler.schedule(
            [_drive(110), _pickup(), _drive(1100), _dropoff()], START, 0.0
        )
        self.assertAlmostEqual(schedule.total_miles, 1210.0, places=1)


class DaySheetTests(SimpleTestCase):
    def test_sheets_cover_every_day_and_split_at_midnight(self) -> None:
        scheduler = HosScheduler()
        schedule = scheduler.schedule(
            [_drive(110), _pickup(), _drive(1650), _dropoff()], START, 0.0
        )
        sheets = build_day_sheets(schedule)

        self.assertGreaterEqual(len(sheets), 3)
        for sheet in sheets:
            for seg in sheet.segments:
                self.assertGreaterEqual(seg.start.date(), sheet.day)
                self.assertLessEqual(seg.start.date(), sheet.day)
        # Mileage across sheets reconciles with the trip total.
        self.assertAlmostEqual(
            sum(s.miles_driven for s in sheets), 1760.0, delta=1.0
        )

    def test_day_hours_sum_to_24_on_full_days(self) -> None:
        scheduler = HosScheduler()
        schedule = scheduler.schedule([_drive(1650)], START, 0.0)
        sheets = build_day_sheets(schedule)
        full_days = sheets[1:-1]
        for sheet in full_days:
            total = sum(seg.hours for seg in sheet.segments)
            self.assertAlmostEqual(total, 24.0, places=2)
