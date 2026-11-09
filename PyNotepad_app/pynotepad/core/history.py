"""Command history: the undo and redo stacks (the Invoker of the Command pattern).

Every tab owns its own CommandHistory, so switching between tabs never loses it.
"""
from __future__ import annotations

from pynotepad.core.commands import Command
from pynotepad.core.observer import Subject


class CommandHistory(Subject):
    def __init__(self, limit: int = 500) -> None:
        super().__init__()
        self._undo_stack: list[Command] = []
        self._redo_stack: list[Command] = []  # the last item is the next one to redo
        self._limit = limit

    # ----- state ------------------------------------------------------------

    @property
    def can_undo(self) -> bool:
        return bool(self._undo_stack)

    @property
    def can_redo(self) -> bool:
        return bool(self._redo_stack)

    @property
    def done_count(self) -> int:
        """How many steps are currently applied."""
        return len(self._undo_stack)

    @property
    def undo_description(self) -> str | None:
        """Name of the step Undo would revert, if any."""
        return self._undo_stack[-1].description if self._undo_stack else None

    @property
    def redo_description(self) -> str | None:
        """Name of the step Redo would apply, if any."""
        return self._redo_stack[-1].description if self._redo_stack else None

    @property
    def entries(self) -> list[tuple[str, bool]]:
        """The whole timeline: (description, is the step currently applied)."""
        done = [(command.description, True) for command in self._undo_stack]
        undone = [(command.description, False) for command in reversed(self._redo_stack)]
        return done + undone

    # ----- actions ----------------------------------------------------------

    def execute(self, command: Command) -> None:
        """Executes a new command. The redo branch is discarded."""
        command.execute()
        self._redo_stack.clear()
        if not (self._undo_stack and self._undo_stack[-1].merge(command)):
            self._undo_stack.append(command)
            if len(self._undo_stack) > self._limit:
                del self._undo_stack[0]
        self.notify()

    def undo(self) -> None:
        if not self.can_undo:
            return
        command = self._undo_stack.pop()
        command.undo()
        self._redo_stack.append(command)
        self.notify()

    def redo(self) -> None:
        if not self.can_redo:
            return
        command = self._redo_stack.pop()
        command.execute()
        self._undo_stack.append(command)
        self.notify()

    def go_to(self, done_count: int) -> None:
        """Jumps to any state of the timeline (0 is the very beginning)."""
        while self.done_count > done_count and self.can_undo:
            self.undo()
        while self.done_count < done_count and self.can_redo:
            self.redo()
