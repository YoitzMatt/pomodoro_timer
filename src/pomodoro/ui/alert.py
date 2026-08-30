"""Always-on-top timer completion dialog."""

from __future__ import annotations

import shutil
import subprocess
import sys
import tkinter as tk
from tkinter import ttk


def beep() -> None:
    """Play a short notification sound when available."""
    if sys.platform == "darwin":
        afplay = shutil.which("afplay")
        if afplay:
            subprocess.Popen(
                [afplay, "/System/Library/Sounds/Glass.aiff"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return
    print("\a", end="", flush=True)


def show_timer_ended(
    parent: tk.Misc,
    title: str,
    message: str,
    *,
    offer_next: bool = False,
) -> bool:
    """Show a modal dialog and return True when Start next is chosen."""
    beep()
    result = {"start_next": False}

    dialog = tk.Toplevel(parent)
    dialog.title(title)
    dialog.transient(parent)
    dialog.resizable(False, False)
    dialog.attributes("-topmost", True)

    frame = ttk.Frame(dialog, padding=18)
    frame.pack(fill=tk.BOTH, expand=True)

    ttk.Label(
        frame,
        text=message,
        justify=tk.CENTER,
        anchor=tk.CENTER,
        wraplength=320,
    ).pack(fill=tk.X, expand=True, pady=(0, 16))

    buttons = ttk.Frame(frame)
    buttons.pack()

    def close() -> None:
        dialog.destroy()

    def start_next() -> None:
        result["start_next"] = True
        dialog.destroy()

    ttk.Button(buttons, text="OK", command=close).pack(side=tk.LEFT, padx=4)
    if offer_next:
        ttk.Button(buttons, text="Start next", command=start_next).pack(
            side=tk.LEFT, padx=4
        )

    dialog.protocol("WM_DELETE_WINDOW", close)
    dialog.update_idletasks()

    parent.update_idletasks()
    x = parent.winfo_rootx()
    y = parent.winfo_rooty()
    width = max(parent.winfo_width(), dialog.winfo_reqwidth())
    height = max(parent.winfo_height(), dialog.winfo_reqheight())
    dx = x + (width - dialog.winfo_reqwidth()) // 2
    dy = y + (height - dialog.winfo_reqheight()) // 2
    dialog.geometry(f"+{dx}+{dy}")

    parent.lift()
    dialog.lift()
    dialog.grab_set()
    dialog.focus_force()
    dialog.wait_window()
    return result["start_next"]
