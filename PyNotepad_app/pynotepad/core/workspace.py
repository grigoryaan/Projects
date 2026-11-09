"""The set of open tabs ("pages").

Every Page owns its own Editor, and therefore its own Document and its own undo
history. Switching tabs only changes which page is active, so no history is ever
lost. The Workspace is a Subject: the window listens to it to add, remove and
rename tabs.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from pynotepad.core.document import Document
from pynotepad.core.editor import Editor
from pynotepad.core.file_formats import HTML, FileFormat, format_for_path
from pynotepad.core.observer import Observer, Subject

ADDED = "added"
REMOVED = "removed"
ACTIVATED = "activated"
UPDATED = "updated"  # title, path or "modified" flag changed


class Page:
    """One tab: an editor plus the file it is bound to."""

    def __init__(self, editor: Editor, number: int, path: str | None = None) -> None:
        self.editor = editor
        self.number = number
        self.path = path
        self.modified = False

    @property
    def title(self) -> str:
        return os.path.basename(self.path) if self.path else f"Untitled {self.number}"

    @property
    def is_blank(self) -> bool:
        """An untouched new tab, safe to replace when a file is opened."""
        return self.path is None and not self.modified and len(self.editor.document) == 0


@dataclass(frozen=True)
class PageEvent:
    kind: str
    page: Page


class Workspace(Subject, Observer):
    def __init__(self) -> None:
        super().__init__()
        self._pages: list[Page] = []
        self._active: Page | None = None
        self._untitled_count = 0
        self._page_of: dict[Document, Page] = {}

    @property
    def pages(self) -> tuple[Page, ...]:
        return tuple(self._pages)

    @property
    def active(self) -> Page | None:
        return self._active

    # ----- tabs -------------------------------------------------------------

    def new_page(self) -> Page:
        return self._add(Editor())

    def open_file(self, path: str) -> Page:
        """Opens a file in a new tab (or just activates the tab that already has it)."""
        path = os.path.abspath(path)
        for page in self._pages:
            if page.path and os.path.abspath(page.path) == path:
                self.activate(page)
                return page
        snapshot = format_for_path(path).load(path)  # may raise OSError / ValueError
        blank = self._active if self._active is not None and self._active.is_blank else None
        page = self._add(Editor(Document(snapshot)), path)
        if blank is not None:
            self.close_page(blank)
        return page

    def close_page(self, page: Page) -> None:
        """Closes a tab. A workspace always keeps at least one tab."""
        index = self._pages.index(page)
        was_active = page is self._active
        self._pages.remove(page)
        page.editor.document.detach(self)
        del self._page_of[page.editor.document]
        self.notify(PageEvent(REMOVED, page))
        if not self._pages:
            self._active = None
            self.new_page()
        elif was_active:
            self.activate(self._pages[min(index, len(self._pages) - 1)])

    def activate(self, page: Page) -> None:
        if page is not self._active:
            self._active = page
            self.notify(PageEvent(ACTIVATED, page))

    # ----- files ------------------------------------------------------------

    def save(self, page: Page, path: str | None = None) -> None:
        """Saves the page (to `path`, or to the file it is bound to)."""
        path = os.path.abspath(path or page.path or "")
        format_for_path(path).save(page.editor.document.snapshot_all(), path)
        page.path = path
        page.modified = False
        self.notify(PageEvent(UPDATED, page))

    def export(self, page: Page, path: str, file_format: FileFormat = HTML) -> None:
        """Writes a copy in another format without rebinding the page to it."""
        file_format.save(page.editor.document.snapshot_all(), path)

    # ----- Observer: any change of a document marks its page as modified ----

    def update(self, subject: Any, event: Any = None) -> None:
        page = self._page_of.get(subject)
        if page is not None and not page.modified:
            page.modified = True
            self.notify(PageEvent(UPDATED, page))

    def _add(self, editor: Editor, path: str | None = None) -> Page:
        self._untitled_count += 0 if path else 1
        page = Page(editor, self._untitled_count, path)
        self._pages.append(page)
        self._page_of[editor.document] = page
        editor.document.attach(self)
        self.notify(PageEvent(ADDED, page))
        self.activate(page)
        return page
