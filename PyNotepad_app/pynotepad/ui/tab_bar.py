"""The row of tabs ("pages") above the editor.

Each Tab is a small frame with a title and a close button. The bar knows nothing
about documents: it reports clicks through callbacks and is told what to show.
"""
from __future__ import annotations

import tkinter as tk
from typing import Callable

from pynotepad.core.workspace import Page
from pynotepad.ui import icons
from pynotepad.ui.theme import Fonts, ThemeManager, observe_theme, px
from pynotepad.ui.widgets import ToolButton

MAX_TITLE = 24


def short_title(title: str) -> str:
    return title if len(title) <= MAX_TITLE else title[:MAX_TITLE - 1] + "…"


class Tab(tk.Frame):
    def __init__(self, bar: TabBar, page: Page) -> None:
        super().__init__(bar.strip, cursor="hand2")
        self._bar = bar
        self.page = page
        self.selected = False
        self._hover = False
        self._accent = tk.Frame(self, height=px(3))
        self._accent.pack(fill=tk.X, side=tk.TOP)
        row = tk.Frame(self)
        row.pack(fill=tk.X)
        self._row = row
        self._dot = tk.Label(row, text="", width=1, font=(bar.fonts.ui, 11, "bold"))
        self._dot.pack(side=tk.LEFT, padx=(px(10), 0))
        self._title = tk.Label(row, font=(bar.fonts.ui, 10), padx=px(4), pady=px(7))
        self._title.pack(side=tk.LEFT)
        self._close = ToolButton(row, bar.themes, icons.close_icon, lambda: bar.on_close(page),
                                 "Close tab (Ctrl+W)", width=22, height=22, background="chrome")
        self._close.pack(side=tk.LEFT, padx=(0, px(6)))
        for widget in (self, self._accent, row, self._dot, self._title):
            widget.bind("<Button-1>", lambda event: bar.on_select(page))
            widget.bind("<Button-2>", lambda event: bar.on_close(page))
            widget.bind("<Button-3>", lambda event: bar.on_context(page, event))
            widget.bind("<Enter>", lambda event: self._set_hover(True))
            widget.bind("<Leave>", lambda event: self._set_hover(False))
        self.refresh()
        observe_theme(self, bar.themes, self._restyle)

    def refresh(self) -> None:
        self._title.configure(text=short_title(self.page.title))
        self._dot.configure(text="●" if self.page.modified else "")
        self._restyle()

    def set_selected(self, selected: bool) -> None:
        self.selected = selected
        self._restyle()

    def _set_hover(self, hover: bool) -> None:
        self._hover = hover
        self._restyle()

    def _restyle(self) -> None:
        theme = self._bar.themes.theme
        if self.selected:
            background, foreground = theme.toolbar, theme.text
        elif self._hover:
            background, foreground = theme.hover, theme.text
        else:
            background, foreground = theme.tab_idle, theme.muted
        for widget in (self, self._row, self._title, self._dot):
            widget.configure(background=background)
        self._title.configure(foreground=foreground)
        self._dot.configure(foreground=theme.accent)
        self._accent.configure(background=theme.accent if self.selected else background)
        self._close._background = "toolbar" if self.selected else "chrome"
        self._close.redraw()
        self.configure(highlightthickness=0)


class TabBar(tk.Frame):
    def __init__(self, parent: tk.Misc, themes: ThemeManager, fonts: Fonts,
                 on_select: Callable[[Page], None], on_close: Callable[[Page], None],
                 on_new: Callable[[], None], on_context: Callable[[Page, tk.Event], None]) -> None:
        super().__init__(parent)
        self.themes = themes
        self.fonts = fonts
        self.on_select = on_select
        self.on_close = on_close
        self.on_context = on_context
        self._tabs: dict[Page, Tab] = {}
        self.strip = tk.Frame(self)
        self.strip.pack(side=tk.LEFT, fill=tk.Y)
        self._new_button = ToolButton(self, themes, icons.new_icon, on_new, "New tab (Ctrl+N)",
                                      width=34, height=30, background="chrome")
        self._new_button.pack(side=tk.LEFT, padx=px(6), pady=(px(4), 0))
        self._rule = tk.Frame(self, height=1)
        observe_theme(self, themes, self._restyle)

    def _restyle(self) -> None:
        theme = self.themes.theme
        for widget in (self, self.strip):
            widget.configure(background=theme.chrome)

    def add(self, page: Page) -> None:
        tab = Tab(self, page)
        tab.pack(side=tk.LEFT, padx=(0, 1), pady=(px(4), 0))
        self._tabs[page] = tab

    def remove(self, page: Page) -> None:
        tab = self._tabs.pop(page, None)
        if tab is not None:
            tab.destroy()

    def refresh(self, page: Page) -> None:
        if page in self._tabs:
            self._tabs[page].refresh()

    def select(self, page: Page) -> None:
        for other, tab in self._tabs.items():
            tab.set_selected(other is page)
