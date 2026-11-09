"""Small reusable widgets: tool button, tooltip, text button, separator, color popup."""
from __future__ import annotations

import tkinter as tk
from tkinter import colorchooser
from tkinter import font as tkfont
from typing import Callable

from pynotepad.ui.icons import Icon
from pynotepad.ui.theme import Fonts, ThemeManager, blend, observe_theme, px


class Tooltip:
    """Small hint that appears when the mouse rests on a widget."""

    DELAY_MS = 550

    def __init__(self, widget: tk.Misc, themes: ThemeManager, text: str = "") -> None:
        self._widget = widget
        self._themes = themes
        self.text = text
        self._job: str | None = None
        self._window: tk.Toplevel | None = None
        widget.bind("<Enter>", self._schedule, add="+")
        widget.bind("<Leave>", self._hide, add="+")
        widget.bind("<ButtonPress>", self._hide, add="+")
        widget.bind("<Destroy>", self._hide, add="+")

    def _schedule(self, event: tk.Event | None = None) -> None:
        self._hide()
        if self.text:
            self._job = self._widget.after(self.DELAY_MS, self._show)

    def _show(self) -> None:
        theme = self._themes.theme
        window = tk.Toplevel(self._widget)
        window.wm_overrideredirect(True)
        window.configure(background=theme.border)
        tk.Label(window, text=self.text, background=theme.toolbar, foreground=theme.text,
                 padx=px(8), pady=px(3)).pack(padx=1, pady=1)
        x = self._widget.winfo_rootx()
        y = self._widget.winfo_rooty() + self._widget.winfo_height() + px(6)
        window.wm_geometry(f"+{x}+{y}")
        self._window = window

    def _hide(self, event: tk.Event | None = None) -> None:
        if self._job is not None:
            try:
                self._widget.after_cancel(self._job)
            except tk.TclError:
                pass
            self._job = None
        if self._window is not None:
            self._window.destroy()
            self._window = None


class ToolButton(tk.Canvas):
    """A flat icon button with hover, pressed, switched-on and disabled looks."""

    def __init__(self, parent: tk.Misc, themes: ThemeManager, icon: Icon, command: Callable[[], None],
                 tooltip: str = "", width: int = 32, height: int = 30, background: str = "toolbar") -> None:
        super().__init__(parent, width=px(width), height=px(height), highlightthickness=0, bd=0)
        self._themes = themes
        self._icon = icon
        self._command = command
        self._background = background  # name of the Theme attribute behind the button
        self._hover = False
        self._pressed = False
        self._active = False
        self._enabled = True
        self._accent = ""  # extra color for the icon (e.g. chosen text color)
        self.tooltip = Tooltip(self, themes, tooltip)
        self.bind("<Enter>", self._on_enter, add="+")
        self.bind("<Leave>", self._on_leave, add="+")
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<Configure>", lambda event: self.redraw())
        observe_theme(self, themes, self.redraw)

    # ----- state ------------------------------------------------------------

    def set_active(self, active: bool) -> None:
        if active != self._active:
            self._active = active
            self.redraw()

    def set_enabled(self, enabled: bool) -> None:
        if enabled != self._enabled:
            self._enabled = enabled
            self.configure(cursor="" if not enabled else "hand2")
            self.redraw()

    def set_accent(self, color: str) -> None:
        self._accent = color
        self.redraw()

    # ----- drawing ----------------------------------------------------------

    def redraw(self) -> None:
        theme = self._themes.theme
        self.delete("all")
        if not self._enabled:
            background, color = getattr(theme, self._background), blend(theme.text, theme.page, 0.65)
        elif self._pressed:
            background, color = theme.pressed, theme.text
        elif self._active:
            background, color = theme.active, theme.accent
        elif self._hover:
            background, color = theme.hover, theme.text
        else:
            background, color = getattr(theme, self._background), theme.text
        self.configure(background=getattr(theme, self._background))
        w, h = self.winfo_width(), self.winfo_height()
        if w <= 1:  # not laid out yet
            w, h = int(self["width"]), int(self["height"])
        if background != getattr(theme, self._background):
            self._rounded(px(1), px(1), w - px(1), h - px(1), px(6), background)
        self._icon(self, w, h, color, self._accent)

    def _rounded(self, x1: float, y1: float, x2: float, y2: float, r: float, fill: str) -> None:
        self.create_polygon(
            x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
            x1, y2, x1, y2 - r, x1, y1 + r, x1, y1, smooth=True, fill=fill, outline="")

    # ----- mouse ------------------------------------------------------------

    def _on_enter(self, event: tk.Event) -> None:
        self._hover = True
        self.redraw()

    def _on_leave(self, event: tk.Event) -> None:
        self._hover = self._pressed = False
        self.redraw()

    def _on_press(self, event: tk.Event) -> None:
        if self._enabled:
            self._pressed = True
            self.redraw()

    def _on_release(self, event: tk.Event) -> None:
        was_pressed = self._pressed
        self._pressed = False
        self.redraw()
        inside = 0 <= event.x <= self.winfo_width() and 0 <= event.y <= self.winfo_height()
        if was_pressed and inside and self._enabled:
            self._command()


class TextButton(tk.Label):
    """A flat button with a text label (Replace, Replace all, ...)."""

    def __init__(self, parent: tk.Misc, themes: ThemeManager, fonts: Fonts, text: str,
                 command: Callable[[], None], primary: bool = False) -> None:
        super().__init__(parent, text=text, padx=px(12), pady=px(4), cursor="hand2",
                         font=(fonts.ui, 10))
        self._themes = themes
        self._primary = primary
        self._hover = False
        self.bind("<Enter>", lambda event: self._set_hover(True))
        self.bind("<Leave>", lambda event: self._set_hover(False))
        self.bind("<ButtonRelease-1>", lambda event: command() if 0 <= event.x <= self.winfo_width() else None)
        observe_theme(self, themes, self._restyle)

    def _set_hover(self, hover: bool) -> None:
        self._hover = hover
        self._restyle()

    def _restyle(self) -> None:
        theme = self._themes.theme
        if self._primary:
            self.configure(background=blend(theme.accent, "#000000", 0.15) if self._hover else theme.accent,
                           foreground="#ffffff")
        else:
            self.configure(background=theme.pressed if self._hover else theme.hover, foreground=theme.text)


class Separator(tk.Frame):
    """A thin vertical line between groups of tool buttons."""

    def __init__(self, parent: tk.Misc, themes: ThemeManager, background: str = "toolbar") -> None:
        super().__init__(parent, width=1, height=px(20))
        observe_theme(self, themes, lambda: self.configure(background=themes.theme.border))


# ----- color popup ---------------------------------------------------------

def _build_palette() -> list[list[str]]:
    grays = ["#000000", "#3c4043", "#5f6368", "#80868b", "#9aa0a6", "#bdc1c6", "#dadce0", "#ffffff"]
    base = ["#d93025", "#e8710a", "#f9ab00", "#188038", "#12a4af", "#1a73e8", "#7b3ff2", "#d01884"]
    tint = lambda amount: [blend(color, "#ffffff", amount) for color in base]  # noqa: E731
    shade = [blend(color, "#000000", 0.3) for color in base]
    return [grays, base, tint(0.45), tint(0.75), shade]


PALETTE = _build_palette()


class ColorPopup(tk.Toplevel):
    """A palette that opens under a button and closes when a color is chosen."""

    def __init__(self, anchor: tk.Misc, themes: ThemeManager, fonts: Fonts, none_label: str,
                 on_pick: Callable[[str], None]) -> None:
        super().__init__(anchor)
        theme = themes.theme
        self._on_pick = on_pick
        self.wm_overrideredirect(True)
        self.configure(background=theme.border)
        body = tk.Frame(self, background=theme.toolbar, padx=px(8), pady=px(8))
        body.pack(padx=1, pady=1)

        self._add_text_row(body, none_label, theme, fonts, lambda: self._choose(""))
        grid = tk.Frame(body, background=theme.toolbar)
        grid.pack(pady=px(6))
        for row, colors in enumerate(PALETTE):
            for column, color in enumerate(colors):
                swatch = tk.Frame(grid, width=px(22), height=px(22), background=color, cursor="hand2",
                                  highlightthickness=1, highlightbackground=theme.border)
                swatch.grid(row=row, column=column, padx=px(1.5), pady=px(1.5))
                swatch.bind("<Button-1>", lambda event, value=color: self._choose(value))
                swatch.bind("<Enter>", lambda event, w=swatch: w.configure(highlightbackground=theme.accent,
                                                                           highlightthickness=2))
                swatch.bind("<Leave>", lambda event, w=swatch: w.configure(highlightbackground=theme.border,
                                                                           highlightthickness=1))
        self._add_text_row(body, "More colors…", theme, fonts, self._more_colors)

        self.bind("<Escape>", lambda event: self.destroy())
        self.bind("<Button-1>", self._click_outside, add="+")
        self.update_idletasks()
        x = anchor.winfo_rootx()
        y = anchor.winfo_rooty() + anchor.winfo_height() + px(4)
        x = min(x, max(0, self.winfo_screenwidth() - self.winfo_reqwidth() - px(8)))
        self.wm_geometry(f"+{x}+{y}")
        self.wait_visibility()
        self.grab_set()
        self.focus_set()

    def _add_text_row(self, parent: tk.Misc, text: str, theme, fonts: Fonts, command: Callable[[], None]) -> None:
        label = tk.Label(parent, text=text, anchor="w", padx=px(6), pady=px(4), cursor="hand2",
                         background=theme.toolbar, foreground=theme.text, font=(fonts.ui, 10))
        label.pack(fill=tk.X)
        label.bind("<Enter>", lambda event: label.configure(background=theme.hover))
        label.bind("<Leave>", lambda event: label.configure(background=theme.toolbar))
        label.bind("<Button-1>", lambda event: command())

    def _choose(self, color: str) -> None:
        self.destroy()
        self._on_pick(color)

    def _more_colors(self) -> None:
        self.grab_release()
        chosen = colorchooser.askcolor(parent=self.master, title="Choose a color")[1]
        self.destroy()
        if chosen:
            self._on_pick(chosen)

    def _click_outside(self, event: tk.Event) -> None:
        # While the popup holds the grab, a click anywhere else is reported to the popup itself.
        if event.widget is self and not (0 <= event.x < self.winfo_width() and 0 <= event.y < self.winfo_height()):
            self.destroy()

    def destroy(self) -> None:
        try:
            self.grab_release()
        except tk.TclError:
            pass
        super().destroy()


class ColorButton(tk.Frame):
    """Applies the last used color on click; the small arrow opens the palette."""

    def __init__(self, parent: tk.Misc, themes: ThemeManager, fonts: Fonts, icon: Icon, tooltip: str,
                 none_label: str, default_color: str, on_pick: Callable[[str], None]) -> None:
        super().__init__(parent, background=themes.theme.toolbar)
        self._themes = themes
        self._fonts = fonts
        self._none_label = none_label
        self._on_pick = on_pick
        self._color = default_color
        self.main = ToolButton(self, themes, icon, self._apply, tooltip, width=30)
        self.main.pack(side=tk.LEFT)
        self.main.set_accent(default_color)
        self.arrow = ToolButton(self, themes, _chevron_small, self._open_palette, "More colors", width=14)
        self.arrow.pack(side=tk.LEFT)
        observe_theme(self, themes, lambda: self.configure(background=themes.theme.toolbar))

    def _apply(self) -> None:
        self._on_pick(self._color)

    def _open_palette(self) -> None:
        ColorPopup(self, self._themes, self._fonts, self._none_label, self._picked)

    def _picked(self, color: str) -> None:
        if color:
            self._color = color
            self.main.set_accent(color)
        self._on_pick(color)


def _chevron_small(c: tk.Canvas, w: int, h: int, color: str, accent: str) -> None:
    cx, cy, s = w / 2, h / 2, px(3)
    c.create_line(cx - s, cy - s / 2, cx, cy + s / 2, cx + s, cy - s / 2, fill=color, width=px(1.6),
                  capstyle="round", joinstyle="round")
