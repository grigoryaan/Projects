"""Find and replace bar (shown under the tabs, like a browser's)."""
from __future__ import annotations

import tkinter as tk
from typing import Callable

from pynotepad.core import search
from pynotepad.core.observer import CallbackObserver
from pynotepad.ui import icons
from pynotepad.ui.page_view import PageView
from pynotepad.ui.theme import Fonts, ThemeManager, observe_theme, px
from pynotepad.ui.widgets import TextButton, ToolButton


class FindBar(tk.Frame):
    def __init__(self, parent: tk.Misc, themes: ThemeManager, fonts: Fonts,
                 get_view: Callable[[], PageView | None], flash: Callable[[str], None]) -> None:
        super().__init__(parent)
        self._themes = themes
        self._get_view = get_view
        self._flash = flash
        self._match_case = False
        self._replace_visible = False
        self._open = False
        self._refresh_job: str | None = None
        self._watched_history = None
        self._observer = CallbackObserver(self._schedule_refresh)
        self._pack_options: dict = {}
        font = (fonts.ui, 10)

        self.find_var = tk.StringVar()
        self.replace_var = tk.StringVar()

        top = tk.Frame(self)
        top.pack(fill=tk.X, padx=px(10), pady=(px(6), px(3)))
        self._top = top
        self.find_entry = self._entry(top, self.find_var, font, width=30)
        self.find_entry.pack(side=tk.LEFT, ipady=px(3))
        self._count = tk.Label(top, font=(fonts.ui, 9), width=11, anchor="w", padx=px(8))
        self._count.pack(side=tk.LEFT)
        self._prev = ToolButton(top, themes, icons.chevron_icon("up"), lambda: self.find_next(True),
                                "Previous match (Shift+F3)", width=28, height=26)
        self._prev.pack(side=tk.LEFT)
        self._next = ToolButton(top, themes, icons.chevron_icon("down"), lambda: self.find_next(False),
                                "Next match (F3)", width=28, height=26)
        self._next.pack(side=tk.LEFT)
        self._case = ToolButton(top, themes, icons.text_icon("Aa", 10, weight="bold"), self._toggle_case,
                                "Match case", width=32, height=26)
        self._case.pack(side=tk.LEFT, padx=px(4))
        self._toggle_replace = TextButton(top, themes, fonts, "Replace…", self._toggle_replace_row)
        self._toggle_replace.pack(side=tk.LEFT, padx=px(6))
        self._close = ToolButton(top, themes, icons.close_icon, self.close, "Close (Esc)", width=28, height=26)
        self._close.pack(side=tk.RIGHT)

        self._bottom = tk.Frame(self)
        self.replace_entry = self._entry(self._bottom, self.replace_var, font, width=30)
        self.replace_entry.pack(side=tk.LEFT, ipady=px(3))
        TextButton(self._bottom, themes, fonts, "Replace", self.replace_current, primary=True).pack(
            side=tk.LEFT, padx=(px(8), px(4)))
        TextButton(self._bottom, themes, fonts, "Replace all", self.replace_all).pack(side=tk.LEFT)
        self._rule = tk.Frame(self, height=1)
        self._rule.pack(fill=tk.X, side=tk.BOTTOM)

        self.find_var.trace_add("write", lambda *args: self._query_changed())
        self.find_entry.bind("<Return>", lambda e: self.find_next(False))
        self.find_entry.bind("<Shift-Return>", lambda e: self.find_next(True))
        self.replace_entry.bind("<Return>", lambda e: self.replace_current())
        for entry in (self.find_entry, self.replace_entry):
            entry.bind("<Escape>", lambda e: self.close())
        observe_theme(self, themes, self._restyle)

    def _entry(self, parent: tk.Misc, variable: tk.StringVar, font: tuple, width: int) -> tk.Entry:
        return tk.Entry(parent, textvariable=variable, font=font, width=width, relief="flat",
                        exportselection=False, highlightthickness=1)

    # ===== showing and hiding ==================================================

    def configure_packing(self, **options) -> None:
        self._pack_options = options

    def open(self, replace: bool = False) -> None:
        view = self._get_view()
        if view is not None:
            selected = view.selection()
            if selected:
                text = view.document.snapshot(*selected).text
                if "\n" not in text:
                    self.find_var.set(text)
        if not self._open:
            self._open = True
            self.pack(fill=tk.X, **self._pack_options)
        self._set_replace_visible(replace or self._replace_visible)
        self.find_entry.focus_set()
        self.find_entry.selection_range(0, tk.END)
        self.on_page_changed()

    def close(self) -> None:
        view = self._get_view()
        if view is not None:
            view.highlight_matches([], None)
        self._unwatch()
        self._open = False
        self.pack_forget()
        if view is not None:
            view.focus()

    @property
    def is_open(self) -> bool:
        return self._open

    def _toggle_replace_row(self) -> None:
        self._set_replace_visible(not self._replace_visible)

    def _set_replace_visible(self, visible: bool) -> None:
        self._replace_visible = visible
        if visible:
            self._bottom.pack(fill=tk.X, padx=px(10), pady=(0, px(6)), before=self._rule)
        else:
            self._bottom.pack_forget()

    def _toggle_case(self) -> None:
        self._match_case = not self._match_case
        self._case.set_active(self._match_case)
        self._refresh()

    # ===== following the active tab ==========================================

    def on_page_changed(self) -> None:
        """The active tab changed: watch its history so highlights stay up to date."""
        self._unwatch()
        view = self._get_view()
        if view is not None and self.is_open:
            self._watched_history = view.editor.history
            self._watched_history.attach(self._observer)
        self._refresh()

    def _unwatch(self) -> None:
        if self._watched_history is not None:
            self._watched_history.detach(self._observer)
            self._watched_history = None

    def _schedule_refresh(self) -> None:
        if self._refresh_job is None:
            self._refresh_job = self.after_idle(self._refresh)

    # ===== searching ===========================================================

    def _query(self) -> str:
        return self.find_var.get()

    def _matches(self, view: PageView) -> list[tuple[int, int]]:
        return search.find_all(view.document.text, self._query(), self._match_case)

    def _refresh(self) -> None:
        """Re-highlights all matches and updates the counter."""
        self._refresh_job = None
        view = self._get_view()
        if view is None or not self.is_open:
            return
        matches = self._matches(view)
        selection = view.selection()
        current = selection if selection in matches else None
        view.highlight_matches(matches, current)
        theme = self._themes.theme
        if not self._query():
            self._count.configure(text="", foreground=theme.muted)
        elif not matches:
            self._count.configure(text="No results", foreground=theme.danger)
        elif current is not None:
            self._count.configure(text=f"{matches.index(current) + 1} of {len(matches)}", foreground=theme.muted)
        else:
            self._count.configure(text=f"{len(matches)} found", foreground=theme.muted)

    def _query_changed(self) -> None:
        """Incremental search: jump to the first match while typing."""
        view = self._get_view()
        if view is not None and self._query():
            selection = view.selection()
            start = selection[0] if selection else view.caret()
            found = view.editor.find(self._query(), start, self._match_case)
            if found is not None:
                view.select_range(*found)
        self._refresh()

    def find_next(self, backwards: bool = False) -> None:
        view = self._get_view()
        if view is None:
            return
        if not self.is_open:
            self.open()
            return
        if not self._query():
            self.find_entry.focus_set()
            return
        selection = view.selection()
        if backwards:
            start = selection[0] if selection else view.caret()
        else:
            start = selection[1] if selection else view.caret()
        found = view.editor.find(self._query(), start, self._match_case, backwards)
        if found is not None:
            view.select_range(*found)
            wrapped = found[0] < start if not backwards else found[1] > start
            if wrapped:
                self._flash("Search wrapped around")
        self._refresh()

    def replace_current(self) -> None:
        view = self._get_view()
        if view is None or not self._query():
            return
        selection = view.selection()
        if selection and view.editor.is_match(*selection, self._query(), self._match_case):
            view.editor.replace_range(*selection, self.replace_var.get())
        self.find_next(False)

    def replace_all(self) -> None:
        view = self._get_view()
        if view is None or not self._query():
            return
        count = view.editor.replace_all(self._query(), self.replace_var.get(), self._match_case)
        self._flash(f"Replaced {count} occurrence{'s' if count != 1 else ''}" if count else "No matches to replace")
        self._refresh()

    # ===== look ================================================================

    def _restyle(self) -> None:
        theme = self._themes.theme
        for widget in (self, self._top, self._bottom, self._count):
            widget.configure(background=theme.toolbar)
        self._count.configure(foreground=theme.muted)
        self._rule.configure(background=theme.border)
        for entry in (self.find_entry, self.replace_entry):
            entry.configure(background=theme.page, foreground=theme.text, insertbackground=theme.text,
                            highlightbackground=theme.border, highlightcolor=theme.accent,
                            selectbackground=theme.selection, selectforeground=theme.text)
