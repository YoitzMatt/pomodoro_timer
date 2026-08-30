"""Load and save presets and pomodoro settings as JSON."""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


DEFAULT_PRESETS = (
    ("25 minutes", 25 * 60),
    ("30 minutes", 30 * 60),
    ("1 hour", 60 * 60),
    ("5 minutes", 5 * 60),
)


@dataclass
class Preset:
    id: str
    name: str
    seconds: int


@dataclass
class PomodoroConfig:
    work: int = 25 * 60
    short_break: int = 5 * 60
    long_break: int = 15 * 60
    long_every: int = 4


@dataclass
class AppConfig:
    presets: list[Preset]
    pomodoro: PomodoroConfig


def default_config_path() -> Path:
    return Path.home() / ".pomodoro_timer" / "config.json"


def default_config() -> AppConfig:
    presets = [
        Preset(id=str(uuid.uuid4()), name=name, seconds=seconds)
        for name, seconds in DEFAULT_PRESETS
    ]
    return AppConfig(presets=presets, pomodoro=PomodoroConfig())


def _to_dict(config: AppConfig) -> dict[str, Any]:
    return {
        "presets": [asdict(p) for p in config.presets],
        "pomodoro": asdict(config.pomodoro),
    }


def _from_dict(data: dict[str, Any]) -> AppConfig:
    presets = [
        Preset(id=p["id"], name=p["name"], seconds=int(p["seconds"]))
        for p in data.get("presets", [])
    ]
    pomo = data.get("pomodoro") or {}
    pomodoro = PomodoroConfig(
        work=int(pomo.get("work", 25 * 60)),
        short_break=int(pomo.get("short_break", 5 * 60)),
        long_break=int(pomo.get("long_break", 15 * 60)),
        long_every=int(pomo.get("long_every", 4)),
    )
    return AppConfig(presets=presets, pomodoro=pomodoro)


def load_config(path: Path | None = None) -> AppConfig:
    path = path or default_config_path()
    if not path.exists():
        return default_config()
    with path.open(encoding="utf-8") as fh:
        return _from_dict(json.load(fh))


def save_config(config: AppConfig, path: Path | None = None) -> None:
    path = path or default_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(_to_dict(config), indent=2)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(payload, encoding="utf-8")
    os.replace(tmp, path)
