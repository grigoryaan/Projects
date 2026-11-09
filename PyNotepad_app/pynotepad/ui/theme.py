"""Colors, fonts and sizes of the interface.

A Theme is a plain data object (Strategy: the widgets ask it for colors and do not
care which theme it is). ThemeManager is a Subject, so switching between light and
dark is just one more Observer notification: every widget re-colors itself.
"""
from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass
from tkinter import font as tkfont
from typing import Callable

from pynotepad.core.observer import CallbackObserver, Subject


@dataclass(frozen=True)
class Theme:
    name: str
    chrome: str  # window background, tab bar, side panel
    toolbar: str
    border: str
    page: str  # text area background
    text: str
    muted: str
    accent: str
    hover: str
    pressed: str
    active: str  # background of a switched-on tool button
    selection: str
    tab_idle: str
    find_match: str
    find_current: str
    danger: str


LIGHT = Theme(
    name="light", chrome="#eef0f4", toolbar="#f8f9fb", border="#d8dce3", page="#ffffff",
    text="#1f2328", muted="#6b7280", accent="#2563eb", hover="#e4e7ec", pressed="#d3d8e0",
    active="#d6e4ff", selection="#b9d3ff", tab_idle="#e3e6ec", find_match="#fde68a",
    find_current="#fdba74", danger="#dc2626",
)
DARK = Theme(
    name="dark", chrome="#1b1d21", toolbar="#23262b", border="#363a41", page="#16181b",
    text="#e6e8eb", muted="#98a0ab", accent="#6ea8fe", hover="#2e333a", pressed="#3a4049",
    active="#27405f", selection="#2f548a", tab_idle="#1f2226", find_match="#665c14",
    find_current="#9a5313", danger="#f87171",
)
THEMES = {theme.name: theme for theme in (LIGHT, DARK)}


class ThemeManager(Subject):
    def __init__(self, theme: Theme = LIGHT) -> None:
        super().__init__()
        self.theme = theme

    def set(self, theme: Theme) -> None:
        if theme is not self.theme:
            self.theme = theme
            self.notify()

    def toggle(self) -> None:
        self.set(DARK if self.theme is LIGHT else LIGHT)


def observe_theme(widget: tk.Misc, themes: ThemeManager, restyle: Callable[[], None]) -> None:
    """Calls `restyle` now and after every theme change, until the widget is destroyed."""
    observer = CallbackObserver(restyle)
    themes.attach(observer)

    def on_destroy(event: tk.Event) -> None:
        if event.widget is widget:
            themes.detach(observer)

    widget.bind("<Destroy>", on_destroy, add="+")
    restyle()


# ----- scaling ---------------------------------------------------------------

_scale = 1.0


def init_scaling(root: tk.Misc) -> None:
    """Remembers how much larger than 96 dpi the screen is, so sizes stay proportional."""
    global _scale
    _scale = max(1.0, float(root.winfo_fpixels("1i")) / 96.0)


def px(value: float) -> int:
    return max(1, round(value * _scale))


# ----- fonts -----------------------------------------------------------------

UI_FONTS = ("Segoe UI", "SF Pro Text", "Helvetica Neue", "Inter", "Noto Sans", "DejaVu Sans",
            "Liberation Sans", "Arial")
DOCUMENT_FONTS = ("Segoe UI", "Calibri", "Helvetica Neue", "Inter", "Noto Sans", "DejaVu Sans",
                  "Liberation Sans", "Arial")


def available_families(root: tk.Misc) -> list[str]:
    names = {name for name in tkfont.families(root) if not name.startswith("@")}
    return sorted(names, key=str.casefold)


def pick_family(root: tk.Misc, candidates: tuple[str, ...]) -> str:
    """The first installed font of the list (the system default if none is installed)."""
    installed = {name.casefold(): name for name in tkfont.families(root)}
    for candidate in candidates:
        if candidate.casefold() in installed:
            return installed[candidate.casefold()]
    return tkfont.nametofont("TkDefaultFont").actual("family")


@dataclass(frozen=True)
class Fonts:
    ui: str
    document: str

    @classmethod
    def detect(cls, root: tk.Misc) -> Fonts:
        return cls(ui=pick_family(root, UI_FONTS), document=pick_family(root, DOCUMENT_FONTS))


def blend(color: str, other: str, amount: float) -> str:
    """Mixes two #rrggbb colors: amount 0 gives `color`, 1 gives `other`."""
    a = [int(color[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(other[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * amount):02x}" for x, y in zip(a, b))
