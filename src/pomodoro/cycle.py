"""Classic pomodoro phase sequence."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

PhaseKind = Literal["work", "short_break", "long_break"]


@dataclass(frozen=True)
class PomodoroSettings:
    work: int = 25 * 60
    short_break: int = 5 * 60
    long_break: int = 15 * 60
    long_every: int = 4


@dataclass(frozen=True)
class Phase:
    kind: PhaseKind
    seconds: int
    work_index: int


def starting_phase(settings: PomodoroSettings) -> Phase:
    return Phase("work", settings.work, work_index=1)


def phase_after_work_complete(
    completed_work: int, settings: PomodoroSettings
) -> Phase:
    """Break that follows a just-finished work session (`completed_work` includes it)."""
    if completed_work < 1:
        raise ValueError("completed_work must be >= 1 after finishing work")
    if settings.long_every < 1:
        raise ValueError("long_every must be >= 1")
    if completed_work % settings.long_every == 0:
        return Phase("long_break", settings.long_break, work_index=completed_work)
    return Phase("short_break", settings.short_break, work_index=completed_work)


def phase_after_break_complete(
    completed_work: int, settings: PomodoroSettings
) -> Phase:
    """Work session that follows a break. `completed_work` is works already done."""
    return Phase("work", settings.work, work_index=completed_work + 1)
