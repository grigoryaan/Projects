"""Observer pattern.

A Subject keeps a list of observers and notifies them when it changes. This is
what keeps the model independent of the interface: the window subscribes to the
model and redraws itself, the model never knows the window exists.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable


class Observer(ABC):
    """Receives a notification whenever a subject it is attached to changes."""

    @abstractmethod
    def update(self, subject: Subject, event: Any = None) -> None:
        """Called by the subject. `event` carries optional details of the change."""


class Subject:
    """Keeps subscribers and broadcasts notifications to them."""

    def __init__(self) -> None:
        self._observers: list[Observer] = []

    def attach(self, observer: Observer) -> None:
        if observer not in self._observers:
            self._observers.append(observer)

    def detach(self, observer: Observer) -> None:
        if observer in self._observers:
            self._observers.remove(observer)

    def notify(self, event: Any = None) -> None:
        # Iterate over a copy: an observer may detach itself while being notified.
        for observer in list(self._observers):
            observer.update(self, event)


class CallbackObserver(Observer):
    """Adapter that turns a plain function into an Observer."""

    def __init__(self, callback: Callable[[], None]) -> None:
        self._callback = callback

    def update(self, subject: Subject, event: Any = None) -> None:
        self._callback()


class EventObserver(Observer):
    """Like CallbackObserver, but the callback receives the event."""

    def __init__(self, callback: Callable[[Any], None]) -> None:
        self._callback = callback

    def update(self, subject: Subject, event: Any = None) -> None:
        self._callback(event)
