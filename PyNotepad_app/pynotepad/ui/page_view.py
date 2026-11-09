"""PageView: the editing surface of one tab.

The Tk Text widget is used only for display. The real text lives in the Document.
Every key press is intercepted and turned into a call to the Editor facade; every
change of the Document is then mirrored into the widget (Observer pattern), always
incrementally, so scrolling, selection and the cursor are not disturbed.

Offsets: Tk indexes are "line.column" strings; Document.line_col / position_of convert
between them and the character offsets the model uses.
"""
from __future__ import annotations

import re
import sys
import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk
from typing import Any, Callable

from pynotepad.core.document import DELETE, FORMAT, INSERT, Document, DocumentChange
from pynotepad.core.editor import Editor, Selection
from pynotepad.core.formatting import DEFAULT_FORMAT, Format
from pynotepad.core.history import CommandHistory
from pynotepad.core.observer import Observer, Subject
from pynotepad.core.workspace import Page
from pynotepad.ui.clipboard import Clipboard
from pynotepad.ui.theme import Fonts, ThemeManager, observe_theme, px

NAVIGATION_KEYS = {"Left", "Right", "Up", "Down", "Home", "End", "Prior", "Next"}
ALT_MASK = {"win32": 0x20000, "linux": 0x8}.get(sys.platform, 0)
SHIFT_MASK = 0x1
FIND_TAGS = ("find_match", "find_current")
MAX_HIGHLIGHTS = 2000
# Tk's built-in emacs-style bindings change text behind the editor's back: disable them.
BLOCKED_SEQUENCES = ("<<Clear>>", "<<PasteSelection>>", "<Button-2>", "<ButtonRelease-2>", "<Control-Key-slash>")

# X11 keycodes of the Latin letters: lets shortcuts work on non-Latin keyboard layouts
# (Armenian, Russian ...) where the key produces a different symbol.
X11_LETTER_KEYCODES = {
    24: "q", 25: "w", 26: "e", 27: "r", 28: "t", 29: "y", 30: "u", 31: "i", 32: "o", 33: "p",
    38: "a", 39: "s", 40: "d", 41: "f", 42: "g", 43: "h", 44: "j", 45: "k", 46: "l",
    52: "z", 53: "x", 54: "c", 55: "v", 56: "b", 57: "n", 58: "m",
}


NAMED_KEYS = re.compile(
    r"f\d+|tab|iso_left_tab|plus|minus|equal|space|bracket(left|right)|return|escape|prior|next|home|end"
    r"|left|right|up|down|delete|backspace|kp_\w+|\d")


def shortcut_key(event: tk.Event) -> str:
    """Name of the pressed key for shortcut matching, independent of the keyboard layout.

    On a non-Latin layout the Z key reports a keysym such as "Cyrillic_ya" or "Armenian_za";
    for those the physical key is looked up by its keycode, so Ctrl+Z still means Undo.
    """
    name = event.keysym
    if len(name) == 1 and name.isascii():
        return name.lower()
    if NAMED_KEYS.fullmatch(name.lower()):
        return name.lower()
    if sys.platform == "win32" and 65 <= event.keycode <= 90:
        return chr(event.keycode).lower()
    if sys.platform.startswith("linux") and event.keycode in X11_LETTER_KEYCODES:
        return X11_LETTER_KEYCODES[event.keycode]
    return name.lower()


class PageView(Observer):
    def __init__(self, parent: tk.Misc, page: Page, themes: ThemeManager, fonts: Fonts, clipboard: Clipboard,
                 shortcut_handler: Callable[[tk.Event], str | None], zoom: float = 1.0, wrap: bool = True) -> None:
        self.page = page
        self._themes = themes
        self._fonts = fonts
        self._clipboard = clipboard
        self._shortcut_handler = shortcut_handler
        self._zoom = zoom
        self.on_status_change: Callable[[], None] = lambda: None
        self.on_zoom_request: Callable[[int], None] = lambda step: None

        self._tag_of: dict[Format, str] = {}
        self._font_cache: dict[tuple[str, int, bool, bool], tkfont.Font] = {}
        self._sync_job: str | None = None

        self.frame = tk.Frame(parent)
        self.scrollbar = ttk.Scrollbar(self.frame, orient=tk.VERTICAL, style="Page.Vertical.TScrollbar")
        self.text = tk.Text(
            self.frame, wrap="word" if wrap else "none", undo=False, exportselection=False,
            borderwidth=0, highlightthickness=0, padx=px(48), pady=px(28), insertwidth=px(2),
            spacing1=0, spacing2=px(3), spacing3=px(5), tabs=("0.5i",), cursor="xterm",
            yscrollcommand=self.scrollbar.set,
        )
        self.scrollbar.configure(command=self.text.yview)
        self.hscroll = ttk.Scrollbar(self.frame, orient=tk.HORIZONTAL, command=self.text.xview,
                                     style="Page.Horizontal.TScrollbar")
        self.text.configure(xscrollcommand=self.hscroll.set)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._set_wrap(wrap)

        self.text.tag_configure("trail", justify="left")
        for name in FIND_TAGS:
            self.text.tag_configure(name)
        self.text.tag_raise("sel")

        self._bind_events()
        observe_theme(self.text, themes, self._restyle)
        self._render_all()

        self.document.attach(self)
        self.editor.history.attach(self)
        self.editor.attach(self)

    # ===== accessors ===========================================================

    @property
    def editor(self) -> Editor:
        return self.page.editor

    @property
    def document(self) -> Document:
        return self.page.editor.document

    def focus(self) -> None:
        self.text.focus_set()

    def caret(self) -> int:
        line, column = str(self.text.index(tk.INSERT)).split(".")
        return self.document.position_of(int(line), int(column))

    def selection(self) -> Selection:
        ranges = self.text.tag_ranges("sel")
        if not ranges:
            return None
        return self._offset(str(ranges[0])), self._offset(str(ranges[1]))

    def select_range(self, start: int, end: int) -> None:
        self.text.tag_remove("sel", "1.0", tk.END)
        self.text.tag_add("sel", self._index(start), self._index(end))
        self.text.mark_set(tk.INSERT, self._index(end))
        self.text.see(self._index(start))
        self.text.see(self._index(end))
        self._schedule_sync()

    def select_all(self) -> None:
        self.text.tag_add("sel", "1.0", "end-1c")
        self.text.mark_set(tk.INSERT, "end-1c")
        self._schedule_sync()

    def set_caret(self, position: int) -> None:
        self.text.tag_remove("sel", "1.0", tk.END)
        self.text.mark_set(tk.INSERT, self._index(position))
        self.text.see(tk.INSERT)
        self._schedule_sync()

    # ===== Observer: the model changed =========================================

    def update(self, subject: Subject, event: Any = None) -> None:
        if isinstance(subject, Document):
            self._on_document_change(event)
        elif isinstance(subject, CommandHistory):
            self._after_command()
        elif isinstance(subject, Editor):  # the typing format changed
            self._update_trailing_line()
            self.on_status_change()

    def _on_document_change(self, change: DocumentChange) -> None:
        if change.kind == INSERT:
            self.text.insert(self._index(change.start), self.document.text[change.start:change.end], ())
            self._tag_runs(change.start, change.end)
        elif change.kind == DELETE:
            start = self._index(change.start)
            self.text.delete(start, f"{start}+{change.end - change.start}c")
        elif change.kind == FORMAT:
            self._retag(change.start, change.end)
        if change.caret is not None:
            self.text.mark_set(tk.INSERT, self._index(change.caret))
            self.text.see(tk.INSERT)

    def _after_command(self) -> None:
        """A whole command finished: take the typing format from the text around the cursor."""
        self.editor.sync_pending(self.caret(), self.selection())
        self._update_trailing_line()
        self.on_status_change()

    # ===== rendering ===========================================================

    def _render_all(self) -> None:
        self.text.delete("1.0", tk.END)
        self.text.insert("1.0", self.document.text, ())
        self._tag_runs(0, len(self.document))
        self._update_trailing_line()

    def _tag_runs(self, start: int, end: int) -> None:
        for run_start, run_end, fmt in self.document.format_runs(start, end):
            if fmt != DEFAULT_FORMAT:
                self.text.tag_add(self._tag_for(fmt), self._index(run_start), self._index(run_end))

    def _retag(self, start: int, end: int) -> None:
        first, last = self._index(start), self._index(end)
        for tag in self._tag_of.values():
            self.text.tag_remove(tag, first, last)
        self._tag_runs(start, end)

    def _tag_for(self, fmt: Format) -> str:
        """The Tk tag that draws a format; created on first use."""
        if fmt not in self._tag_of:
            name = f"fmt{len(self._tag_of)}"
            self._tag_of[fmt] = name
            self._configure_tag(name, fmt)
            self.text.tag_lower(name)  # below the selection and the search highlights
        return self._tag_of[fmt]

    def _configure_tag(self, name: str, fmt: Format) -> None:
        theme = self._themes.theme
        heading = fmt.is_heading
        self.text.tag_configure(
            name,
            font=self._font_for(fmt),
            foreground=fmt.color or theme.text,
            background=fmt.highlight or "",
            underline=fmt.underline,
            overstrike=fmt.strike,
            justify=fmt.align,
            spacing1=px(12) if heading else 0,
            spacing3=px(6) if heading else px(5),
        )

    def _font_for(self, fmt: Format) -> tkfont.Font:
        family = fmt.family or self._fonts.document
        size = max(1, round(fmt.display_size * self._zoom))
        bold = fmt.bold or fmt.is_heading
        key = (family, size, bold, fmt.italic)
        if key not in self._font_cache:
            self._font_cache[key] = tkfont.Font(
                root=self.text, family=family, size=size,
                weight="bold" if bold else "normal", slant="italic" if fmt.italic else "roman")
        return self._font_cache[key]

    def _update_trailing_line(self) -> None:
        """Tk always has one more (empty) last line; give it the alignment being typed."""
        self.text.tag_configure("trail", justify=self.editor.pending_format.align)
        self.text.tag_remove("trail", "1.0", tk.END)
        self.text.tag_add("trail", "end-1c", tk.END)

    def _restyle(self) -> None:
        theme = self._themes.theme
        self.text.configure(
            background=theme.page, foreground=theme.text, insertbackground=theme.text,
            selectbackground=theme.selection, selectforeground=theme.text,
            inactiveselectbackground=theme.selection)
        self.frame.configure(background=theme.page)
        self.text.tag_configure("find_match", background=theme.find_match)
        self.text.tag_configure("find_current", background=theme.find_current)
        for fmt, name in self._tag_of.items():
            self._configure_tag(name, fmt)
        self._apply_base_font()

    def _apply_base_font(self) -> None:
        self._base_font = self._font_for(DEFAULT_FORMAT)
        self.text.configure(font=self._base_font)

    def set_zoom(self, zoom: float) -> None:
        self._zoom = zoom
        self._font_cache.clear()
        self._restyle()
        self.on_status_change()

    @property
    def zoom(self) -> float:
        return self._zoom

    def set_wrap(self, wrap: bool) -> None:
        self.text.configure(wrap="word" if wrap else "none")
        self._set_wrap(wrap)

    def _set_wrap(self, wrap: bool) -> None:
        if wrap:
            self.hscroll.pack_forget()
        else:
            self.hscroll.pack(side=tk.BOTTOM, fill=tk.X, before=self.text)

    def highlight_matches(self, matches: list[tuple[int, int]], current: tuple[int, int] | None) -> None:
        for name in FIND_TAGS:
            self.text.tag_remove(name, "1.0", tk.END)
        for start, end in matches[:MAX_HIGHLIGHTS]:
            self.text.tag_add("find_match", self._index(start), self._index(end))
        if current is not None:
            self.text.tag_add("find_current", self._index(current[0]), self._index(current[1]))

    # ===== keyboard and mouse ==================================================

    def _bind_events(self) -> None:
        text = self.text
        text.bind("<Key>", self._on_key)
        text.bind("<KeyRelease>", self._on_key_release)
        text.bind("<ButtonRelease-1>", lambda event: self._schedule_sync())
        text.bind("<<Selection>>", lambda event: self._schedule_sync())
        modifier = "Command" if sys.platform == "darwin" else "Control"
        text.bind(f"<{modifier}-Key>", self._on_shortcut)
        text.bind(f"<{modifier}-MouseWheel>", self._on_zoom_wheel)
        text.bind(f"<{modifier}-Button-4>", lambda event: self._on_zoom_wheel(event, 1))
        text.bind(f"<{modifier}-Button-5>", lambda event: self._on_zoom_wheel(event, -1))
        for sequence in BLOCKED_SEQUENCES:
            text.bind(sequence, lambda event: "break")

    def _on_shortcut(self, event: tk.Event) -> str | None:
        result = self._shortcut_handler(event)
        if result == "break":
            return "break"
        # Ctrl+letter that is not a shortcut: swallow it so Tk's emacs bindings stay silent.
        # Exception: a printable character typed with AltGr (Ctrl+Alt on Windows).
        if event.char and event.char.isprintable() and not event.char.isspace():
            self.editor.type_text(event.char, *self._caret_and_selection())
            return "break"
        return "break" if len(event.keysym) == 1 else None

    def _on_zoom_wheel(self, event: tk.Event, direction: int | None = None) -> str:
        step = direction if direction is not None else (1 if event.delta > 0 else -1)
        self.on_zoom_request(step)
        return "break"

    def _on_key(self, event: tk.Event) -> str | None:
        if event.state & ALT_MASK:
            return None  # menu accelerators
        caret, selection = self._caret_and_selection()
        key = event.keysym
        if key == "BackSpace":
            self.editor.backspace(caret, selection)
        elif key == "Delete":
            self.editor.delete_forward(caret, selection)
        elif key in ("Return", "KP_Enter"):
            self.editor.press_enter(caret, selection)
        elif key == "Tab":
            self.editor.type_text("\t", caret, selection)
        elif event.char and event.char.isprintable():
            self.editor.type_text(event.char, caret, selection)
        else:
            return None  # arrows, Home/End, PageUp/PageDown ... keep Tk's behavior
        return "break"

    def _on_key_release(self, event: tk.Event) -> None:
        if event.keysym in NAVIGATION_KEYS:
            self._schedule_sync()

    def _schedule_sync(self) -> None:
        """After the cursor or selection moved, the typing format follows the text."""
        if self._sync_job is None:
            self._sync_job = self.text.after_idle(self._sync_typing_format)

    def _sync_typing_format(self) -> None:
        self._sync_job = None
        try:
            self.editor.sync_pending(*self._caret_and_selection())
        except tk.TclError:
            return  # the widget was destroyed in the meantime
        self.on_status_change()

    # ===== clipboard actions (used by the menus and shortcuts) ================

    def copy(self) -> None:
        fragment = self.editor.copy(self.selection())
        if fragment is not None:
            self._clipboard.put(fragment)

    def cut(self) -> None:
        fragment = self.editor.cut(self.selection())
        if fragment is not None:
            self._clipboard.put(fragment)

    def paste(self) -> None:
        content = self._clipboard.get()
        if content:
            self.editor.paste(content, *self._caret_and_selection())

    # ===== offsets =============================================================

    def _caret_and_selection(self) -> tuple[int, Selection]:
        return self.caret(), self.selection()

    def _index(self, offset: int) -> str:
        line, column = self.document.line_col(offset)
        return f"{line}.{column}"

    def _offset(self, index: str) -> int:
        line, column = index.split(".")
        return self.document.position_of(int(line), int(column))

    def destroy(self) -> None:
        if self._sync_job is not None:
            self.text.after_cancel(self._sync_job)
        self.document.detach(self)
        self.editor.history.detach(self)
        self.editor.detach(self)
        self.frame.destroy()
