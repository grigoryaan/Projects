"""Clipboard that keeps formatting inside the application.

The system clipboard only carries plain text. We also remember the last copied
fragment with its formatting; when the system clipboard still holds exactly that
text, pasting restores the formatting too. Text copied from anywhere else is pasted
as plain text.
"""
from __future__ import annotations

import tkinter as tk

from pynotepad.core.document import Snapshot, normalize_text


class Clipboard:
    def __init__(self, root: tk.Misc) -> None:
        self._root = root
        self._last: Snapshot | None = None

    def put(self, fragment: Snapshot) -> None:
        self._root.clipboard_clear()
        self._root.clipboard_append(fragment.text)
        self._last = fragment

    def get(self) -> str | Snapshot | None:
        """A formatted fragment, plain text, or None when the clipboard is empty."""
        try:
            text = normalize_text(self._root.clipboard_get())
        except tk.TclError:
            return None
        if self._last is not None and self._last.text == text:
            return self._last
        return text or None
