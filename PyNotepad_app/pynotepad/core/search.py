"""Text search and word navigation helpers (pure functions, no state)."""
from __future__ import annotations

import re

Match = tuple[int, int]


def _pattern(query: str, match_case: bool) -> re.Pattern[str]:
    # A regex is used only for case-insensitive matching with correct offsets
    # (str.lower() can change the length of a string, which would shift indices).
    return re.compile(re.escape(query), 0 if match_case else re.IGNORECASE)


def find_all(text: str, query: str, match_case: bool = False) -> list[Match]:
    if not query:
        return []
    return [match.span() for match in _pattern(query, match_case).finditer(text)]


def find_next(text: str, query: str, start: int, match_case: bool = False,
              backwards: bool = False) -> Match | None:
    """Next match at or after `start` (or the previous one before it), wrapping around."""
    matches = find_all(text, query, match_case)
    if not matches:
        return None
    if backwards:
        earlier = [match for match in matches if match[1] <= start]
        return earlier[-1] if earlier else matches[-1]
    later = [match for match in matches if match[0] >= start]
    return later[0] if later else matches[0]


def word_boundary(text: str, position: int, forward: bool) -> int:
    """Where Ctrl+Delete / Ctrl+Backspace should stop: after skipping spaces, one whole word."""
    step = 1 if forward else -1
    limit = len(text) if forward else 0

    def char_at(index: int) -> str:
        return text[index] if forward else text[index - 1]

    def is_word_char(char: str) -> bool:
        return char.isalnum() or char == "_"

    index = position
    while index != limit and char_at(index).isspace():
        index += step
    if index != limit:
        in_word = is_word_char(char_at(index))
        while index != limit and not char_at(index).isspace() and is_word_char(char_at(index)) == in_word:
            index += step
    return index
