"""Tkinter application for saved timers and Pomodoro cycles."""

from __future__ import annotations

import tkinter as tk
from dataclasses import replace
from pathlib import Path
from tkinter import messagebox, simpledialog, ttk
from uuid import uuid4

from pomodoro.cycle import (
    Phase,
    PomodoroSettings,
    phase_after_break_complete,
    phase_after_work_complete,
    starting_phase,
)
from pomodoro.storage import PomodoroConfig, Preset, load_config, save_config
from pomodoro.timer import TimerEngine, TimerState, format_hms

from pomodoro.ui.alert import show_timer_ended


class PresetDialog(simpledialog.Dialog):
    """Modal editor for timer presets."""

    def __init__(self, parent: tk.Misc, preset: Preset | None = None) -> None:
        self.preset = preset
        self.result_value: tuple[str, int] | None = None
        super().__init__(parent, title="Edit preset" if preset else "New preset")

    def body(self, master: ttk.Frame) -> tk.Widget:
        ttk.Label(master, text="Name").grid(row=0, column=0, sticky="w", pady=4)
        ttk.Label(master, text="Hours").grid(row=1, column=0, sticky="w", pady=4)
        ttk.Label(master, text="Minutes").grid(row=2, column=0, sticky="w", pady=4)
        ttk.Label(master, text="Seconds").grid(row=3, column=0, sticky="w", pady=4)

        hours = minutes = seconds = 0
        if self.preset is not None:
            hours, rem = divmod(self.preset.seconds, 3600)
            minutes, seconds = divmod(rem, 60)

        self.name_var = tk.StringVar(value=self.preset.name if self.preset else "")
        self.hours_var = tk.StringVar(value=str(hours))
        self.minutes_var = tk.StringVar(value=str(minutes))
        self.seconds_var = tk.StringVar(value=str(seconds))

        name_entry = ttk.Entry(master, textvariable=self.name_var, width=28)
        name_entry.grid(row=0, column=1, sticky="ew", pady=4)
        ttk.Entry(master, textvariable=self.hours_var, width=10).grid(
            row=1, column=1, sticky="w", pady=4
        )
        ttk.Entry(master, textvariable=self.minutes_var, width=10).grid(
            row=2, column=1, sticky="w", pady=4
        )
        ttk.Entry(master, textvariable=self.seconds_var, width=10).grid(
            row=3, column=1, sticky="w", pady=4
        )
        master.columnconfigure(1, weight=1)
        return name_entry

    def validate(self) -> bool:
        name = self.name_var.get().strip()
        if not name:
            messagebox.showerror("Invalid preset", "Preset name cannot be empty.")
            return False
        try:
            hours = int(self.hours_var.get() or "0")
            minutes = int(self.minutes_var.get() or "0")
            seconds = int(self.seconds_var.get() or "0")
        except ValueError:
            messagebox.showerror("Invalid preset", "Duration fields must be integers.")
            return False
        if min(hours, minutes, seconds) < 0:
            messagebox.showerror("Invalid preset", "Duration fields cannot be negative.")
            return False
        total_seconds = hours * 3600 + minutes * 60 + seconds
        if total_seconds <= 0:
            messagebox.showerror("Invalid preset", "Preset duration must be greater than zero.")
            return False
        self.result_value = (name, total_seconds)
        return True

    def apply(self) -> None:
        return None


class PomodoroApp:
    def __init__(self, config_path: Path | None = None) -> None:
        self.root = tk.Tk()
        self.root.title("Pomodoro Timer")
        self.root.minsize(720, 430)

        self.config_path = config_path
        self.config = load_config(config_path)
        self.engine = TimerEngine()
        self.engine.on_complete = lambda: self.root.after(0, self._handle_completion)

        self.mode_var = tk.StringVar(value="simple")
        self.time_var = tk.StringVar(value="25:00")
        self.current_label_var = tk.StringVar(value="Ready")

        self.work_var = tk.StringVar(value=str(self.config.pomodoro.work // 60))
        self.short_break_var = tk.StringVar(
            value=str(self.config.pomodoro.short_break // 60)
        )
        self.long_break_var = tk.StringVar(value=str(self.config.pomodoro.long_break // 60))
        self.long_every_var = tk.StringVar(value=str(self.config.pomodoro.long_every))

        self.current_phase: Phase | None = None
        self.active_pomodoro_settings: PomodoroSettings | None = None
        self.completed_work = 0

        self._build_ui()
        self._populate_presets()
        self._update_time_display()
        self._refresh_controls()
        self._schedule_poll()

    def _build_ui(self) -> None:
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(0, weight=1)

        left = ttk.Frame(self.root, padding=12)
        left.grid(row=0, column=0, sticky="nsew")
        left.rowconfigure(1, weight=1)

        center = ttk.Frame(self.root, padding=12)
        center.grid(row=0, column=1, sticky="nsew")
        center.columnconfigure(0, weight=1)

        ttk.Label(left, text="Saved timers").grid(row=0, column=0, sticky="w")
        list_frame = ttk.Frame(left)
        list_frame.grid(row=1, column=0, sticky="nsew", pady=(8, 8))
        list_frame.rowconfigure(0, weight=1)
        list_frame.columnconfigure(0, weight=1)

        self.preset_list = tk.Listbox(list_frame, height=12, exportselection=False)
        self.preset_list.grid(row=0, column=0, sticky="nsew")
        self.preset_list.bind("<<ListboxSelect>>", lambda _event: self._on_preset_select())

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.preset_list.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.preset_list.configure(yscrollcommand=scrollbar.set)

        preset_buttons = ttk.Frame(left)
        preset_buttons.grid(row=2, column=0, sticky="ew")
        for column in range(3):
            preset_buttons.columnconfigure(column, weight=1)
        ttk.Button(preset_buttons, text="New", command=self._new_preset).grid(
            row=0, column=0, padx=2, sticky="ew"
        )
        ttk.Button(preset_buttons, text="Edit", command=self._edit_selected_preset).grid(
            row=0, column=1, padx=2, sticky="ew"
        )
        ttk.Button(
            preset_buttons, text="Delete", command=self._delete_selected_preset
        ).grid(row=0, column=2, padx=2, sticky="ew")

        mode_frame = ttk.LabelFrame(center, text="Mode", padding=12)
        mode_frame.grid(row=0, column=0, sticky="ew")
        ttk.Radiobutton(
            mode_frame,
            text="Simple timer",
            value="simple",
            variable=self.mode_var,
            command=self._on_mode_change,
        ).pack(side=tk.LEFT, padx=(0, 12))
        ttk.Radiobutton(
            mode_frame,
            text="Pomodoro cycle",
            value="pomodoro",
            variable=self.mode_var,
            command=self._on_mode_change,
        ).pack(side=tk.LEFT)

        ttk.Label(
            center, textvariable=self.time_var, font=("TkDefaultFont", 34, "bold")
        ).grid(row=1, column=0, pady=(28, 8))
        ttk.Label(center, textvariable=self.current_label_var).grid(row=2, column=0, pady=(0, 18))

        controls = ttk.Frame(center)
        controls.grid(row=3, column=0)
        ttk.Button(controls, text="Start", command=self._start_clicked).pack(
            side=tk.LEFT, padx=4
        )
        self.pause_button = ttk.Button(controls, text="Pause", command=self._toggle_pause)
        self.pause_button.pack(side=tk.LEFT, padx=4)
        ttk.Button(controls, text="Reset", command=self._reset_timer).pack(
            side=tk.LEFT, padx=4
        )

        settings = ttk.LabelFrame(center, text="Pomodoro settings", padding=12)
        settings.grid(row=4, column=0, sticky="ew", pady=(28, 0))
        settings.columnconfigure(1, weight=1)

        ttk.Label(settings, text="Work (minutes)").grid(row=0, column=0, sticky="w", pady=4)
        ttk.Entry(settings, textvariable=self.work_var, width=10).grid(
            row=0, column=1, sticky="w", pady=4
        )
        ttk.Label(settings, text="Short break (minutes)").grid(
            row=1, column=0, sticky="w", pady=4
        )
        ttk.Entry(settings, textvariable=self.short_break_var, width=10).grid(
            row=1, column=1, sticky="w", pady=4
        )
        ttk.Label(settings, text="Long break (minutes)").grid(
            row=2, column=0, sticky="w", pady=4
        )
        ttk.Entry(settings, textvariable=self.long_break_var, width=10).grid(
            row=2, column=1, sticky="w", pady=4
        )
        ttk.Label(settings, text="Long break every N work sessions").grid(
            row=3, column=0, sticky="w", pady=4
        )
        ttk.Entry(settings, textvariable=self.long_every_var, width=10).grid(
            row=3, column=1, sticky="w", pady=4
        )
        ttk.Button(settings, text="Save settings", command=self._save_settings).grid(
            row=4, column=0, columnspan=2, sticky="w", pady=(8, 0)
        )

    def _schedule_poll(self) -> None:
        self.engine.poll()
        self._update_time_display()
        self._refresh_controls()
        self.root.after(200, self._schedule_poll)

    def _refresh_controls(self) -> None:
        paused = self.engine.state == TimerState.PAUSED
        self.pause_button.configure(
            text="Resume" if paused else "Pause",
            state=tk.NORMAL if self.engine.state in {TimerState.RUNNING, TimerState.PAUSED} else tk.DISABLED,
        )

    def _populate_presets(self) -> None:
        current_id = self._selected_preset_id()
        self.preset_list.delete(0, tk.END)
        for preset in self.config.presets:
            self.preset_list.insert(tk.END, f"{preset.name} ({format_hms(preset.seconds)})")
        if not self.config.presets:
            self.time_var.set("00:00")
            self.current_label_var.set("Create a timer preset to begin.")
            return
        selected_index = 0
        if current_id is not None:
            for index, preset in enumerate(self.config.presets):
                if preset.id == current_id:
                    selected_index = index
                    break
        self.preset_list.selection_set(selected_index)
        self.preset_list.activate(selected_index)
        self._on_preset_select()

    def _selected_preset_id(self) -> str | None:
        selection = self.preset_list.curselection()
        if not selection:
            return None
        return self.config.presets[selection[0]].id

    def _selected_preset(self) -> Preset | None:
        selection = self.preset_list.curselection()
        if not selection:
            return None
        return self.config.presets[selection[0]]

    def _on_preset_select(self) -> None:
        preset = self._selected_preset()
        if preset and self.mode_var.get() == "simple" and self.engine.state == TimerState.IDLE:
            self.current_label_var.set(f"Ready: {preset.name}")
            self.time_var.set(format_hms(preset.seconds))

    def _new_preset(self) -> None:
        dialog = PresetDialog(self.root)
        if dialog.result_value is None:
            return
        name, seconds = dialog.result_value
        self.config.presets.append(Preset(id=str(uuid4()), name=name, seconds=seconds))
        self._save_config()
        self._populate_presets()
        self.time_var.set(format_hms(seconds))

    def _edit_selected_preset(self) -> None:
        preset = self._selected_preset()
        if preset is None:
            messagebox.showinfo("Edit preset", "Select a preset first.")
            return
        dialog = PresetDialog(self.root, preset)
        if dialog.result_value is None:
            return
        name, seconds = dialog.result_value
        index = self.config.presets.index(preset)
        self.config.presets[index] = replace(preset, name=name, seconds=seconds)
        self._save_config()
        self._populate_presets()
        self.time_var.set(format_hms(seconds))

    def _delete_selected_preset(self) -> None:
        preset = self._selected_preset()
        if preset is None:
            messagebox.showinfo("Delete preset", "Select a preset first.")
            return
        if not messagebox.askyesno(
            "Delete preset", f"Delete the preset '{preset.name}'?"
        ):
            return
        self.config.presets = [item for item in self.config.presets if item.id != preset.id]
        self._save_config()
        self._populate_presets()
        self._update_time_display()

    def _save_config(self) -> None:
        save_config(self.config, self.config_path)

    def _settings_from_form(self) -> PomodoroSettings:
        try:
            work = int(self.work_var.get())
            short_break = int(self.short_break_var.get())
            long_break = int(self.long_break_var.get())
            long_every = int(self.long_every_var.get())
        except ValueError as exc:
            raise ValueError("Pomodoro settings must be integers.") from exc
        if min(work, short_break, long_break, long_every) <= 0:
            raise ValueError("Pomodoro settings must be greater than zero.")
        return PomodoroSettings(
            work=work * 60,
            short_break=short_break * 60,
            long_break=long_break * 60,
            long_every=long_every,
        )

    def _save_settings(self) -> PomodoroSettings | None:
        try:
            settings = self._settings_from_form()
        except ValueError as exc:
            messagebox.showerror("Invalid settings", str(exc))
            return None
        self.config.pomodoro = PomodoroConfig(
            work=settings.work,
            short_break=settings.short_break,
            long_break=settings.long_break,
            long_every=settings.long_every,
        )
        self._save_config()
        if self.mode_var.get() == "pomodoro" and self.engine.state == TimerState.IDLE:
            self.time_var.set(format_hms(settings.work))
            self.current_label_var.set("Ready: Pomodoro cycle")
        return settings

    def _confirm_replace(self) -> bool:
        if self.engine.state == TimerState.IDLE:
            return True
        return messagebox.askyesno(
            "Replace timer", "A timer is already active. Replace it with a new one?"
        )

    def _on_mode_change(self) -> None:
        if self.engine.state != TimerState.IDLE:
            return
        if self.mode_var.get() == "pomodoro":
            self.current_label_var.set("Ready: Pomodoro cycle")
        else:
            preset = self._selected_preset()
            if preset is not None:
                self.current_label_var.set(f"Ready: {preset.name}")
            else:
                self.current_label_var.set("Create a timer preset to begin.")
        self._update_time_display()

    def _start_clicked(self) -> None:
        if not self._confirm_replace():
            return
        if self.mode_var.get() == "pomodoro":
            settings = self._save_settings()
            if settings is None:
                return
            self.completed_work = 0
            self.active_pomodoro_settings = settings
            self._start_phase(starting_phase(settings))
            return

        preset = self._selected_preset()
        if preset is None:
            messagebox.showinfo("Start timer", "Create or select a preset first.")
            return
        self.completed_work = 0
        self.active_pomodoro_settings = None
        self.current_phase = None
        self.engine.start(preset.seconds, preset.name)
        self.current_label_var.set(f"Running: {preset.name}")
        self._update_time_display()
        self._refresh_controls()

    def _toggle_pause(self) -> None:
        if self.engine.state == TimerState.RUNNING:
            self.engine.pause()
            self.current_label_var.set(f"Paused: {self.engine.label}")
        elif self.engine.state == TimerState.PAUSED:
            self.engine.resume()
            self.current_label_var.set(f"Running: {self.engine.label}")
        self._refresh_controls()

    def _reset_timer(self) -> None:
        self.engine.reset()
        self.current_phase = None
        self.active_pomodoro_settings = None
        self.completed_work = 0
        self._update_time_display()
        preset = self._selected_preset()
        if self.mode_var.get() == "simple" and preset is not None:
            self.current_label_var.set(f"Ready: {preset.name}")
        elif self.mode_var.get() == "pomodoro":
            self.current_label_var.set("Ready: Pomodoro cycle")
        else:
            self.current_label_var.set("Ready")
        self._refresh_controls()

    def _phase_label(self, phase: Phase) -> str:
        if phase.kind == "work":
            return f"Work {phase.work_index}"
        if phase.kind == "long_break":
            return f"Long break after work {phase.work_index}"
        return f"Short break after work {phase.work_index}"

    def _start_phase(self, phase: Phase) -> None:
        self.current_phase = phase
        label = self._phase_label(phase)
        self.engine.start(phase.seconds, label)
        self.current_label_var.set(f"Running: {label}")
        self._update_time_display()
        self._refresh_controls()

    def _handle_completion(self) -> None:
        if self.current_phase is None:
            title = "Timer ended"
            message = f"{self.engine.label or 'Your timer'} has ended."
            self.current_label_var.set("Timer completed.")
            self.time_var.set("00:00")
            show_timer_ended(self.root, title, message, offer_next=False)
            preset = self._selected_preset()
            if preset is not None and self.mode_var.get() == "simple":
                self.time_var.set(format_hms(preset.seconds))
                self.current_label_var.set(f"Ready: {preset.name}")
            return

        completed_phase = self.current_phase
        settings = self.active_pomodoro_settings or self._settings_from_form()
        if completed_phase.kind == "work":
            self.completed_work += 1
            next_phase = phase_after_work_complete(self.completed_work, settings)
        else:
            next_phase = phase_after_break_complete(self.completed_work, settings)

        self.time_var.set("00:00")
        self.current_label_var.set(f"Completed: {self._phase_label(completed_phase)}")
        start_next = show_timer_ended(
            self.root,
            "Pomodoro phase ended",
            f"{self._phase_label(completed_phase)} has ended.",
            offer_next=True,
        )
        if start_next:
            self._start_phase(next_phase)
        else:
            self.current_phase = None
            self.active_pomodoro_settings = None
            self.time_var.set(format_hms(settings.work))
            self.current_label_var.set("Ready: Pomodoro cycle")
            self._refresh_controls()

    def _update_time_display(self) -> None:
        if self.engine.state in {TimerState.RUNNING, TimerState.PAUSED}:
            self.time_var.set(format_hms(self.engine.remaining_seconds))
            return
        if self.current_phase is not None:
            if self.engine.state == TimerState.IDLE:
                self.time_var.set("00:00")
                return
            self.time_var.set(format_hms(self.current_phase.seconds))
            return
        preset = self._selected_preset()
        if self.mode_var.get() == "simple" and preset is not None:
            self.time_var.set(format_hms(preset.seconds))
        elif self.mode_var.get() == "pomodoro":
            try:
                settings = self._settings_from_form()
                self.time_var.set(format_hms(settings.work))
            except ValueError:
                self.time_var.set("00:00")
        elif not self.config.presets:
            self.time_var.set("00:00")

    def run(self) -> None:
        self.root.mainloop()


def run() -> None:
    PomodoroApp().run()
