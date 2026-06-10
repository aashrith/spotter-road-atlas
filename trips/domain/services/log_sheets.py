"""Split a trip schedule into driver's-daily-log sheets (one per calendar day)."""
from __future__ import annotations

from datetime import datetime, time, timedelta

from ..entities import DaySheet, DutySegment, TripSchedule
from ..value_objects import DutyStatus


def build_day_sheets(schedule: TripSchedule) -> tuple[DaySheet, ...]:
    """Slice duty segments at midnight boundaries into daily sheets.

    Time standard of the home terminal is assumed (naive local time),
    matching how a paper log's 24-hour grid is filled in.
    """
    sheets: list[DaySheet] = []
    day = schedule.start.date()
    last_day = schedule.end.date()

    while day <= last_day:
        day_start = datetime.combine(day, time.min)
        day_end = day_start + timedelta(days=1)

        clipped = [
            DutySegment(
                status=seg.status,
                start=max(seg.start, day_start),
                end=min(seg.end, day_end),
                note=seg.note,
                miles_from_start=seg.miles_from_start,
            )
            for seg in schedule.segments
            if seg.start < day_end and seg.end > day_start
        ]
        if clipped:
            clipped = _pad_to_full_day(clipped, day_start, day_end)
            sheets.append(
                DaySheet(
                    day=day,
                    segments=tuple(clipped),
                    miles_driven=_miles_driven(schedule, day_start, day_end),
                )
            )
        day += timedelta(days=1)

    return tuple(sheets)


def _pad_to_full_day(
    segments: list[DutySegment], day_start: datetime, day_end: datetime
) -> list[DutySegment]:
    """A paper log covers all 24 hours: time before the first activity and
    after the last one is recorded as Off Duty."""
    padded = list(segments)
    first, last = padded[0], padded[-1]
    if first.start > day_start:
        padded.insert(
            0,
            DutySegment(
                status=DutyStatus.OFF_DUTY,
                start=day_start,
                end=first.start,
                note="Off duty",
                miles_from_start=first.miles_from_start,
            ),
        )
    if last.end < day_end:
        padded.append(
            DutySegment(
                status=DutyStatus.OFF_DUTY,
                start=last.end,
                end=day_end,
                note="Off duty",
                miles_from_start=last.miles_from_start,
            )
        )
    return padded


def _miles_driven(
    schedule: TripSchedule, day_start: datetime, day_end: datetime
) -> float:
    """Miles covered within the day, prorating segments that cross midnight."""
    miles = 0.0
    segments = schedule.segments
    for i, seg in enumerate(segments):
        if seg.status != DutyStatus.DRIVING or seg.hours <= 0:
            continue
        overlap_start = max(seg.start, day_start)
        overlap_end = min(seg.end, day_end)
        if overlap_end <= overlap_start:
            continue
        next_odometer = (
            segments[i + 1].miles_from_start
            if i + 1 < len(segments)
            else schedule.total_miles
        )
        seg_miles = next_odometer - seg.miles_from_start
        overlap_hours = (overlap_end - overlap_start).total_seconds() / 3600.0
        miles += seg_miles * (overlap_hours / seg.hours)
    return miles
