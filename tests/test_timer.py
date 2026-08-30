from time import sleep

import pytest

from pomodoro.timer import TimerEngine, TimerState, format_hms


def test_format_hms_formats_minutes_and_hours() -> None:
    assert format_hms(59) == "00:59"
    assert format_hms(61) == "01:01"
    assert format_hms(3600) == "01:00:00"
    assert format_hms(0.2) == "00:01"


def test_start_rejects_zero_duration() -> None:
    engine = TimerEngine()
    with pytest.raises(ValueError):
        engine.start(0)


def test_start_sets_running_and_remaining() -> None:
    engine = TimerEngine()
    engine.start(120, label="Focus")
    assert engine.state == TimerState.RUNNING
    assert engine.label == "Focus"
    assert 119 <= engine.remaining_seconds <= 120


def test_pause_and_resume_preserve_remaining() -> None:
    engine = TimerEngine()
    engine.start(30)
    sleep(0.05)
    engine.pause()
    assert engine.state == TimerState.PAUSED
    paused = engine.remaining_seconds
    sleep(0.1)
    assert engine.remaining_seconds == pytest.approx(paused, abs=0.01)
    engine.resume()
    assert engine.state == TimerState.RUNNING
    assert engine.remaining_seconds <= paused


def test_reset_returns_to_idle() -> None:
    engine = TimerEngine()
    engine.start(10)
    engine.reset()
    assert engine.state == TimerState.IDLE
    assert engine.remaining_seconds == 0
    assert engine.label == ""


def test_poll_fires_on_complete_once() -> None:
    calls = []
    engine = TimerEngine()
    engine.on_complete = lambda: calls.append(1)
    engine.start(0.05)
    sleep(0.08)
    engine.poll()
    engine.poll()
    assert calls == [1]
    assert engine.state == TimerState.IDLE
