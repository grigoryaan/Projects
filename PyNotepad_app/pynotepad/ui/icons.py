"""Tool button icons, drawn on a Canvas so they look the same on every platform.

An icon is a function `draw(canvas, w, h, color, accent)`; `accent` is the optional
second color (the color bar under the "A" of the text color button, for example).
"""
from __future__ import annotations

import tkinter as tk
from tkinter import font as tkfont
from typing import Callable

from pynotepad.ui.theme import px

Icon = Callable[[tk.Canvas, int, int, str, str], None]


def _remember(canvas: tk.Canvas, font: tkfont.Font) -> tkfont.Font:
    """A Tk font disappears when its Python object is collected, so keep it alive."""
    if not hasattr(canvas, "_icon_fonts"):
        canvas._icon_fonts = []  # type: ignore[attr-defined]
    canvas._icon_fonts.append(font)  # type: ignore[attr-defined]
    return font


def text_icon(label: str, size: int = 12, **font_options) -> Icon:
    def draw(c: tk.Canvas, w: int, h: int, color: str, accent: str) -> None:
        font = _remember(c, tkfont.Font(root=c, size=size, **font_options))
        c.create_text(w / 2, h / 2, text=label, fill=color, font=font)
    return draw


def font_size_icon(sign: str) -> Icon:
    def draw(c: tk.Canvas, w: int, h: int, color: str, accent: str) -> None:
        big = _remember(c, tkfont.Font(root=c, size=13, weight="bold"))
        small = _remember(c, tkfont.Font(root=c, size=8, weight="bold"))
        c.create_text(w / 2 - px(3), h / 2 + px(1), text="A", fill=color, font=big)
        c.create_text(w / 2 + px(8), h / 2 - px(5), text=sign, fill=color, font=small)
    return draw


def color_icon(label: str, highlighted: bool = False) -> Icon:
    """A letter with a bar of the chosen color under it (accent = the color)."""
    def draw(c: tk.Canvas, w: int, h: int, color: str, accent: str) -> None:
        font = _remember(c, tkfont.Font(root=c, size=12, weight="bold"))
        if highlighted and accent:
            c.create_rectangle(w / 2 - px(9), h / 2 - px(9), w / 2 + px(9), h / 2 + px(5), fill=accent, width=0)
        c.create_text(w / 2, h / 2 - px(2), text=label, fill=color, font=font)
        bar = accent or color
        c.create_rectangle(w / 2 - px(9), h - px(9), w / 2 + px(9), h - px(5), fill=bar,
                           outline=color if not accent else "", width=1)
    return draw


def align_icon(kind: str) -> Icon:
    widths = (16, 10, 16, 10)

    def draw(c: tk.Canvas, w: int, h: int, color: str, accent: str) -> None:
        top = h / 2 - px(7)
        for row, width in enumerate(widths):
            y = top + row * px(4.5)
            width = px(width)
            if kind == "left":
                x1 = w / 2 - px(8)
            elif kind == "center":
                x1 = w / 2 - width / 2
            else:
                x1 = w / 2 + px(8) - width
            c.create_line(x1, y, x1 + width, y, fill=color, width=px(1.6), capstyle="round")
    return draw


def bullets_icon(c: tk.Canvas, w: int, h: int, color: str, accent: str) -> None:
    for row in range(3):
        y = h / 2 - px(5.5) + row * px(5.5)
        c.create_oval(w / 2 - px(9), y - px(1.6), w / 2 - px(5.8), y + px(1.6), fill=color, width=0)
        c.create_line(w / 2 - px(2), y, w / 2 + px(9), y, fill=color, width=px(1.6), capstyle="round")


def _arrow(c: tk.Canvas, w: int, h: int, color: str, direction: int) -> None:
    """A curved arrow: direction +1 puts the head on the left (undo), -1 on the right (redo)."""
    cx, cy = w / 2, h / 2
    d = direction
    points = (cx + d * px(7), cy + px(6), cx + d * px(8), cy - px(4), cx - d * px(1), cy - px(7),
              cx - d * px(8), cy - px(1))
    c.create_line(*points, smooth=True, fill=color, width=px(1.8), capstyle="round")
    c.create_polygon(cx - d * px(12), cy + px(1), cx - d * px(4), cy - px(2), cx - d * px(7), cy + px(6),
                     fill=color, width=0)


def undo_icon(c: tk.Canvas, w: int, h: int, color: str, accent: str) -> None:
    _arrow(c, w, h, color, +1)  # the arrow head is on the left


def redo_icon(c: tk.Canvas, w: int, h: int, color: str, accent: str) -> None:
    _arrow(c, w, h, color, -1)  # the arrow head is on the right


def new_icon(c: tk.Canvas, w: int, h: int, color: str, accent: str) -> None:
    x, y, pw, ph, fold = w / 2 - px(6), h / 2 - px(8), px(12), px(16), px(5)
    c.create_polygon(x, y, x + pw - fold, y, x + pw, y + fold, x + pw, y + ph, x, y + ph,
                     outline=color, fill="", width=px(1.5), joinstyle="round")
    c.create_line(x + pw - fold, y, x + pw - fold, y + fold, x + pw, y + fold, fill=color, width=px(1.5))
    c.create_line(w / 2 - px(3), h / 2 + px(2), w / 2 + px(3), h / 2 + px(2), fill=color, width=px(1.5))
    c.create_line(w / 2, h / 2 - px(1), w / 2, h / 2 + px(5), fill=color, width=px(1.5))


def open_icon(c: tk.Canvas, w: int, h: int, color: str, accent: str) -> None:
    x, y = w / 2 - px(9), h / 2 - px(6)
    c.create_polygon(x, y + px(2), x + px(6), y + px(2), x + px(8), y + px(4), x + px(17), y + px(4),
                     x + px(17), y + px(12), x, y + px(12),
                     outline=color, fill="", width=px(1.5), joinstyle="round")
    c.create_line(x, y + px(7), x + px(17), y + px(7), fill=color, width=px(1.5))


def save_icon(c: tk.Canvas, w: int, h: int, color: str, accent: str) -> None:
    x, y, s = w / 2 - px(8), h / 2 - px(8), px(16)
    c.create_polygon(x, y, x + s - px(3), y, x + s, y + px(3), x + s, y + s, x, y + s,
                     outline=color, fill="", width=px(1.5), joinstyle="round")
    c.create_rectangle(x + px(4), y, x + s - px(4), y + px(5), outline=color, width=px(1.3))
    c.create_rectangle(x + px(3.5), y + px(9), x + s - px(3.5), y + s - px(1), outline=color, width=px(1.3))


def search_icon(c: tk.Canvas, w: int, h: int, color: str, accent: str) -> None:
    cx, cy, r = w / 2 - px(2), h / 2 - px(2), px(6)
    c.create_oval(cx - r, cy - r, cx + r, cy + r, outline=color, width=px(1.7))
    c.create_line(cx + r * 0.7, cy + r * 0.7, cx + px(9), cy + px(9), fill=color, width=px(2), capstyle="round")


def cut_icon(c: tk.Canvas, w: int, h: int, color: str, accent: str) -> None:
    cx, cy = w / 2, h / 2
    c.create_line(cx - px(5), cy - px(8), cx + px(4), cy + px(3), fill=color, width=px(1.6))
    c.create_line(cx + px(5), cy - px(8), cx - px(4), cy + px(3), fill=color, width=px(1.6))
    for dx in (-5, 5):
        c.create_oval(cx + px(dx) - px(3), cy + px(3), cx + px(dx) + px(3), cy + px(9), outline=color, width=px(1.5))


def copy_icon(c: tk.Canvas, w: int, h: int, color: str, accent: str) -> None:
    x, y = w / 2 - px(7), h / 2 - px(8)
    c.create_rectangle(x + px(4), y, x + px(13), y + px(11), outline=color, width=px(1.5))
    c.create_rectangle(x, y + px(4), x + px(9), y + px(15), outline=color, width=px(1.5), fill="")


def paste_icon(c: tk.Canvas, w: int, h: int, color: str, accent: str) -> None:
    x, y = w / 2 - px(7), h / 2 - px(8)
    c.create_rectangle(x, y + px(2), x + px(14), y + px(16), outline=color, width=px(1.5))
    c.create_rectangle(x + px(4), y, x + px(10), y + px(4), outline=color, fill=color, width=px(1))
    c.create_line(x + px(3), y + px(8), x + px(11), y + px(8), fill=color, width=px(1.4))
    c.create_line(x + px(3), y + px(12), x + px(9), y + px(12), fill=color, width=px(1.4))


def clear_format_icon(c: tk.Canvas, w: int, h: int, color: str, accent: str) -> None:
    font = _remember(c, tkfont.Font(root=c, size=12))
    c.create_text(w / 2 - px(2), h / 2 - px(1), text="T", fill=color, font=font)
    x, y = w / 2 + px(3), h / 2 + px(2)
    c.create_line(x, y, x + px(6), y + px(6), fill=color, width=px(1.6), capstyle="round")
    c.create_line(x + px(6), y, x, y + px(6), fill=color, width=px(1.6), capstyle="round")


def history_icon(c: tk.Canvas, w: int, h: int, color: str, accent: str) -> None:
    cx, cy, r = w / 2, h / 2, px(8)
    c.create_oval(cx - r, cy - r, cx + r, cy + r, outline=color, width=px(1.6))
    c.create_line(cx, cy - px(5), cx, cy, cx + px(4), cy + px(3), fill=color, width=px(1.6), capstyle="round")


def theme_icon(c: tk.Canvas, w: int, h: int, color: str, accent: str) -> None:
    cx, cy, r = w / 2, h / 2, px(7.5)
    c.create_oval(cx - r, cy - r, cx + r, cy + r, outline=color, width=px(1.6))
    c.create_arc(cx - r, cy - r, cx + r, cy + r, start=90, extent=180, fill=color, outline=color)


def chevron_icon(direction: str) -> Icon:
    def draw(c: tk.Canvas, w: int, h: int, color: str, accent: str) -> None:
        cx, cy, s = w / 2, h / 2, px(4)
        if direction == "down":
            points = (cx - s, cy - s / 2, cx, cy + s / 2, cx + s, cy - s / 2)
        elif direction == "up":
            points = (cx - s, cy + s / 2, cx, cy - s / 2, cx + s, cy + s / 2)
        elif direction == "left":
            points = (cx + s / 2, cy - s, cx - s / 2, cy, cx + s / 2, cy + s)
        else:
            points = (cx - s / 2, cy - s, cx + s / 2, cy, cx - s / 2, cy + s)
        c.create_line(*points, fill=color, width=px(1.8), capstyle="round", joinstyle="round")
    return draw


def close_icon(c: tk.Canvas, w: int, h: int, color: str, accent: str) -> None:
    cx, cy, s = w / 2, h / 2, px(4.5)
    c.create_line(cx - s, cy - s, cx + s, cy + s, fill=color, width=px(1.7), capstyle="round")
    c.create_line(cx + s, cy - s, cx - s, cy + s, fill=color, width=px(1.7), capstyle="round")
