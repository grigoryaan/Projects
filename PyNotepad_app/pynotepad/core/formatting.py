"""Formatting attributes of a character and of the paragraph it belongs to.

`Format` is an immutable value object, and every character of a document carries
one. Paragraph-level attributes (alignment, heading level) are stored on every
character of the paragraph, so a paragraph needs no data structure of its own.
"""
from __future__ import annotations

from dataclasses import dataclass, fields, replace
from typing import Any

DEFAULT_SIZE = 12
MIN_SIZE = 6
MAX_SIZE = 96

ALIGN_LEFT = "left"
ALIGN_CENTER = "center"
ALIGN_RIGHT = "right"
ALIGNMENTS = (ALIGN_LEFT, ALIGN_CENTER, ALIGN_RIGHT)

PARAGRAPH = "p"
HEADING_1 = "h1"
HEADING_2 = "h2"
HEADING_3 = "h3"
BLOCK_NAMES = {
    PARAGRAPH: "Normal text",
    HEADING_1: "Heading 1",
    HEADING_2: "Heading 2",
    HEADING_3: "Heading 3",
}
# A heading scales the font size of its characters and makes them bold.
HEADING_SCALE = {PARAGRAPH: 1.0, HEADING_1: 2.0, HEADING_2: 1.5, HEADING_3: 1.25}

# Attributes that belong to single characters / to a whole paragraph.
CHAR_ATTRIBUTES = ("bold", "italic", "underline", "strike", "family", "size", "color", "highlight")
PARAGRAPH_ATTRIBUTES = ("align", "block")


@dataclass(frozen=True)
class Format:
    bold: bool = False
    italic: bool = False
    underline: bool = False
    strike: bool = False
    family: str = ""  # "" means the default font
    size: int = DEFAULT_SIZE
    color: str = ""  # "" means the default text color
    highlight: str = ""  # "" means no background
    align: str = ALIGN_LEFT
    block: str = PARAGRAPH

    def with_changes(self, **changes: Any) -> Format:
        return replace(self, **changes)

    @property
    def is_heading(self) -> bool:
        return self.block != PARAGRAPH

    @property
    def display_size(self) -> int:
        """Font size actually shown (headings are larger than their base size)."""
        return round(self.size * HEADING_SCALE[self.block])

    def for_new_paragraph(self) -> Format:
        """Format for text typed on a fresh line: a heading does not continue."""
        return replace(self, block=PARAGRAPH)

    # ----- (de)serialization --------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Only attributes that differ from the defaults (keeps files small)."""
        return {f.name: getattr(self, f.name) for f in fields(self) if getattr(self, f.name) != f.default}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Format:
        defaults = {f.name: f.default for f in fields(cls)}
        values: dict[str, Any] = {}
        for key, value in data.items():
            if key not in defaults or type(value) is not type(defaults[key]):
                raise ValueError(f"Invalid format attribute: {key!r}")
            values[key] = value
        result = cls(**values)
        if result.align not in ALIGNMENTS or result.block not in HEADING_SCALE:
            raise ValueError("Invalid paragraph attribute")
        return result


DEFAULT_FORMAT = Format()
