"""Side panel with the undo/redo timeline of the active tab.

Click a step to jump to that state of the document. Each tab keeps its own history;
the panel simply shows the history of whichever tab is active.
"""
from __future__ import annotations

import tkinter as tk
from typing import Any, Callable

from pynotepad.core.history import CommandHistory
from pynotepad.core.observer import Observer, Subject
from pynotepad.ui.theme import Fonts, ThemeManager, observe_theme, px

START_LABEL = "Original document"


class HistoryPanel(tk.Frame, Observer):
    def __init__(self, parent: tk.Misc, themes: ThemeManager, fonts: Fonts) -> None:
        super().__init__(parent, width=px(290))
        self._themes = themes
        self._history: CommandHistory | None = None
        self._title_text = ""

        self._header = tk.Label(self, text="History", anchor="w", font=(fonts.ui, 11, "bold"),
                                padx=px(14), pady=px(10))
        self._header.pack(fill=tk.X)
        self._subtitle = tk.Label(self, anchor="w", font=(fonts.ui, 9), padx=px(14))
        self._subtitle.pack(fill=tk.X)
        self._list = tk.Listbox(self, activestyle="none", exportselection=False, borderwidth=0,
                                highlightthickness=0, font=(fonts.ui, 10), selectborderwidth=0)
        self._list.pack(fill=tk.BOTH, expand=True, padx=px(8), pady=px(8))
        self._hint = tk.Label(self, text="Click a step to go back or forward.", anchor="w",
                              font=(fonts.ui, 9), padx=px(14), pady=px(8), wraplength=px(260), justify="left")
        self._hint.pack(fill=tk.X)
        self.pack_propagate(False)
        self._list.bind("<<ListboxSelect>>", self._on_click)
        self._jumping = False
        observe_theme(self, themes, self._restyle)

    def show(self, history: CommandHistory | None, title: str) -> None:
        """Displays the history of another tab."""
        if self._history is not None:
            self._history.detach(self)
        self._history = history
        self._title_text = title
        if history is not None:
            history.attach(self)
        self._refresh()

    def set_title(self, title: str) -> None:
        self._title_text = title
        self._refresh_subtitle()

    def update(self, subject: Subject, event: Any = None) -> None:
        self._refresh()

    def _refresh(self) -> None:
        theme = self._themes.theme
        self._list.delete(0, tk.END)
        history = self._history
        if history is None:
            return
        self._list.insert(tk.END, f"  {START_LABEL}")
        for number, (description, applied) in enumerate(history.entries, start=1):
            self._list.insert(tk.END, f"  {number}.  {description}")
            if not applied:  # undone steps are dimmed
                self._list.itemconfig(number, foreground=theme.muted)
        for index in range(self._list.size()):
            self._list.itemconfig(index, selectbackground=theme.selection, selectforeground=theme.text)
        self._list.selection_clear(0, tk.END)
        self._list.selection_set(history.done_count)
        self._list.see(history.done_count)
        self._refresh_subtitle()

    def _refresh_subtitle(self) -> None:
        history = self._history
        steps = f"{history.done_count} of {len(history.entries)} steps applied" if history else ""
        self._subtitle.configure(text=f"{self._title_text}  ·  {steps}" if self._title_text else steps)

    def _on_click(self, event: tk.Event) -> None:
        chosen = self._list.curselection()
        if chosen and self._history is not None and chosen[0] != self._history.done_count:
            self._history.go_to(chosen[0])
            self.event_generate("<<HistoryJump>>")

    def _restyle(self) -> None:
        theme = self._themes.theme
        for widget in (self, self._header, self._subtitle, self._hint):
            widget.configure(background=theme.chrome)
        self._header.configure(foreground=theme.text)
        self._subtitle.configure(foreground=theme.muted)
        self._hint.configure(foreground=theme.muted)
        self._list.configure(background=theme.toolbar, foreground=theme.text)
        self._refresh()
