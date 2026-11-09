"""The two toolbar rows: file/edit tools and text formatting tools.

The toolbar shows the state of the active editor's typing format (is bold on?
which font? which alignment?) and reports user choices through the `handlers`
object. It never touches documents itself.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any, Protocol

from pynotepad.core.editor import Editor
from pynotepad.core.formatting import ALIGN_CENTER, ALIGN_LEFT, ALIGN_RIGHT, BLOCK_NAMES, MAX_SIZE, MIN_SIZE
from pynotepad.core.observer import Observer, Subject
from pynotepad.ui import icons
from pynotepad.ui.actions import Action
from pynotepad.ui.theme import Fonts, ThemeManager, observe_theme, px
from pynotepad.ui.widgets import ColorButton, Separator, ToolButton

FONT_SIZES = (8, 9, 10, 11, 12, 14, 16, 18, 20, 24, 28, 32, 36, 48, 60, 72, 96)
BLOCK_BY_NAME = {name: block for block, name in BLOCK_NAMES.items()}


class Handlers(Protocol):
    """What the toolbar needs from the application."""

    actions: dict[str, Action]

    def set_block(self, block: str) -> None: ...
    def set_font_family(self, family: str) -> None: ...
    def set_font_size(self, size: int) -> None: ...
    def set_text_color(self, color: str) -> None: ...
    def set_highlight(self, color: str) -> None: ...
    def focus_editor(self) -> None: ...


class Toolbar(tk.Frame, Observer):
    def __init__(self, parent: tk.Misc, themes: ThemeManager, fonts: Fonts, families: list[str],
                 handlers: Handlers) -> None:
        super().__init__(parent)
        self._themes = themes
        self._fonts = fonts
        self._handlers = handlers
        self._editor: Editor | None = None
        self._updating = False  # True while we set widget values ourselves (no reaction wanted)
        self._buttons: dict[str, ToolButton] = {}

        self._top = self._row()
        self._bottom = self._row()
        self._build_top_row()
        self._build_bottom_row(families)
        observe_theme(self, themes, self._restyle)

    # ===== construction ========================================================

    def _row(self) -> tk.Frame:
        row = tk.Frame(self, padx=px(8), pady=px(3))
        row.pack(fill=tk.X)
        return row

    def _button(self, row: tk.Frame, action_id: str, icon: icons.Icon, side: str = tk.LEFT,
                width: int = 32) -> ToolButton:
        action = self._handlers.actions[action_id]
        button = ToolButton(row, self._themes, icon, action.run, action.tooltip, width=width)
        button.pack(side=side, padx=px(1))
        self._buttons[action_id] = button
        return button

    def _separator(self, row: tk.Frame) -> None:
        Separator(row, self._themes).pack(side=tk.LEFT, padx=px(7), pady=px(5))

    def _build_top_row(self) -> None:
        row = self._top
        self._button(row, "new", icons.new_icon)
        self._button(row, "open", icons.open_icon)
        self._button(row, "save", icons.save_icon)
        self._separator(row)
        self._button(row, "undo", icons.undo_icon)
        self._button(row, "redo", icons.redo_icon)
        self._separator(row)
        self._button(row, "cut", icons.cut_icon)
        self._button(row, "copy", icons.copy_icon)
        self._button(row, "paste", icons.paste_icon)
        self._separator(row)
        self._button(row, "find", icons.search_icon)
        # right side (packed from the right edge)
        self._button(row, "toggle_theme", icons.theme_icon, side=tk.RIGHT)
        self._button(row, "toggle_history", icons.history_icon, side=tk.RIGHT)

    def _build_bottom_row(self, families: list[str]) -> None:
        row = self._bottom
        style = ttk.Combobox(row, values=list(BLOCK_NAMES.values()), state="readonly", width=12,
                             style="Tool.TCombobox", exportselection=False)
        style.pack(side=tk.LEFT, padx=(px(2), px(4)), pady=px(2))
        style.bind("<<ComboboxSelected>>", lambda e: self._choose_block(style.get()))
        self._style_box = style

        font = ttk.Combobox(row, values=families, width=18, style="Tool.TCombobox", exportselection=False)
        font.pack(side=tk.LEFT, padx=px(4), pady=px(2))
        font.bind("<<ComboboxSelected>>", lambda e: self._choose_family(font.get()))
        font.bind("<Return>", lambda e: self._choose_family(font.get()))
        self._font_box = font

        size = ttk.Combobox(row, values=[str(s) for s in FONT_SIZES], width=4, style="Tool.TCombobox",
                            exportselection=False)
        size.pack(side=tk.LEFT, padx=px(4), pady=px(2))
        size.bind("<<ComboboxSelected>>", lambda e: self._choose_size(size.get()))
        size.bind("<Return>", lambda e: self._choose_size(size.get()))
        self._size_box = size

        self._button(row, "smaller", icons.font_size_icon("−"))
        self._button(row, "larger", icons.font_size_icon("+"))
        self._separator(row)
        self._button(row, "bold", icons.text_icon("B", weight="bold"))
        self._button(row, "italic", icons.text_icon("I", slant="italic"))
        self._button(row, "underline", icons.text_icon("U", underline=True))
        self._button(row, "strike", icons.text_icon("S", overstrike=True))
        self._separator(row)

        self._text_color = ColorButton(row, self._themes, self._fonts, icons.color_icon("A"), "Text color",
                                       "Automatic", "#d93025", self._handlers.set_text_color)
        self._text_color.pack(side=tk.LEFT, padx=px(1))
        self._highlight = ColorButton(row, self._themes, self._fonts, icons.color_icon("ab", highlighted=True),
                                      "Highlight color", "No highlight", "#fdd835", self._handlers.set_highlight)
        self._highlight.pack(side=tk.LEFT, padx=px(1))
        self._separator(row)
        self._button(row, "align_left", icons.align_icon("left"))
        self._button(row, "align_center", icons.align_icon("center"))
        self._button(row, "align_right", icons.align_icon("right"))
        self._separator(row)
        self._button(row, "bullets", icons.bullets_icon)
        self._button(row, "clear_format", icons.clear_format_icon)

    @property
    def comboboxes(self) -> tuple[ttk.Combobox, ...]:
        return self._style_box, self._font_box, self._size_box

    # ===== reacting to the model ==============================================

    def bind_editor(self, editor: Editor) -> None:
        """Shows the state of another tab."""
        if self._editor is not None:
            self._editor.detach(self)
            self._editor.history.detach(self)
        self._editor = editor
        editor.attach(self)
        editor.history.attach(self)
        self._sync()

    def update(self, subject: Subject, event: Any = None) -> None:
        self._sync()

    def _sync(self) -> None:
        editor = self._editor
        if editor is None:
            return
        fmt = editor.pending_format
        for action_id, value in (("bold", fmt.bold), ("italic", fmt.italic), ("underline", fmt.underline),
                                 ("strike", fmt.strike), ("align_left", fmt.align == ALIGN_LEFT),
                                 ("align_center", fmt.align == ALIGN_CENTER),
                                 ("align_right", fmt.align == ALIGN_RIGHT)):
            self._buttons[action_id].set_active(value)
        self._buttons["undo"].set_enabled(editor.history.can_undo)
        self._buttons["redo"].set_enabled(editor.history.can_redo)
        self._updating = True
        try:
            self._style_box.set(BLOCK_NAMES[fmt.block])
            self._font_box.set(fmt.family or self._fonts.document)
            if self.focus_get() is not self._size_box:  # do not overwrite what the user is typing
                self._size_box.set(str(fmt.size))
        finally:
            self._updating = False

    # ===== user choices ========================================================

    def _choose_block(self, name: str) -> None:
        if not self._updating:
            self._handlers.set_block(BLOCK_BY_NAME[name])
            self._handlers.focus_editor()

    def _choose_family(self, family: str) -> None:
        family = family.strip()
        if not self._updating and family:
            self._handlers.set_font_family(family)
            self._handlers.focus_editor()

    def _choose_size(self, text: str) -> None:
        if self._updating:
            return
        try:
            size = int(float(text))
        except ValueError:
            self._sync()  # not a number: put the real value back
            return
        self._handlers.set_font_size(max(MIN_SIZE, min(MAX_SIZE, size)))
        self._handlers.focus_editor()

    # ===== look ================================================================

    def _restyle(self) -> None:
        theme = self._themes.theme
        self.configure(background=theme.toolbar)
        for row in (self._top, self._bottom):
            row.configure(background=theme.toolbar)
