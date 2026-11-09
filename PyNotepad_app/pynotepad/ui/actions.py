"""Named user actions: one place that says what an action is called, what it does
and which shortcut triggers it. Menus, toolbar tooltips, key bindings and the
"Keyboard shortcuts" window are all generated from these objects, so they can
never disagree with each other.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Callable

MAC = sys.platform == "darwin"
KEY_NAMES = {"plus": "+", "minus": "-", "equal": "=", "tab": "Tab", "bracketleft": "[", "bracketright": "]",
             "space": "Space"}


@dataclass
class Action:
    label: str
    run: Callable[[], None]
    key: str | None = None  # lowercase Tk keysym, e.g. "b", "plus", "f3"
    shift: bool = False
    ctrl: bool = True  # False for plain keys such as F3
    text_only: bool = False  # an editing shortcut: only active while the text has the focus
    group: str = ""  # section in the shortcuts window

    @property
    def accelerator(self) -> str:
        if not self.key:
            return ""
        parts = []
        if self.ctrl:
            parts.append("Cmd" if MAC else "Ctrl")
        if self.shift:
            parts.append("Shift")
        name = KEY_NAMES.get(self.key, self.key.upper())
        parts.append(name)
        return "+".join(parts)

    @property
    def tooltip(self) -> str:
        return f"{self.label} ({self.accelerator})" if self.key else self.label
