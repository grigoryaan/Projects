"""Facade: the single entry point the interface uses to edit a document.

The window never builds commands itself. It calls simple methods such as
`type_text`, `toggle_attribute` or `set_alignment`; the Editor turns them into
commands and hands them to the history.

Offsets are character positions from the start of the text; a selection is a
(start, end) pair or None.

Typing format
-------------
The editor keeps a `pending_format`: the format given to the next typed characters.
Toolbar actions always change it (even when they also reformat a selection), so
what you chose stays active while you keep writing. It is re-synchronised with the
document only when the cursor or the selection moves (`sync_pending`).
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pynotepad.core import search
from pynotepad.core.commands import (
    Command,
    DeleteCommand,
    FormatCommand,
    InsertCommand,
    MacroCommand,
    preview,
)
from pynotepad.core.document import Document, Snapshot, normalize_text
from pynotepad.core.formatting import (
    ALIGN_LEFT,
    BLOCK_NAMES,
    CHAR_ATTRIBUTES,
    DEFAULT_FORMAT,
    MAX_SIZE,
    MIN_SIZE,
    Format,
)
from pynotepad.core.history import CommandHistory
from pynotepad.core.observer import Subject

Selection = tuple[int, int] | None

BULLET = "• "

_TOGGLE_LABELS = {
    "bold": ("Remove bold", "Bold"),
    "italic": ("Remove italic", "Italic"),
    "underline": ("Remove underline", "Underline"),
    "strike": ("Remove strikethrough", "Strikethrough"),
}


class Editor(Subject):
    """Notifies its observers when the typing format changes."""

    def __init__(self, document: Document | None = None) -> None:
        super().__init__()
        self.document = document if document is not None else Document()
        self.history = CommandHistory()
        self._pending: Format = DEFAULT_FORMAT
        # True while a toolbar format change is being applied: the typing format was just
        # chosen explicitly, so the document change it causes must not overwrite it.
        self._applying_format = False

    @property
    def pending_format(self) -> Format:
        return self._pending

    # ===== typing and deleting ==============================================

    def type_text(self, text: str, caret: int, selection: Selection = None) -> None:
        """Types text in the current typing format; a selection is replaced."""
        text = normalize_text(text)
        if text:
            self._insert_fragment(Snapshot.uniform(text, self._pending), caret, selection, None)

    def paste(self, content: str | Snapshot, caret: int, selection: Selection = None) -> None:
        """Pastes plain text (typing format) or a formatted fragment (its own formats)."""
        if isinstance(content, str):
            content = Snapshot.uniform(normalize_text(content), self._pending)
        if len(content):
            self._insert_fragment(content, caret, selection, f'Paste "{preview(content.text)}"')

    def press_enter(self, caret: int, selection: Selection = None) -> None:
        """Enter key. Inside a bullet list it continues (or ends) the list."""
        if self._selected_range(selection) is None:
            doc = self.document
            line_start = doc.line_start(caret)
            if doc.text.startswith(BULLET, line_start) and caret >= line_start + len(BULLET):
                if doc.text[line_start:doc.line_text_end(caret)] == BULLET:  # empty item
                    self._execute(DeleteCommand(doc, line_start, line_start + len(BULLET),
                                                description="End bullet list"))
                else:
                    self.type_text("\n" + BULLET, caret)
                return
        self.type_text("\n", caret, selection)

    def backspace(self, caret: int, selection: Selection = None) -> None:
        selected = self._selected_range(selection)
        if selected:
            self._delete(*selected, mergeable=False)
        elif caret > 0:
            self._delete(caret - 1, caret, mergeable=True)

    def delete_forward(self, caret: int, selection: Selection = None) -> None:
        selected = self._selected_range(selection)
        if selected:
            self._delete(*selected, mergeable=False)
        elif caret < len(self.document):
            self._delete(caret, caret + 1, mergeable=True)

    def delete_word(self, caret: int, selection: Selection = None, forward: bool = False) -> None:
        """Ctrl+Backspace / Ctrl+Delete."""
        selected = self._selected_range(selection)
        if selected is None:
            boundary = search.word_boundary(self.document.text, caret, forward)
            selected = (min(caret, boundary), max(caret, boundary))
        if selected[0] < selected[1]:
            self._execute(DeleteCommand(self.document, *selected, description="Delete word"))

    def copy(self, selection: Selection) -> Snapshot | None:
        """The selected fragment with its formatting (for the clipboard), or None."""
        selected = self._selected_range(selection)
        return self.document.snapshot(*selected) if selected else None

    def cut(self, selection: Selection) -> Snapshot | None:
        """Deletes the selection and returns it (for the clipboard), or None."""
        fragment = self.copy(selection)
        if fragment is not None:
            self._delete(*self._selected_range(selection), mergeable=False)
        return fragment

    def insert_timestamp(self, caret: int, selection: Selection = None) -> None:
        self.type_text(datetime.now().strftime("%Y-%m-%d %H:%M"), caret, selection)

    # ===== character formatting ============================================

    def toggle_attribute(self, name: str, selection: Selection = None) -> None:
        """Toggles bold / italic / underline / strike."""
        selected = self._selected_range(selection)
        if selected:
            formats = self.document.snapshot(*selected).formats
            enable = not all(getattr(fmt, name) for fmt in formats)
        else:
            enable = not getattr(self._pending, name)
        self.apply_char_format({name: enable}, selection, _TOGGLE_LABELS[name][enable])

    def set_font_family(self, family: str, selection: Selection = None) -> None:
        self.apply_char_format({"family": family}, selection, f"Font {family or 'Default'}")

    def set_font_size(self, size: int, selection: Selection = None) -> None:
        size = max(MIN_SIZE, min(MAX_SIZE, int(size)))
        self.apply_char_format({"size": size}, selection, f"Font size {size}")

    def change_font_size(self, delta: int, selection: Selection = None) -> None:
        selected = self._selected_range(selection)
        base = self.document.format_at(selected[0]).size if selected else self._pending.size
        self.set_font_size(base + delta, selection)

    def set_text_color(self, color: str, selection: Selection = None) -> None:
        self.apply_char_format({"color": color}, selection, "Text color" if color else "Default text color")

    def set_highlight(self, color: str, selection: Selection = None) -> None:
        self.apply_char_format({"highlight": color}, selection, "Highlight" if color else "Remove highlight")

    def clear_formatting(self, selection: Selection = None) -> None:
        changes = {name: getattr(DEFAULT_FORMAT, name) for name in CHAR_ATTRIBUTES}
        self.apply_char_format(changes, selection, "Clear formatting")

    def apply_char_format(self, changes: dict[str, Any], selection: Selection, description: str) -> None:
        """Changes the typing format and, if text is selected, the selected characters."""
        self._set_pending(self._pending.with_changes(**changes))
        selected = self._selected_range(selection)
        if selected:
            self._apply_format(*selected, changes, description)

    # ===== paragraph formatting ============================================

    def set_alignment(self, align: str, caret: int, selection: Selection = None) -> None:
        self.apply_paragraph_format({"align": align}, caret, selection, f"Align {align}")

    def set_block(self, block: str, caret: int, selection: Selection = None) -> None:
        self.apply_paragraph_format({"block": block}, caret, selection, BLOCK_NAMES[block])

    def apply_paragraph_format(self, changes: dict[str, Any], caret: int, selection: Selection,
                               description: str) -> None:
        """Applies the change to every paragraph touched by the selection or the caret."""
        doc = self.document
        selected = self._selected_range(selection) or (caret, caret)
        start, end = doc.paragraph_range(*selected)
        # The typing format changes only if the cursor is inside the paragraphs being changed
        # (not when it sits at the start of the next paragraph).
        at_next_paragraph = caret == end and end > start and doc.text[end - 1] == "\n"
        if start <= caret <= end and not at_next_paragraph:
            self._set_pending(self._pending.with_changes(**changes))
        if start < end:  # an empty last line has no characters to change yet
            self._apply_format(start, end, changes, description)

    def toggle_bullets(self, caret: int, selection: Selection = None) -> None:
        """Adds or removes a bullet at the start of every touched paragraph."""
        doc = self.document
        starts = doc.paragraph_starts(*(self._selected_range(selection) or (caret, caret)))
        all_bulleted = all(doc.text.startswith(BULLET, start) for start in starts)
        commands: list[Command] = []
        for start in reversed(starts):  # from the end, so earlier offsets stay valid
            if all_bulleted:
                commands.append(DeleteCommand(doc, start, start + len(BULLET)))
            elif not doc.text.startswith(BULLET, start):
                fmt = doc.format_at(start) if start < len(doc) else self._pending
                commands.append(InsertCommand(doc, start, Snapshot.uniform(BULLET, fmt)))
        if commands:
            self._execute(MacroCommand(commands, "Remove bullets" if all_bulleted else "Bullet list"))

    def sync_pending(self, caret: int, selection: Selection = None) -> None:
        """Takes the typing format from the document around the cursor."""
        if self._applying_format:
            return
        doc = self.document
        selected = self._selected_range(selection)
        caret = min(caret, len(doc))
        if selected:
            fmt = doc.format_at(selected[0])
        elif caret > 0 and doc.text[caret - 1] != "\n":
            fmt = doc.format_at(caret - 1)
        elif caret < len(doc):
            fmt = doc.format_at(caret)
        elif caret > 0:  # a fresh empty line at the end: continue, but not a heading
            fmt = doc.format_at(caret - 1).for_new_paragraph()
        else:
            fmt = DEFAULT_FORMAT
        self._set_pending(fmt)

    # ===== find and replace ================================================

    def find(self, query: str, start: int, match_case: bool = False, backwards: bool = False):
        return search.find_next(self.document.text, query, start, match_case, backwards)

    def is_match(self, start: int, end: int, query: str, match_case: bool = False) -> bool:
        found = self.document.snapshot(start, end).text
        return bool(query) and (found == query if match_case else found.casefold() == query.casefold())

    def replace_range(self, start: int, end: int, text: str) -> None:
        """Replaces [start, end) with text that keeps the format of the first character."""
        fragment = Snapshot.uniform(normalize_text(text), self.document.format_at(start))
        self._replace(start, end, fragment, f'Replace with "{preview(text)}"')

    def replace_all(self, query: str, replacement: str, match_case: bool = False) -> int:
        """Replaces every match in one undoable step. Returns how many were replaced."""
        matches = search.find_all(self.document.text, query, match_case)
        if not matches:
            return 0
        replacement = normalize_text(replacement)
        commands: list[Command] = []
        for start, end in reversed(matches):  # from the end, so earlier offsets stay valid
            commands.append(DeleteCommand(self.document, start, end))
            if replacement:
                fragment = Snapshot.uniform(replacement, self.document.format_at(start))
                commands.append(InsertCommand(self.document, start, fragment))
        description = f'Replace all "{preview(query, 12)}" ({len(matches)})'
        self._execute(MacroCommand(commands, description))
        return len(matches)

    # ===== history =========================================================

    def undo(self) -> None:
        self.history.undo()

    def redo(self) -> None:
        self.history.redo()

    # ===== internals =======================================================

    def _execute(self, command: Command) -> None:
        self.history.execute(command)

    def _delete(self, start: int, end: int, mergeable: bool) -> None:
        self._execute(DeleteCommand(self.document, start, end, mergeable))

    def _insert_fragment(self, fragment: Snapshot, caret: int, selection: Selection,
                         description: str | None) -> None:
        """Inserts a fragment at the caret, or in place of the selection (one undo step)."""
        selected = self._selected_range(selection)
        if selected is None:
            self._execute(InsertCommand(self.document, caret, fragment, description))
        else:
            self._replace(*selected, fragment, description or f'Replace with "{preview(fragment.text)}"')

    def _replace(self, start: int, end: int, fragment: Snapshot, description: str) -> None:
        self._execute(MacroCommand(
            [DeleteCommand(self.document, start, end), InsertCommand(self.document, start, fragment)],
            description,
        ))

    def _apply_format(self, start: int, end: int, changes: dict[str, Any], description: str) -> None:
        formats = self.document.snapshot(start, end).formats
        if any(fmt.with_changes(**changes) != fmt for fmt in formats):  # skip no-op steps
            self._applying_format = True
            try:
                self._execute(FormatCommand(self.document, start, end, changes, description))
            finally:
                self._applying_format = False

    def _set_pending(self, fmt: Format) -> None:
        if fmt != self._pending:
            self._pending = fmt
            self.notify()

    @staticmethod
    def _selected_range(selection: Selection) -> tuple[int, int] | None:
        """The selection as an ordered, non-empty range (or None)."""
        if selection is None:
            return None
        start, end = sorted(selection)
        return (start, end) if start < end else None
