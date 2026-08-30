"""Entry point: python -m pomodoro."""


def main() -> None:
    try:
        from pomodoro.ui.app import run
    except ModuleNotFoundError as exc:
        if exc.name == "_tkinter":
            raise SystemExit(
                "Tkinter is not available in this Python build. "
                "Install or use a Python distribution with Tk support."
            ) from exc
        raise
    run()


if __name__ == "__main__":
    main()
