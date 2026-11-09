"""GUI tests: drive the real window with simulated key presses (skipped without a display).

Run with a virtual display if you have none:  xvfb-run -a python -m unittest tests.test_gui -v
"""
import os
import random
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

try:
    import tkinter as tk

    from pynotepad.ui.app import App
except ImportError as error:  # Python built without Tkinter
    raise unittest.SkipTest(f"tkinter is not available: {error}")

from pynotepad.core.formatting import DEFAULT_FORMAT, HEADING_1, PARAGRAPH
from pynotepad.settings import Settings


def key_event(keysym, char="", state=0, keycode=0):
    return SimpleNamespace(keysym=keysym, char=char, state=state, keycode=keycode)


class GuiTestCase(unittest.TestCase):
    def setUp(self):
        try:
            self.root = tk.Tk()
        except tk.TclError:
            self.skipTest("no display available")
        self.addCleanup(self._close_window)
        home = tempfile.TemporaryDirectory()
        self.addCleanup(home.cleanup)
        self.home = home.name
        self.app = App(self.root, Settings())
        self.app.start([])
        self.root.update()

    def _close_window(self):
        self.root.update()  # run pending idle callbacks before the window goes away
        self.root.destroy()

    # ----- helpers --------------------------------------------------------------

    @property
    def view(self):
        return self.app.active_view

    @property
    def doc(self):
        return self.view.document

    def type_text(self, text):
        for char in text:
            if char == "\n":
                self.view._on_key(key_event("Return", "\r"))
            else:
                self.view._on_key(key_event(char if char != " " else "space", char))
        self.root.update()

    def press(self, keysym, char=""):
        self.view._on_key(key_event(keysym, char))
        self.root.update()

    def ctrl(self, key, shift=False):
        event = key_event(key, state=0x4 | (0x1 if shift else 0))
        self.app.handle_shortcut(event, in_text=True)
        self.root.update()

    def shown_text(self):
        return self.view.text.get("1.0", "end-1c")

    def assert_view_matches_model(self):
        """The widget must show exactly the model: same text and the same formatting everywhere."""
        view, doc = self.view, self.doc
        self.assertEqual(self.shown_text(), doc.text)
        all_tags = set(view._tag_of.values())
        for position in range(len(doc)):
            line, col = doc.line_col(position)
            tags = all_tags & set(view.text.tag_names(f"{line}.{col}"))
            fmt = doc.format_at(position)
            expected = set() if fmt == DEFAULT_FORMAT else {view._tag_of[fmt]}
            self.assertEqual(tags, expected, f"wrong formatting at offset {position}")


class TypingTests(GuiTestCase):
    def test_typing_is_mirrored_in_the_widget(self):
        self.type_text("Hello, world!\nSecond line")
        self.assertEqual(self.doc.text, "Hello, world!\nSecond line")
        self.assert_view_matches_model()

    def test_backspace_delete_and_undo(self):
        self.type_text("hello")
        self.press("BackSpace")
        self.press("BackSpace")
        self.assertEqual(self.shown_text(), "hel")
        self.ctrl("z")
        self.assertEqual(self.shown_text(), "hello")
        self.ctrl("y")
        self.assertEqual(self.shown_text(), "hel")

    def test_non_latin_text_can_be_typed(self):
        self.type_text("Բարև Привет")
        self.assertEqual(self.doc.text, "Բարև Привет")
        self.assert_view_matches_model()


class TypingFormatTests(GuiTestCase):
    def test_bold_chosen_for_a_selection_survives_typing(self):
        """The bug from the bug report: select text, press Bold, start typing."""
        self.type_text("hello world")
        self.view.select_range(0, 5)
        self.app.toggle_attribute("bold")
        self.type_text("X")  # replaces the selection
        self.type_text("Y")  # and keeps going
        self.assertEqual(self.doc.text, "XY world")
        self.assertTrue(self.doc.format_at(0).bold)
        self.assertTrue(self.doc.format_at(1).bold)
        self.assertFalse(self.doc.format_at(3).bold)
        self.assert_view_matches_model()

    def test_bold_without_selection_applies_to_following_text(self):
        self.ctrl("b")
        self.type_text("abc")
        self.ctrl("b")
        self.type_text("def")
        self.assertEqual([self.doc.format_at(i).bold for i in range(6)], [True] * 3 + [False] * 3)
        self.assert_view_matches_model()

    def test_toolbar_shows_the_typing_format(self):
        self.ctrl("b")
        self.ctrl("i")
        buttons = self.app.toolbar._buttons
        self.assertTrue(buttons["bold"]._active and buttons["italic"]._active)
        self.assertFalse(buttons["underline"]._active)

    def test_moving_the_cursor_takes_the_format_of_the_text(self):
        self.ctrl("b")
        self.type_text("ab")
        self.ctrl("b")
        self.type_text("cd")
        self.view.set_caret(1)
        self.root.update()
        self.assertTrue(self.app.active_view.editor.pending_format.bold)
        self.view.set_caret(4)
        self.root.update()
        self.assertFalse(self.app.active_view.editor.pending_format.bold)

    def test_font_size_and_family_for_a_selection_then_typing(self):
        self.type_text("abc")
        self.view.select_range(0, 3)
        self.app.set_font_size(24)
        self.type_text("Z")
        self.assertEqual(self.doc.format_at(0).size, 24)
        self.assert_view_matches_model()

    def test_size_box_edit_applies_to_selection(self):
        self.type_text("abc")
        self.view.select_range(0, 3)
        self.app.toolbar._size_box.set("30")
        self.app.toolbar._choose_size("30")
        self.assertEqual(self.doc.format_at(1).size, 30)
        self.assertEqual(self.view.selection(), (0, 3))  # the selection is still there

    def test_heading_then_enter_returns_to_normal_text(self):
        self.ctrl("1")
        self.type_text("Title")
        self.press("Return", "\r")
        self.type_text("body")
        self.assertEqual(self.doc.format_at(0).block, HEADING_1)
        self.assertEqual(self.doc.format_at(len(self.doc) - 1).block, PARAGRAPH)
        self.assertEqual(self.doc.format_at(0).display_size, 24)
        self.assert_view_matches_model()

    def test_alignment_of_an_empty_new_line_is_kept_for_typing(self):
        self.type_text("one\n")
        self.ctrl("e")
        self.type_text("two")
        self.assertEqual(self.doc.format_at(len(self.doc) - 1).align, "center")
        self.assertEqual(self.doc.format_at(0).align, "left")
        self.assert_view_matches_model()

    def test_clear_formatting_and_colors(self):
        self.type_text("abc")
        self.view.select_range(0, 3)
        self.app.set_text_color("#ff0000")
        self.app.set_highlight("#ffff00")
        self.assertEqual(self.doc.format_at(0).color, "#ff0000")
        self.ctrl("space")
        self.assertEqual(self.doc.format_at(0), DEFAULT_FORMAT)
        self.assert_view_matches_model()


class RealEventTests(GuiTestCase):
    """Real Tk events, to prove the key bindings are wired to the handlers."""

    def test_keyboard_events_reach_the_editor(self):
        text = self.view.text
        text.focus_force()
        self.root.update()
        for key in ("h", "i"):
            text.event_generate(f"<Key-{key}>")
        text.event_generate("<Control-b>")
        text.event_generate("<Key-x>")
        self.root.update()
        self.assertEqual(self.doc.text, "hix")
        self.assertTrue(self.doc.format_at(2).bold)
        self.assertFalse(self.doc.format_at(1).bold)
        text.event_generate("<Control-z>")
        self.root.update()
        self.assertEqual(self.doc.text, "hi")
        text.event_generate("<BackSpace>")
        self.root.update()
        self.assertEqual(self.doc.text, "h")
        self.assertEqual(self.shown_text(), "h")

    def test_emacs_style_bindings_do_not_edit_behind_the_editors_back(self):
        text = self.view.text
        text.focus_force()
        self.type_text("hello")
        self.view.set_caret(0)
        for sequence in ("<Control-d>", "<Control-k>", "<Control-p>", "<Control-t>"):  # emacs keys, no shortcut
            text.event_generate(sequence)
        self.root.update()
        self.assertEqual(self.doc.text, "hello")
        self.assertEqual(self.shown_text(), "hello")


class ColorPaletteTests(GuiTestCase):
    def test_palette_applies_a_color_to_the_selection(self):
        from pynotepad.ui.widgets import PALETTE, ColorPopup

        self.type_text("abc")
        self.view.select_range(0, 3)
        button = self.app.toolbar._text_color
        button._open_palette()
        popup = next(w for w in button.winfo_children() if isinstance(w, ColorPopup))
        colors = {w.cget("background") for w in popup.winfo_children()[0].winfo_children()[1].winfo_children()}
        self.assertTrue({color for row in PALETTE for color in row} <= colors)
        popup._choose("#188038")
        self.root.update()
        self.assertEqual(self.doc.format_at(1).color, "#188038")
        self.assertEqual(self.view.selection(), (0, 3))
        self.assertFalse(popup.winfo_exists())

    def test_automatic_resets_the_color(self):
        self.type_text("abc")
        self.view.select_range(0, 3)
        self.app.set_text_color("#ff0000")
        self.app.toolbar._text_color._picked("")
        self.assertEqual(self.doc.format_at(0).color, "")


class ShortcutTests(GuiTestCase):
    @unittest.skipUnless(sys.platform.startswith("linux"), "uses X11 keycodes")
    def test_shortcuts_work_on_a_non_latin_layout(self):
        self.type_text("hello")
        # Armenian layout: the physical Z key (X11 keycode 52) produces "զ", not "z"
        event = key_event("Armenian_za", "\x1a", state=0x4, keycode=52)
        self.assertEqual(self.app.handle_shortcut(event, in_text=True), "break")
        self.assertEqual(self.doc.text, "")

    def test_editing_shortcuts_are_ignored_outside_the_text(self):
        self.type_text("hello")
        self.app.handle_shortcut(key_event("z", state=0x4), in_text=False)
        self.assertEqual(self.doc.text, "hello")

    def test_ctrl_shift_tab_goes_to_the_previous_tab_on_every_platform(self):
        """X11 reports this key as ISO_Left_Tab, Windows as Tab+Shift; both must work."""
        first = self.app.workspace.active
        self.app.new_tab()
        for keysym in ("ISO_Left_Tab", "Tab"):
            self.app.workspace.activate(self.app.workspace.pages[1])
            self.app.handle_shortcut(key_event(keysym, state=0x4 | 0x1), in_text=True)
            self.assertIs(self.app.workspace.active, first, keysym)

    def test_zoom_shortcuts(self):
        self.ctrl("plus")
        self.assertAlmostEqual(self.view.zoom, 1.1)
        self.ctrl("0")
        self.assertEqual(self.view.zoom, 1.0)


class TabTests(GuiTestCase):
    def test_every_tab_keeps_its_own_text_and_history(self):
        self.type_text("first")
        first = self.app.workspace.active
        self.app.new_tab()
        self.root.update()
        self.type_text("second")
        self.press("space", " ")
        self.type_text("tab")
        second = self.app.workspace.active
        self.assertEqual(self.shown_text(), "second tab")

        self.app.workspace.activate(first)
        self.root.update()
        self.assertEqual(self.shown_text(), "first")
        self.assertEqual(len(self.app.history_panel._list.get(0, tk.END)), 2)  # original + 1 step
        self.app.workspace.activate(second)
        self.root.update()
        self.assertEqual(len(self.app.history_panel._list.get(0, tk.END)), 3)  # original + 2 steps

        self.ctrl("z")
        self.assertEqual(self.shown_text(), "second ")
        self.app.workspace.activate(first)
        self.root.update()
        self.assertEqual(self.shown_text(), "first")  # untouched by the undo in the other tab
        self.app.workspace.activate(second)
        self.root.update()
        self.ctrl("y")
        self.assertEqual(self.shown_text(), "second tab")  # redo still available after switching

    def test_history_panel_click_jumps_to_that_state(self):
        self.type_text("one ")
        self.type_text("two ")
        self.type_text("three")
        panel = self.app.history_panel
        panel._list.selection_clear(0, tk.END)
        panel._list.selection_set(1)
        panel._on_click(None)
        self.root.update()
        self.assertEqual(self.shown_text(), "one ")
        panel._list.selection_clear(0, tk.END)
        panel._list.selection_set(3)
        panel._on_click(None)
        self.assertEqual(self.shown_text(), "one two three")

    def test_tab_titles_and_modified_marker(self):
        page = self.app.workspace.active
        self.assertEqual(self.app.tab_bar._tabs[page]._dot.cget("text"), "")
        self.type_text("x")
        self.assertEqual(self.app.tab_bar._tabs[page]._dot.cget("text"), "●")
        self.assertTrue(self.root.title().startswith("●"))

    def test_closing_a_modified_tab_asks_and_can_be_cancelled(self):
        self.type_text("x")
        with mock.patch("pynotepad.ui.app.messagebox.askyesnocancel", return_value=None) as ask:
            self.assertFalse(self.app.close_tab())
        ask.assert_called_once()
        self.assertEqual(len(self.app.workspace.pages), 1)
        with mock.patch("pynotepad.ui.app.messagebox.askyesnocancel", return_value=False):
            self.assertTrue(self.app.close_tab())
        self.assertEqual(self.shown_text(), "")  # a fresh tab replaced it

    def test_switching_tabs_with_ctrl_tab(self):
        first = self.app.workspace.active
        self.app.new_tab()
        self.ctrl("tab")
        self.assertIs(self.app.workspace.active, first)
        self.ctrl("tab", shift=True)
        self.assertIsNot(self.app.workspace.active, first)


class FileTests(GuiTestCase):
    def test_save_and_reopen_keeps_formatting(self):
        self.ctrl("b")
        self.type_text("bold")
        self.ctrl("b")
        self.type_text(" plain")
        path = os.path.join(self.home, "note.pnote")
        self.assertTrue(self.app._write(self.app.workspace.active, path))
        self.app.new_tab()
        self.app._open_path(path)
        self.root.update()
        self.assertEqual(self.shown_text(), "bold plain")
        self.assertTrue(self.doc.format_at(0).bold)
        self.assertFalse(self.doc.format_at(5).bold)
        self.assert_view_matches_model()
        self.assertEqual(self.root.title(), "note.pnote — PyNotepad")

    def test_saving_formatted_text_as_txt_warns_once(self):
        self.ctrl("b")
        self.type_text("bold")
        page = self.app.workspace.active
        path = os.path.join(self.home, "plain.txt")
        with mock.patch("pynotepad.ui.app.messagebox.askyesno", return_value=False) as ask:
            self.assertFalse(self.app._write(page, path))
        ask.assert_called_once()
        self.assertFalse(os.path.exists(path))
        with mock.patch("pynotepad.ui.app.messagebox.askyesno", return_value=True):
            self.assertTrue(self.app._write(page, path))
        with open(path, encoding="utf-8") as file:
            self.assertEqual(file.read(), "bold")

    def test_opening_a_missing_file_shows_an_error(self):
        with mock.patch("pynotepad.ui.app.messagebox.showerror") as error:
            self.app._open_path(os.path.join(self.home, "nope.txt"))
        error.assert_called_once()

    def test_html_export(self):
        self.ctrl("1")
        self.type_text("Title")
        path = os.path.join(self.home, "page.html")
        self.app.workspace.export(self.app.workspace.active, path)
        with open(path, encoding="utf-8") as file:
            self.assertIn("<h1>", file.read())


class ClipboardTests(GuiTestCase):
    def test_copy_and_paste_keep_formatting(self):
        self.ctrl("b")
        self.type_text("bold")
        self.ctrl("b")
        self.type_text(" ")
        self.view.select_range(0, 4)
        self.ctrl("c")
        self.view.set_caret(len(self.doc))
        self.ctrl("v")
        self.assertEqual(self.doc.text, "bold bold")
        self.assertTrue(self.doc.format_at(6).bold)
        self.assert_view_matches_model()

    def test_cut(self):
        self.type_text("hello")
        self.view.select_range(1, 4)
        self.ctrl("x")
        self.assertEqual(self.shown_text(), "ho")
        self.ctrl("z")
        self.assertEqual(self.shown_text(), "hello")


class FindTests(GuiTestCase):
    def test_find_counts_highlights_and_replaces(self):
        self.type_text("cat dog Cat")
        bar = self.app.find_bar
        self.app.show_find(True)
        bar.find_var.set("cat")
        self.root.update()
        self.assertEqual(bar._count.cget("text")[-4:], "of 2")
        self.assertEqual(len(self.view.text.tag_ranges("find_match")), 4)  # two ranges = four indexes
        bar.find_next()
        self.assertEqual(self.view.selection(), (8, 11))
        bar.replace_var.set("bird")
        bar.replace_current()
        self.assertEqual(self.doc.text, "cat dog bird")
        bar.replace_all()
        self.assertEqual(self.doc.text, "bird dog bird")
        self.ctrl("z")
        self.assertEqual(self.doc.text, "cat dog bird")
        bar.close()
        self.assertFalse(self.view.text.tag_ranges("find_match"))

    def test_no_results_message(self):
        self.type_text("abc")
        self.app.show_find(False)
        self.app.find_bar.find_var.set("zzz")
        self.root.update()
        self.assertEqual(self.app.find_bar._count.cget("text"), "No results")


class ViewOptionTests(GuiTestCase):
    def test_dark_theme_recolors_the_text_area(self):
        light = self.view.text.cget("background")
        self.app.actions["toggle_theme"].run()
        self.assertNotEqual(self.view.text.cget("background"), light)
        self.app.actions["toggle_theme"].run()
        self.assertEqual(self.view.text.cget("background"), light)

    def test_status_bar_reports_position_and_counts(self):
        self.type_text("one two\nthree")
        self.root.update()
        labels = self.app.status_bar._cell_labels
        self.assertEqual(labels["position"].cget("text"), "Ln 2, Col 6")
        self.assertEqual(labels["words"].cget("text"), "3 words")
        self.assertEqual(labels["characters"].cget("text"), "13 characters")

    def test_toggling_panels_and_wrap(self):
        self.app.actions["toggle_history"].run()
        self.assertFalse(self.app.history_panel.winfo_ismapped())
        self.app.actions["toggle_wrap"].run()
        self.assertEqual(self.view.text.cget("wrap"), "none")

    def test_goto_line(self):
        self.type_text("a\nb\nc")
        with mock.patch("pynotepad.ui.app.simpledialog.askinteger", return_value=2):
            self.app.goto_line()
        self.assertEqual(self.view.caret(), 2)


class RendererConsistencyTests(GuiTestCase):
    def test_random_editing_never_desynchronizes_the_widget(self):
        """Hundreds of random edits, undos and redos; after each, widget == model."""
        rng = random.Random(7)
        alphabet = ["a", "b", "c", " ", "ж", "Ա", "\n"]
        for step in range(400):
            size = len(self.doc)
            position = rng.randint(0, size)
            roll = rng.random()
            if roll < 0.40:
                self.view.set_caret(position)
                char = rng.choice(alphabet)
                self.type_text(char)
            elif roll < 0.50 and size:
                self.view.set_caret(position)
                self.press("BackSpace")
            elif roll < 0.58 and size:
                end = min(size, position + rng.randint(1, 6))
                self.view.select_range(position, end)
                self.type_text(rng.choice(alphabet))
            elif roll < 0.72 and size:
                end = min(size, position + rng.randint(1, 8))
                self.view.select_range(position, end)
                self.app.toggle_attribute(rng.choice(["bold", "italic", "underline", "strike"]))
            elif roll < 0.77 and size:
                self.view.set_caret(position)
                self.app.set_block(rng.choice([HEADING_1, PARAGRAPH]))
            elif roll < 0.82:
                self.view.set_caret(position)
                self.app.set_alignment(rng.choice(["left", "center", "right"]))
            elif roll < 0.86 and size:
                end = min(size, position + rng.randint(1, 8))
                self.view.select_range(position, end)
                self.app.set_text_color(rng.choice(["#ff0000", "#00aa00", ""]))
            elif roll < 0.90:
                self.view.set_caret(position)
                self.app.toggle_bullets()
            elif roll < 0.96:
                self.ctrl("z")
            else:
                self.ctrl("y")
            self.assert_view_matches_model()


if __name__ == "__main__":
    unittest.main()
