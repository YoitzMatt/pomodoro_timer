# Pomodoro Timer

Desktop countdown timer built with Python and Tkinter. Save named presets, run one timer at a time, and optionally cycle through classic pomodoro work/break phases. When a timer ends, an always-on-top popup appears.

## Run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python -m pomodoro
```

## Tests

```bash
python -m pytest
```
