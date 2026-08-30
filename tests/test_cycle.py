from pomodoro.cycle import (
    PomodoroSettings,
    phase_after_break_complete,
    phase_after_work_complete,
    starting_phase,
)


def test_starts_with_work() -> None:
    phase = starting_phase(PomodoroSettings())
    assert phase.kind == "work"
    assert phase.seconds == 25 * 60
    assert phase.work_index == 1


def test_short_break_after_work_until_long_every() -> None:
    settings = PomodoroSettings(long_every=4)
    after_1 = phase_after_work_complete(1, settings)
    after_3 = phase_after_work_complete(3, settings)
    after_4 = phase_after_work_complete(4, settings)
    assert after_1.kind == "short_break"
    assert after_3.kind == "short_break"
    assert after_4.kind == "long_break"
    assert after_4.seconds == 15 * 60


def test_work_follows_break() -> None:
    phase = phase_after_break_complete(2, PomodoroSettings())
    assert phase.kind == "work"
    assert phase.work_index == 3
