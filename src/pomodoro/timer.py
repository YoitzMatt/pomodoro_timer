"""Monotonic countdown engine. UI polls remaining_seconds; do not decrement in widgets."""

from __future__ import annotations

from enum import Enum
from math import ceil
from time import monotonic
from typing import Callable


def format_hms(seconds: float) -> str:
    total = max(0, ceil(seconds - 1e-9) if seconds > 0 else 0)
    hours, rem = divmod(total, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


class TimerState(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"


class TimerEngine:
    def __init__(self) -> None:
        self.state = TimerState.IDLE
        self.label = ""
        self._duration = 0.0
        self._remaining = 0.0
        self._end_monotonic: float | None = None
        self._completed = False
        self.on_complete: Callable[[], None] | None = None

    @property
    def remaining_seconds(self) -> float:
        if self.state == TimerState.RUNNING and self._end_monotonic is not None:
            return max(0.0, self._end_monotonic - monotonic())
        return max(0.0, self._remaining)

    def start(self, seconds: float, label: str = "") -> None:
        if seconds <= 0:
            raise ValueError("Timer duration must be greater than zero")
        self.label = label
        self._duration = float(seconds)
        self._remaining = float(seconds)
        self._end_monotonic = monotonic() + self._remaining
        self._completed = False
        self.state = TimerState.RUNNING

    def pause(self) -> None:
        if self.state != TimerState.RUNNING:
            return
        self._remaining = self.remaining_seconds
        self._end_monotonic = None
        self.state = TimerState.PAUSED

    def resume(self) -> None:
        if self.state != TimerState.PAUSED:
            return
        self._end_monotonic = monotonic() + self._remaining
        self.state = TimerState.RUNNING

    def reset(self) -> None:
        self.state = TimerState.IDLE
        self.label = ""
        self._remaining = 0.0
        self._end_monotonic = None
        self._completed = False

    def poll(self) -> float:
        remaining = self.remaining_seconds
        if (
            self.state == TimerState.RUNNING
            and remaining <= 0
            and not self._completed
        ):
            self._completed = True
            self.state = TimerState.IDLE
            self._remaining = 0.0
            self._end_monotonic = None
            if self.on_complete is not None:
                self.on_complete()
        return remaining
