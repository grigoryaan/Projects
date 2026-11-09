"""The document: text plus a Format for every character.

Snapshot is the Memento of this program: an immutable copy of a fragment (text and
per-character formats). Commands keep snapshots to be able to undo themselves.

Document is the Receiver of the Command pattern: it only knows three elementary
operations (insert, delete, replace formats) and reports each one to its observers
through a DocumentChange. It knows nothing about history or the interface.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator, Sequence

from pynotepad.core.formatting import DEFAULT_FORMAT, Format
from pynotepad.core.observer import Subject

INSERT = "insert"
DELETE = "delete"
FORMAT = "format"


def _is_safe_char(char: str) -> bool:
    code = ord(char)
    if char in "\n\t":
        return True
    # No control characters, no lone surrogates, nothing outside the Basic Multilingual Plane.
    return code >= 32 and not 0x7F <= code < 0xA0 and not 0xD800 <= code <= 0xDFFF and code <= 0xFFFF


def normalize_text(text: str) -> str:
    """Unify line endings and replace characters the Tk text widget cannot handle.

    Characters are replaced one-for-one (never dropped), so offsets stay valid. Tk may
    count characters outside the Basic Multilingual Plane (e.g. emoji) differently from
    Python, which would desynchronize text offsets between the model and the widget.
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return "".join(char if _is_safe_char(char) else "�" for char in text)


@dataclass(frozen=True)
class Snapshot:
    """Memento: text of a fragment together with the format of each character."""

    text: str
    formats: tuple[Format, ...]

    @classmethod
    def uniform(cls, text: str, fmt: Format = DEFAULT_FORMAT) -> Snapshot:
        """A fragment in which every character has the same format."""
        return cls(text, (fmt,) * len(text))

    def __len__(self) -> int:
        return len(self.text)

    def __add__(self, other: Snapshot) -> Snapshot:
        return Snapshot(self.text + other.text, self.formats + other.formats)


@dataclass(frozen=True)
class DocumentChange:
    """What happened, reported to observers.

    kind   - INSERT, DELETE or FORMAT
    start, end - the affected range (for DELETE: the removed range, in old offsets)
    caret  - where the cursor belongs after the change (None: leave it alone)
    """

    kind: str
    start: int
    end: int
    caret: int | None = None


class Document(Subject):
    def __init__(self, content: Snapshot | None = None) -> None:
        super().__init__()
        if content is None:
            content = Snapshot("", ())
        self._text = content.text
        self._formats: list[Format] = list(content.formats)

    # ----- reading ----------------------------------------------------------

    @property
    def text(self) -> str:
        return self._text

    def __len__(self) -> int:
        return len(self._text)

    def format_at(self, position: int) -> Format:
        return self._formats[position]

    def snapshot(self, start: int, end: int) -> Snapshot:
        self._check_range(start, end)
        return Snapshot(self._text[start:end], tuple(self._formats[start:end]))

    def snapshot_all(self) -> Snapshot:
        return self.snapshot(0, len(self._text))

    def format_runs(self, start: int = 0, end: int | None = None) -> Iterator[tuple[int, int, Format]]:
        """Groups of consecutive characters with equal formats inside [start, end)."""
        end = len(self._text) if end is None else end
        position = start
        while position < end:
            fmt = self._formats[position]
            run_end = position + 1
            while run_end < end and self._formats[run_end] == fmt:
                run_end += 1
            yield position, run_end, fmt
            position = run_end

    def has_formatting(self) -> bool:
        return any(fmt != DEFAULT_FORMAT for fmt in self._formats)

    @property
    def word_count(self) -> int:
        return len(self._text.split())

    # ----- paragraphs (lines) -------------------------------------------------

    def line_col(self, position: int) -> tuple[int, int]:
        """(line, column) of an offset; the line is 1-based, the column 0-based (like Tk)."""
        return self._text.count("\n", 0, position) + 1, position - self.line_start(position)

    def position_of(self, line: int, column: int = 0) -> int:
        """Offset of a (line, column) pair; out-of-range values are clamped to the text."""
        position = 0
        for _ in range(line - 1):
            newline = self._text.find("\n", position)
            if newline == -1:
                return len(self._text)
            position = newline + 1
        return min(position + column, self.line_text_end(position))

    def line_start(self, position: int) -> int:
        return self._text.rfind("\n", 0, position) + 1

    def line_text_end(self, position: int) -> int:
        """End of the line's text, before its newline."""
        index = self._text.find("\n", position)
        return len(self._text) if index == -1 else index

    def line_end(self, position: int) -> int:
        """End of the line including its newline character."""
        index = self._text.find("\n", position)
        return len(self._text) if index == -1 else index + 1

    def paragraph_range(self, start: int, end: int) -> tuple[int, int]:
        """Whole paragraphs touched by [start, end) (or by the caret if start == end)."""
        last = end - 1 if end > start else start
        return self.line_start(start), self.line_end(last)

    def paragraph_starts(self, start: int, end: int) -> list[int]:
        """Offsets where the paragraphs touched by [start, end) begin."""
        last = end - 1 if end > start else start
        starts = []
        position = self.line_start(start)
        while True:
            starts.append(position)
            newline = self._text.find("\n", position)
            if newline == -1 or newline + 1 > last:
                return starts
            position = newline + 1

    # ----- elementary operations (called by commands) -----------------------

    def insert(self, position: int, fragment: Snapshot) -> None:
        self._check_range(position, position)
        self._text = self._text[:position] + fragment.text + self._text[position:]
        self._formats[position:position] = fragment.formats
        end = position + len(fragment)
        self.notify(DocumentChange(INSERT, position, end, caret=end))

    def delete(self, start: int, end: int) -> Snapshot:
        """Removes [start, end) and returns what was removed."""
        removed = self.snapshot(start, end)
        self._text = self._text[:start] + self._text[end:]
        del self._formats[start:end]
        self.notify(DocumentChange(DELETE, start, end, caret=start))
        return removed

    def replace_formats(self, start: int, end: int, formats: Sequence[Format]) -> None:
        """Replaces the formats of [start, end); the text itself is untouched."""
        self._check_range(start, end)
        if len(formats) != end - start:
            raise ValueError("Number of formats must match the length of the range")
        self._formats[start:end] = formats
        self.notify(DocumentChange(FORMAT, start, end))

    def _check_range(self, start: int, end: int) -> None:
        if not 0 <= start <= end <= len(self._text):
            raise IndexError(f"Range [{start}, {end}) is outside a document of length {len(self._text)}")
