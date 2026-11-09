"""Status bar: a message on the left, document statistics on the right."""
from __future__ import annotations

import tkinter as tk

from pynotepad.ui.theme import Fonts, ThemeManager, observe_theme, px


class StatusBar(tk.Frame):
    MESSAGE_MS = 4000

    def __init__(self, parent: tk.Misc, themes: ThemeManager, fonts: Fonts) -> None:
        super().__init__(parent)
        self._themes = themes
        self._font = (fonts.ui, 9)
        self._message = tk.Label(self, anchor="w", font=self._font, padx=px(12), pady=px(4))
        self._message.pack(side=tk.LEFT)
        self._labels: list[tk.Label] = []
        self._job: str | None = None
        self._cells = ["position", "selection", "words", "characters", "zoom", "encoding"]
        self._cell_labels: dict[str, tk.Label] = {}
        for name in reversed(self._cells):
            label = tk.Label(self, font=self._font, padx=px(10), pady=px(4))
            label.pack(side=tk.RIGHT)
            self._cell_labels[name] = label
        self.bind("<Destroy>", self._cancel_flash, add="+")
        observe_theme(self, themes, self._restyle)

    def _cancel_flash(self, event: tk.Event | None = None) -> None:
        if self._job is not None:
            self.after_cancel(self._job)
            self._job = None

    def set_values(self, **values: str) -> None:
        for name, text in values.items():
            self._cell_labels[name].configure(text=text)

    def flash(self, text: str) -> None:
        """Shows a short message that disappears after a few seconds."""
        self._message.configure(text=text)
        self._cancel_flash()
        self._job = self.after(self.MESSAGE_MS, self._clear_message)

    def _clear_message(self) -> None:
        self._job = None
        self._message.configure(text="")

    def _restyle(self) -> None:
        theme = self._themes.theme
        self.configure(background=theme.chrome)
        for label in (self._message, *self._cell_labels.values()):
            label.configure(background=theme.chrome, foreground=theme.muted)
        self._message.configure(foreground=theme.text)
