from pathlib import Path

from pomodoro.storage import AppConfig, PomodoroConfig, Preset, load_config, save_config


def test_load_missing_file_returns_defaults(tmp_path: Path) -> None:
    config = load_config(tmp_path / "missing.json")
    names = [p.name for p in config.presets]
    assert "25 minutes" in names
    assert "1 hour" in names
    assert config.pomodoro.work == 25 * 60


def test_save_and_load_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    config = AppConfig(
        presets=[Preset(id="abc", name="Sprint", seconds=1800)],
        pomodoro=PomodoroConfig(work=20 * 60, long_every=3),
    )
    save_config(config, path)
    loaded = load_config(path)
    assert loaded.presets[0].name == "Sprint"
    assert loaded.presets[0].seconds == 1800
    assert loaded.pomodoro.long_every == 3
    assert path.exists()
    assert not path.with_suffix(".json.tmp").exists()
