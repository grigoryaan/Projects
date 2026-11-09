"""Strategy pattern: interchangeable file formats.

Each FileFormat knows how to turn a Snapshot of the document into a file and
back. The workspace picks a strategy from the file extension and does not care
how it works.

- NativeFormat   (.pnote) keeps text and all formatting (JSON).
- PlainTextFormat (.txt)  keeps text only.
- HtmlFormat     (.html) export only: keeps formatting for the web.
"""
from __future__ import annotations

import html
import json
import os
from abc import ABC, abstractmethod
from typing import Iterator

from pynotepad import APP_NAME
from pynotepad.core.document import Snapshot, normalize_text
from pynotepad.core.formatting import DEFAULT_FORMAT, DEFAULT_SIZE, Format


class FileFormat(ABC):
    extension: str
    label: str
    lossy: bool = False  # True if saving drops formatting

    @abstractmethod
    def save(self, snapshot: Snapshot, path: str) -> None: ...

    def load(self, path: str) -> Snapshot:
        raise NotImplementedError(f"{self.label} files cannot be opened")


class NativeFormat(FileFormat):
    extension = ".pnote"
    label = f"{APP_NAME} document"
    VERSION = 1

    def save(self, snapshot: Snapshot, path: str) -> None:
        runs = []
        position = 0
        formats = snapshot.formats
        while position < len(formats):
            end = position + 1
            while end < len(formats) and formats[end] == formats[position]:
                end += 1
            if formats[position] != DEFAULT_FORMAT:
                runs.append({"start": position, "end": end, "format": formats[position].to_dict()})
            position = end
        payload = {"app": APP_NAME, "version": self.VERSION, "text": snapshot.text, "runs": runs}
        with open(path, "w", encoding="utf-8") as file:
            json.dump(payload, file, ensure_ascii=False, separators=(",", ":"))

    def load(self, path: str) -> Snapshot:
        with open(path, encoding="utf-8") as file:
            try:
                payload = json.load(file)
                text = payload["text"]
                if not isinstance(text, str) or payload.get("version") != self.VERSION:
                    raise ValueError
                clean_text = normalize_text(text)
                if len(clean_text) != len(text):
                    raise ValueError
                formats = [DEFAULT_FORMAT] * len(text)
                for run in payload["runs"]:
                    start, end = run["start"], run["end"]
                    if not (isinstance(start, int) and isinstance(end, int) and 0 <= start <= end <= len(text)):
                        raise ValueError
                    formats[start:end] = [Format.from_dict(run["format"])] * (end - start)
            except (KeyError, TypeError, ValueError, AttributeError) as error:
                raise ValueError(f"{os.path.basename(path)} is not a valid {APP_NAME} document") from error
        return Snapshot(clean_text, tuple(formats))


class PlainTextFormat(FileFormat):
    extension = ".txt"
    label = "Plain text"
    lossy = True

    def save(self, snapshot: Snapshot, path: str) -> None:
        with open(path, "w", encoding="utf-8", newline="\n") as file:
            file.write(snapshot.text)

    def load(self, path: str) -> Snapshot:
        with open(path, encoding="utf-8-sig", errors="replace") as file:
            return Snapshot.uniform(normalize_text(file.read()))


class HtmlFormat(FileFormat):
    extension = ".html"
    label = "HTML page"

    def save(self, snapshot: Snapshot, path: str) -> None:
        title = html.escape(os.path.splitext(os.path.basename(path))[0])
        body = "\n".join(self._paragraph(text, formats, para) for text, formats, para in self._lines(snapshot))
        page = (
            "<!doctype html>\n<html><head><meta charset=\"utf-8\">"
            f"<title>{title}</title></head>\n"
            "<body style=\"font-family:sans-serif;font-size:12pt;max-width:820px;margin:2rem auto;"
            f"line-height:1.5\">\n{body}\n</body></html>\n"
        )
        with open(path, "w", encoding="utf-8") as file:
            file.write(page)

    @staticmethod
    def _lines(snapshot: Snapshot) -> Iterator[tuple[str, tuple[Format, ...], Format]]:
        """Yields (text, character formats, paragraph format) for every line."""
        text, formats = snapshot.text, snapshot.formats
        start = 0
        while True:
            newline = text.find("\n", start)
            stop = len(text) if newline == -1 else newline
            if newline != -1:
                paragraph = formats[newline]
            else:
                paragraph = formats[start] if start < stop else DEFAULT_FORMAT
            yield text[start:stop], formats[start:stop], paragraph
            if newline == -1:
                return
            start = newline + 1

    @classmethod
    def _paragraph(cls, text: str, formats: tuple[Format, ...], paragraph: Format) -> str:
        tag = "p" if not paragraph.is_heading else paragraph.block
        style = f' style="text-align:{paragraph.align}"' if paragraph.align != "left" else ""
        spans = []
        position = 0
        while position < len(text):
            end = position + 1
            while end < len(text) and formats[end] == formats[position]:
                end += 1
            spans.append(cls._span(text[position:end], formats[position]))
            position = end
        return f"<{tag}{style}>{''.join(spans) or '<br>'}</{tag}>"

    @staticmethod
    def _span(text: str, fmt: Format) -> str:
        css = []
        if fmt.bold:
            css.append("font-weight:bold")
        if fmt.italic:
            css.append("font-style:italic")
        decorations = [name for flag, name in ((fmt.underline, "underline"), (fmt.strike, "line-through")) if flag]
        if decorations:
            css.append("text-decoration:" + " ".join(decorations))
        if fmt.family:
            css.append(f"font-family:'{fmt.family}'")
        if fmt.size != DEFAULT_SIZE and not fmt.is_heading:
            css.append(f"font-size:{fmt.size}pt")
        if fmt.color:
            css.append(f"color:{fmt.color}")
        if fmt.highlight:
            css.append(f"background-color:{fmt.highlight}")
        escaped = html.escape(text).replace("\t", "&emsp;")
        return f'<span style="{";".join(css)}">{escaped}</span>' if css else escaped


NATIVE = NativeFormat()
PLAIN_TEXT = PlainTextFormat()
HTML = HtmlFormat()


def format_for_path(path: str) -> FileFormat:
    """Factory: picks the format by file extension (unknown extensions are plain text)."""
    return NATIVE if os.path.splitext(path)[1].lower() == NATIVE.extension else PLAIN_TEXT
