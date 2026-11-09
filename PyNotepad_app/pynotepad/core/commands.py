"""Command pattern (plus Composite for macro commands).

Every user action is an object with execute() and undo(). A command stores
everything it needs to undo itself, usually a Snapshot (Memento) of the region it
changed. Roles: Command - interface, Document - receiver, CommandHistory - invoker,
Editor - client that creates the commands.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Mapping, Sequence

from pynotepad.core.document import Document, Snapshot


def preview(text: str, limit: int = 24) -> str:
    """Short single-line version of a text for history entries."""
    text = text.replace("\n", "↵").replace("\t", "→")
    return text if len(text) <= limit else text[:limit] + "…"


class Command(ABC):
    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable name shown in the history panel."""

    @abstractmethod
    def execute(self) -> None:
        """Performs the action (also used again for redo)."""

    @abstractmethod
    def undo(self) -> None:
        """Reverts the action."""

    def merge(self, other: Command) -> bool:
        """Try to absorb the command executed right after this one.

        Lets a typed word, or a series of Backspaces, be undone in one step.
        Returns True if `other` was absorbed and must not be stored separately.
        """
        return False


class InsertCommand(Command):
    def __init__(self, document: Document, position: int, fragment: Snapshot, description: str | None = None) -> None:
        self._document = document
        self._position = position
        self._fragment = fragment
        self._description = description

    @property
    def description(self) -> str:
        return self._description or f'Type "{preview(self._fragment.text)}"'

    def execute(self) -> None:
        self._document.insert(self._position, self._fragment)

    def undo(self) -> None:
        self._document.delete(self._position, self._position + len(self._fragment))

    def merge(self, other: Command) -> bool:
        if not isinstance(other, InsertCommand) or self._description or other._description:
            return False
        continues_here = other._position == self._position + len(self._fragment)
        same_format = other._fragment.formats[0] == self._fragment.formats[-1]
        is_typing = len(other._fragment) == 1 and other._fragment.text != "\n"
        word_goes_on = not self._fragment.text[-1].isspace()  # a space ends the undo step
        if continues_here and same_format and is_typing and word_goes_on:
            self._fragment = self._fragment + other._fragment
            return True
        return False


class DeleteCommand(Command):
    """Deletes [start, end); the removed fragment is kept as a Snapshot."""

    def __init__(self, document: Document, start: int, end: int, mergeable: bool = False,
                 description: str | None = None) -> None:
        self._document = document
        self.start = start
        self.end = end
        self.mergeable = mergeable  # True for single Backspace / Delete key presses
        self._description = description
        self._removed: Snapshot | None = None

    @property
    def description(self) -> str:
        if self._description:
            return self._description
        return f'Delete "{preview(self._removed.text if self._removed else "")}"'

    def execute(self) -> None:
        self._removed = self._document.delete(self.start, self.end)

    def undo(self) -> None:
        assert self._removed is not None, "undo() called before execute()"
        self._document.insert(self.start, self._removed)

    def merge(self, other: Command) -> bool:
        if not (isinstance(other, DeleteCommand) and self.mergeable and other.mergeable):
            return False
        assert self._removed is not None and other._removed is not None
        if other.end == self.start:  # Backspace: the next character on the left
            self.start = other.start
            self._removed = other._removed + self._removed
            return True
        if other.start == self.start:  # Delete: the next character on the right
            self.end += other.end - other.start
            self._removed = self._removed + other._removed
            return True
        return False


class FormatCommand(Command):
    """Changes formatting attributes of [start, end), e.g. {"bold": True}."""

    def __init__(self, document: Document, start: int, end: int, changes: Mapping[str, Any],
                 description: str) -> None:
        self._document = document
        self._start = start
        self._end = end
        self._changes = dict(changes)
        self._description = description
        self._before: Snapshot | None = None

    @property
    def description(self) -> str:
        return self._description

    def execute(self) -> None:
        self._before = self._document.snapshot(self._start, self._end)  # Memento
        new_formats = [fmt.with_changes(**self._changes) for fmt in self._before.formats]
        self._document.replace_formats(self._start, self._end, new_formats)

    def undo(self) -> None:
        assert self._before is not None, "undo() called before execute()"
        self._document.replace_formats(self._start, self._end, self._before.formats)


class MacroCommand(Command):
    """Composite: several commands executed and undone as a single step."""

    def __init__(self, commands: Sequence[Command], description: str) -> None:
        self._commands = list(commands)
        self._description = description

    @property
    def description(self) -> str:
        return self._description

    def execute(self) -> None:
        for command in self._commands:
            command.execute()

    def undo(self) -> None:
        for command in reversed(self._commands):
            command.undo()
