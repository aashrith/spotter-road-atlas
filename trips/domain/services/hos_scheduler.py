"""HOS timeline simulation for a property-carrying driver (70hr/8day).

Walks the trip's activities (drive legs, pickup, fuel stops, drop-off)
through a clock while enforcing FMCSA limits:

- 11 hours driving per shift, within a 14-hour on-duty window
- 30-minute break once 8 cumulative driving hours accrue without a
  >=30-minute non-driving interruption (post-2020 rule: on-duty
  stops like fueling/pickup also reset the counter)
- 10 consecutive hours off duty reset the shift
- 70-hour/8-day on-duty cycle; when exhausted, a 34-hour restart
  is scheduled (the rolling 8-day recovery is modelled as a budget —
  see README assumptions)

The 14-hour window limits *driving*, not on-duty work, so pickup or
drop-off may finish past the 14th hour as the regulation allows.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from typing import Sequence

from ..entities import DutySegment, TripSchedule, TripStop
from ..value_objects import (
    Activity,
    DriveActivity,
    DutyStatus,
    HosRules,
    StopActivity,
    StopKind,
)

_EPS = 1e-6
_MAX_SEGMENTS = 2000  # safety valve against runaway simulations


class TripTooLongError(Exception):
    """The simulation exceeded any reasonable trip length."""


@dataclass
class _State:
    clock: datetime
    odometer: float = 0.0
    shift_start: datetime | None = None
    driving_this_shift: float = 0.0
    driving_since_break: float = 0.0
    cycle_remaining: float = 0.0


class HosScheduler:
    def __init__(self, rules: HosRules | None = None) -> None:
        self._rules = rules or HosRules()

    def schedule(
        self,
        activities: Sequence[Activity],
        start_time: datetime,
        cycle_used_hours: float,
    ) -> TripSchedule:
        rules = self._rules
        state = _State(
            clock=start_time,
            cycle_remaining=max(0.0, rules.cycle_on_duty_limit_hours - cycle_used_hours),
        )
        segments: list[DutySegment] = []
        stops: list[TripStop] = []

        for activity in activities:
            if isinstance(activity, DriveActivity):
                self._drive(activity, state, segments, stops)
            else:
                self._work_stop(activity, state, segments, stops)

        if not segments:
            raise ValueError("Trip contains no activities.")

        return TripSchedule(
            segments=tuple(segments),
            stops=tuple(stops),
            total_miles=state.odometer,
            cycle_used_at_end_hours=(
                rules.cycle_on_duty_limit_hours - state.cycle_remaining
            ),
        )

    # ----- driving -----

    def _drive(
        self,
        activity: DriveActivity,
        state: _State,
        segments: list[DutySegment],
        stops: list[TripStop],
    ) -> None:
        rules = self._rules
        remaining_hours = activity.hours
        speed = activity.miles / activity.hours if activity.hours > _EPS else 0.0

        while remaining_hours > _EPS:
            if len(segments) > _MAX_SEGMENTS:
                raise TripTooLongError("Trip is too long to schedule.")
            if state.shift_start is None:
                state.shift_start = state.clock

            window_left = rules.driving_window_hours - self._hours_since(
                state.shift_start, state.clock
            )
            chunk = min(
                remaining_hours,
                rules.max_driving_per_shift_hours - state.driving_this_shift,
                window_left,
                rules.driving_before_break_hours - state.driving_since_break,
                state.cycle_remaining,
            )

            if chunk <= _EPS:
                self._insert_required_rest(state, segments, stops, window_left)
                continue

            end = state.clock + timedelta(hours=chunk)
            segments.append(
                DutySegment(
                    status=DutyStatus.DRIVING,
                    start=state.clock,
                    end=end,
                    note=activity.note,
                    miles_from_start=state.odometer,
                )
            )
            state.clock = end
            state.odometer += chunk * speed
            state.driving_this_shift += chunk
            state.driving_since_break += chunk
            state.cycle_remaining -= chunk
            remaining_hours -= chunk

    def _insert_required_rest(
        self,
        state: _State,
        segments: list[DutySegment],
        stops: list[TripStop],
        window_left: float,
    ) -> None:
        rules = self._rules
        break_needed = (
            state.driving_since_break
            >= rules.driving_before_break_hours - _EPS
        )
        shift_exhausted = (
            state.driving_this_shift >= rules.max_driving_per_shift_hours - _EPS
            or window_left <= rules.rest_break_hours + _EPS
        )

        if break_needed and not shift_exhausted:
            self._rest(
                state, segments, stops,
                hours=rules.rest_break_hours,
                status=DutyStatus.OFF_DUTY,
                kind=StopKind.REST_BREAK,
                note="30-minute rest break (required after 8h driving)",
            )
            state.driving_since_break = 0.0
        elif state.cycle_remaining <= _EPS:
            self._rest(
                state, segments, stops,
                hours=rules.cycle_restart_hours,
                status=DutyStatus.OFF_DUTY,
                kind=StopKind.CYCLE_RESTART,
                note="34-hour restart (70hr/8day cycle exhausted)",
            )
            state.cycle_remaining = rules.cycle_on_duty_limit_hours
            self._reset_shift(state)
        else:
            self._rest(
                state, segments, stops,
                hours=rules.daily_rest_hours,
                status=DutyStatus.SLEEPER_BERTH,
                kind=StopKind.OVERNIGHT_REST,
                note="10-hour rest (daily driving limit reached)",
            )
            self._reset_shift(state)

    # ----- on-duty (not driving) stops -----

    def _work_stop(
        self,
        activity: StopActivity,
        state: _State,
        segments: list[DutySegment],
        stops: list[TripStop],
    ) -> None:
        rules = self._rules
        if state.cycle_remaining < activity.hours - _EPS:
            self._rest(
                state, segments, stops,
                hours=rules.cycle_restart_hours,
                status=DutyStatus.OFF_DUTY,
                kind=StopKind.CYCLE_RESTART,
                note="34-hour restart (70hr/8day cycle exhausted)",
            )
            state.cycle_remaining = rules.cycle_on_duty_limit_hours
            self._reset_shift(state)

        if state.shift_start is None:
            state.shift_start = state.clock

        end = state.clock + timedelta(hours=activity.hours)
        segments.append(
            DutySegment(
                status=DutyStatus.ON_DUTY,
                start=state.clock,
                end=end,
                note=activity.note,
                miles_from_start=state.odometer,
            )
        )
        stops.append(
            TripStop(
                kind=activity.kind,
                note=activity.note,
                arrival=state.clock,
                departure=end,
                miles_from_start=state.odometer,
            )
        )
        state.clock = end
        state.cycle_remaining -= activity.hours
        # A non-driving stop of >=30 minutes satisfies the break rule.
        if activity.hours >= rules.rest_break_hours - _EPS:
            state.driving_since_break = 0.0

    # ----- helpers -----

    def _rest(
        self,
        state: _State,
        segments: list[DutySegment],
        stops: list[TripStop],
        hours: float,
        status: DutyStatus,
        kind: StopKind,
        note: str,
    ) -> None:
        end = state.clock + timedelta(hours=hours)
        segments.append(
            DutySegment(
                status=status,
                start=state.clock,
                end=end,
                note=note,
                miles_from_start=state.odometer,
            )
        )
        stops.append(
            TripStop(
                kind=kind,
                note=note,
                arrival=state.clock,
                departure=end,
                miles_from_start=state.odometer,
            )
        )
        state.clock = end
        state.driving_since_break = 0.0

    @staticmethod
    def _reset_shift(state: _State) -> None:
        state.shift_start = None
        state.driving_this_shift = 0.0
        state.driving_since_break = 0.0

    @staticmethod
    def _hours_since(start: datetime, now: datetime) -> float:
        return (now - start).total_seconds() / 3600.0
