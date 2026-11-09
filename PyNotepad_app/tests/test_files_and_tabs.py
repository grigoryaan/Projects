"""Tests of file formats (Strategy) and of the tabs workspace."""
import json
import os
import tempfile
import unittest

from pynotepad.core.document import Document, Snapshot
from pynotepad.core.file_formats import HTML, NATIVE, PLAIN_TEXT, format_for_path
from pynotepad.core.formatting import ALIGN_CENTER, DEFAULT_FORMAT, HEADING_1, Format
from pynotepad.core.observer import CallbackObserver
from pynotepad.core.workspace import ACTIVATED, ADDED, REMOVED, UPDATED, Workspace


def formatted_snapshot() -> Snapshot:
    bold = Format(bold=True, color="#ff0000", size=18)
    heading = Format(block=HEADING_1, align=ALIGN_CENTER)
    return Snapshot("Hello <b>\nTitle", (DEFAULT_FORMAT,) * 6 + (bold,) * 3 + (heading,) * 6)


class FileFormatTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)

    def path(self, name):
        return os.path.join(self.folder.name, name)

    def test_native_format_round_trip_keeps_formatting(self):
        snapshot = formatted_snapshot()
        NATIVE.save(snapshot, self.path("a.pnote"))
        self.assertEqual(NATIVE.load(self.path("a.pnote")), snapshot)

    def test_native_file_is_compact_json(self):
        NATIVE.save(formatted_snapshot(), self.path("a.pnote"))
        with open(self.path("a.pnote"), encoding="utf-8") as file:
            payload = json.load(file)
        self.assertEqual(len(payload["runs"]), 2)  # default runs are not stored

    def test_native_format_rejects_garbage(self):
        for content in ("not json", '{"version": 1}', '{"version":1,"text":"ab","runs":[{"start":0,"end":9,"format":{}}]}',
                        '{"version":1,"text":"ab","runs":[{"start":0,"end":1,"format":{"bold":"yes"}}]}'):
            with open(self.path("bad.pnote"), "w", encoding="utf-8") as file:
                file.write(content)
            with self.assertRaises(ValueError, msg=content):
                NATIVE.load(self.path("bad.pnote"))

    def test_plain_text_round_trip_loses_formatting(self):
        PLAIN_TEXT.save(formatted_snapshot(), self.path("a.txt"))
        loaded = PLAIN_TEXT.load(self.path("a.txt"))
        self.assertEqual(loaded.text, formatted_snapshot().text)
        self.assertEqual(set(loaded.formats), {DEFAULT_FORMAT})

    def test_plain_text_reads_windows_line_endings_and_bom(self):
        with open(self.path("w.txt"), "wb") as file:
            file.write(b"\xef\xbb\xbfone\r\ntwo")
        self.assertEqual(PLAIN_TEXT.load(self.path("w.txt")).text, "one\ntwo")

    def test_html_export_contains_formatting_and_escapes(self):
        HTML.save(formatted_snapshot(), self.path("a.html"))
        with open(self.path("a.html"), encoding="utf-8") as file:
            page = file.read()
        self.assertIn("&lt;b&gt;", page)
        self.assertIn("<h1 style=\"text-align:center\">", page)
        self.assertIn("font-weight:bold", page)
        self.assertIn("color:#ff0000", page)

    def test_html_cannot_be_opened(self):
        with self.assertRaises(NotImplementedError):
            HTML.load(self.path("a.html"))

    def test_format_is_chosen_by_extension(self):
        self.assertIs(format_for_path("x.PNOTE"), NATIVE)
        self.assertIs(format_for_path("x.txt"), PLAIN_TEXT)
        self.assertIs(format_for_path("x.md"), PLAIN_TEXT)


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.workspace = Workspace()
        self.events = []
        self.workspace.attach(CallbackObserver(lambda: None))
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)

    def record(self):
        events = []

        class Spy(CallbackObserver):
            def update(self, subject, event=None):
                events.append((event.kind, event.page))

        self.workspace.attach(Spy(lambda: None))
        return events

    def test_new_pages_are_numbered_and_activated(self):
        events = self.record()
        first, second = self.workspace.new_page(), self.workspace.new_page()
        self.assertEqual((first.title, second.title), ("Untitled 1", "Untitled 2"))
        self.assertIs(self.workspace.active, second)
        self.assertEqual([kind for kind, _ in events], [ADDED, ACTIVATED, ADDED, ACTIVATED])

    def test_switching_tabs_keeps_each_history(self):
        first, second = self.workspace.new_page(), self.workspace.new_page()
        first.editor.type_text("one", caret=0)
        second.editor.type_text("two", caret=0)
        second.editor.type_text("!!", caret=3)
        self.workspace.activate(first)
        self.workspace.activate(second)
        self.workspace.activate(first)
        self.assertEqual(len(first.editor.history.entries), 1)
        self.assertEqual(len(second.editor.history.entries), 2)
        second.editor.undo()
        self.assertEqual(second.editor.document.text, "two")
        self.assertEqual(first.editor.document.text, "one")

    def test_modified_flag_and_updated_event(self):
        page = self.workspace.new_page()
        self.assertFalse(page.modified)
        events = self.record()
        page.editor.type_text("x", caret=0)
        page.editor.type_text("y", caret=1)
        self.assertTrue(page.modified)
        self.assertEqual([kind for kind, _ in events], [UPDATED])  # reported once

    def test_closing_active_page_activates_a_neighbour(self):
        first, second, third = (self.workspace.new_page() for _ in range(3))
        self.workspace.activate(second)
        self.workspace.close_page(second)
        self.assertIs(self.workspace.active, third)
        self.assertEqual(self.workspace.pages, (first, third))

    def test_closing_the_last_page_leaves_a_fresh_one(self):
        only = self.workspace.new_page()
        events = self.record()
        self.workspace.close_page(only)
        self.assertEqual(len(self.workspace.pages), 1)
        self.assertIsNot(self.workspace.active, only)
        self.assertEqual(events[0][0], REMOVED)

    def test_save_and_open_round_trip_in_a_new_tab(self):
        page = self.workspace.new_page()
        page.editor.type_text("hello", caret=0)
        page.editor.toggle_attribute("bold", selection=(0, 5))
        path = os.path.join(self.folder.name, "note.pnote")
        self.workspace.save(page, path)
        self.assertFalse(page.modified)
        self.assertEqual(page.title, "note.pnote")

        self.workspace.close_page(page)  # a file that is still open would just be re-activated
        opened = self.workspace.open_file(path)
        self.assertEqual(opened.editor.document.text, "hello")
        self.assertTrue(opened.editor.document.format_at(0).bold)
        self.assertFalse(opened.modified)
        self.assertFalse(opened.editor.history.can_undo)

    def test_opening_the_same_file_twice_activates_the_existing_tab(self):
        path = os.path.join(self.folder.name, "a.txt")
        with open(path, "w", encoding="utf-8") as file:
            file.write("text")
        first = self.workspace.open_file(path)
        self.workspace.new_page()
        again = self.workspace.open_file(path)
        self.assertIs(first, again)
        self.assertIs(self.workspace.active, first)

    def test_opening_a_file_replaces_a_blank_tab(self):
        path = os.path.join(self.folder.name, "a.txt")
        with open(path, "w", encoding="utf-8") as file:
            file.write("text")
        blank = self.workspace.new_page()
        opened = self.workspace.open_file(path)
        self.assertNotIn(blank, self.workspace.pages)
        self.assertEqual(self.workspace.pages, (opened,))

    def test_failed_open_changes_nothing(self):
        blank = self.workspace.new_page()
        with self.assertRaises(OSError):
            self.workspace.open_file(os.path.join(self.folder.name, "missing.txt"))
        self.assertEqual(self.workspace.pages, (blank,))

    def test_export_does_not_rebind_the_page(self):
        page = self.workspace.new_page()
        page.editor.type_text("x", caret=0)
        self.workspace.export(page, os.path.join(self.folder.name, "x.html"))
        self.assertIsNone(page.path)
        self.assertTrue(page.modified)


if __name__ == "__main__":
    unittest.main()
