"""Tests of the editing model (no GUI needed)"""
import unittest

from pynotepad.core.commands import InsertCommand
from pynotepad.core.document import DELETE, FORMAT, INSERT, Document, DocumentChange, Snapshot
from pynotepad.core.editor import BULLET, Editor
from pynotepad.core.formatting import (
    ALIGN_CENTER,
    DEFAULT_FORMAT,
    HEADING_1,
    PARAGRAPH,
)
from pynotepad.core.history import CommandHistory
from pynotepad.core.observer import CallbackObserver, Observer


class Recorder(Observer):
    def __init__(self):
        self.events = []

    def update(self, subject, event=None):
        self.events.append(event)


class EditorTestCase(unittest.TestCase):
    def setUp(self):
        self.editor = Editor()
        self.doc = self.editor.document

    def type_like_user(self, text):
        for char in text:
            self.editor.type_text(char, caret=len(self.doc))

    def all_have(self, attribute, value, start=0, end=None):
        end = len(self.doc) if end is None else end
        return all(getattr(self.doc.format_at(i), attribute) == value for i in range(start, end))


class TypingAndDeletingTests(EditorTestCase):
    def test_insert_undo_redo(self):
        self.editor.type_text("hello", caret=0)
        self.assertEqual(self.doc.text, "hello")
        self.editor.undo()
        self.assertEqual(self.doc.text, "")
        self.editor.redo()
        self.assertEqual(self.doc.text, "hello")

    def test_typing_is_grouped_by_words(self):
        self.type_like_user("hello world")
        self.assertEqual(len(self.editor.history.entries), 2)
        self.editor.undo()
        self.assertEqual(self.doc.text, "hello ")
        self.editor.undo()
        self.assertEqual(self.doc.text, "")

    def test_consecutive_backspaces_are_one_step(self):
        self.editor.type_text("hello", caret=0)
        for caret in (5, 4, 3):
            self.editor.backspace(caret)
        self.assertEqual(self.doc.text, "he")
        self.editor.undo()
        self.assertEqual(self.doc.text, "hello")

    def test_consecutive_delete_key_is_one_step(self):
        self.editor.type_text("hello", caret=0)
        self.editor.delete_forward(0)
        self.editor.delete_forward(0)
        self.assertEqual(self.doc.text, "llo")
        self.editor.undo()
        self.assertEqual(self.doc.text, "hello")

    def test_backspace_at_start_does_nothing(self):
        self.editor.backspace(0)
        self.assertFalse(self.editor.history.can_undo)

    def test_replacing_selection_is_one_undo_step(self):
        self.editor.type_text("hello", caret=0)
        self.editor.type_text("J", caret=5, selection=(0, 1))
        self.assertEqual(self.doc.text, "Jello")
        self.editor.undo()
        self.assertEqual(self.doc.text, "hello")
        self.editor.redo()
        self.assertEqual(self.doc.text, "Jello")

    def test_cut_returns_formatted_fragment_and_can_be_undone(self):
        self.editor.type_text("hello", caret=0)
        self.editor.toggle_attribute("bold", (1, 4))
        fragment = self.editor.cut((1, 4))
        self.assertEqual(fragment.text, "ell")
        self.assertTrue(all(fmt.bold for fmt in fragment.formats))
        self.assertEqual(self.doc.text, "ho")
        self.editor.undo()
        self.assertEqual(self.doc.text, "hello")

    def test_copy_does_not_change_the_document(self):
        self.editor.type_text("hello", caret=0)
        self.assertEqual(self.editor.copy((0, 2)).text, "he")
        self.assertIsNone(self.editor.copy(None))
        self.assertIsNone(self.editor.copy((2, 2)))
        self.assertEqual(len(self.editor.history.entries), 1)

    def test_paste_formatted_fragment_keeps_its_formats(self):
        self.editor.type_text("ab", caret=0)
        self.editor.toggle_attribute("bold", (0, 2))
        fragment = self.editor.copy((0, 2))
        self.editor.sync_pending(2)
        self.editor.toggle_attribute("bold")  # typing format is now plain again
        self.editor.paste(fragment, caret=2)
        self.assertEqual(self.doc.text, "abab")
        self.assertTrue(self.all_have("bold", True))
        self.editor.undo()
        self.assertEqual(self.doc.text, "ab")

    def test_paste_plain_text_uses_typing_format_and_is_not_merged(self):
        self.editor.toggle_attribute("italic")
        self.editor.paste("one", caret=0)
        self.editor.paste("two", caret=3)
        self.assertTrue(self.all_have("italic", True))
        self.assertEqual(len(self.editor.history.entries), 2)

    def test_paste_replaces_selection(self):
        self.editor.type_text("hello", caret=0)
        self.editor.paste("J", caret=5, selection=(0, 1))
        self.assertEqual(self.doc.text, "Jello")

    def test_delete_word(self):
        self.editor.type_text("one two  three", caret=0)
        self.editor.delete_word(caret=14, forward=False)
        self.assertEqual(self.doc.text, "one two  ")
        self.editor.delete_word(caret=0, forward=True)  # removes the word, keeps the space
        self.assertEqual(self.doc.text, " two  ")
        self.editor.undo()
        self.assertEqual(self.doc.text, "one two  ")
        self.editor.delete_word(caret=0)  # nothing to the left: no history step
        self.assertEqual(len(self.editor.history.entries), 3)

    def test_line_endings_and_astral_characters_are_normalized(self):
        self.editor.type_text("a\r\nb\rc\U0001F600", caret=0)
        self.assertEqual(self.doc.text, "a\nb\nc�")


class CharacterFormattingTests(EditorTestCase):
    def test_toggle_bold_and_undo(self):
        self.editor.type_text("hello", caret=0)
        self.editor.toggle_attribute("bold", selection=(0, 5))
        self.assertTrue(self.all_have("bold", True))
        self.editor.toggle_attribute("bold", selection=(0, 5))
        self.assertTrue(self.all_have("bold", False))
        self.editor.undo()
        self.assertTrue(self.all_have("bold", True))
        self.editor.undo()
        self.assertTrue(self.all_have("bold", False))
        self.assertEqual(self.doc.text, "hello")

    def test_partially_bold_selection_becomes_fully_bold(self):
        self.editor.type_text("hello", caret=0)
        self.editor.toggle_attribute("bold", selection=(0, 2))
        self.editor.toggle_attribute("bold", selection=(0, 5))
        self.assertTrue(self.all_have("bold", True))

    def test_undo_restores_mixed_formats(self):
        self.editor.type_text("abcd", caret=0)
        self.editor.toggle_attribute("bold", selection=(0, 2))
        self.editor.toggle_attribute("italic", selection=(1, 4))
        self.editor.undo()
        self.assertEqual([self.doc.format_at(i).bold for i in range(4)], [True, True, False, False])
        self.assertTrue(self.all_have("italic", False))

    def test_font_size_family_color_highlight(self):
        self.editor.type_text("hello", caret=0)
        self.editor.set_font_size(20, (0, 5))
        self.editor.set_font_family("Georgia", (0, 5))
        self.editor.set_text_color("#ff0000", (0, 5))
        self.editor.set_highlight("#ffff00", (0, 5))
        fmt = self.doc.format_at(2)
        self.assertEqual((fmt.size, fmt.family, fmt.color, fmt.highlight), (20, "Georgia", "#ff0000", "#ffff00"))
        self.editor.undo()
        self.assertEqual(self.doc.format_at(2).highlight, "")

    def test_font_size_is_clamped_and_changes_by_delta(self):
        self.editor.type_text("hello", caret=0)
        self.editor.set_font_size(1000, (0, 5))
        self.assertEqual(self.doc.format_at(0).size, 96)
        self.editor.set_font_size(12, (0, 5))
        self.editor.change_font_size(2, (0, 5))
        self.assertEqual(self.doc.format_at(0).size, 14)

    def test_clear_formatting(self):
        self.editor.type_text("hello", caret=0)
        self.editor.toggle_attribute("bold", (0, 5))
        self.editor.set_text_color("#ff0000", (0, 5))
        self.editor.clear_formatting((0, 5))
        self.assertEqual(self.doc.format_at(0), DEFAULT_FORMAT)

    def test_noop_format_does_not_create_history_step(self):
        self.editor.type_text("hello", caret=0)
        self.editor.set_font_size(12, (0, 5))  # already 12
        self.assertEqual(len(self.editor.history.entries), 1)

    def test_format_runs(self):
        self.editor.type_text("abcd", caret=0)
        self.editor.toggle_attribute("bold", selection=(1, 3))
        runs = [(a, b, f.bold) for a, b, f in self.doc.format_runs()]
        self.assertEqual(runs, [(0, 1, False), (1, 3, True), (3, 4, False)])


class TypingFormatTests(EditorTestCase):
    """The format chosen in the toolbar must stay active while typing."""

    def test_format_without_selection_applies_to_next_typed_text(self):
        self.editor.toggle_attribute("bold")
        self.editor.type_text("a", caret=0)
        self.assertTrue(self.doc.format_at(0).bold)
        self.assertEqual(len(self.editor.history.entries), 1)

    def test_format_chosen_for_selection_survives_typing(self):
        self.editor.type_text("hello", caret=0)
        self.editor.sync_pending(5)  # caret at the end, plain text
        self.editor.toggle_attribute("bold", selection=(0, 5))  # make the selection bold
        self.editor.type_text("X", caret=5, selection=(0, 5))  # typing replaces the selection
        self.assertEqual(self.doc.text, "X")
        self.assertTrue(self.doc.format_at(0).bold)

    def test_chosen_format_stays_for_following_characters(self):
        self.editor.type_text("hello", caret=0)
        self.editor.toggle_attribute("bold", selection=(1, 3))
        self.editor.type_text("ZZ", caret=3)  # continues the bold selection's format
        self.assertTrue(self.all_have("bold", True, 3, 5))

    def test_sync_takes_format_from_left_character(self):
        self.editor.type_text("ab", caret=0)
        self.editor.toggle_attribute("bold", selection=(0, 1))
        self.editor.sync_pending(1)
        self.assertTrue(self.editor.pending_format.bold)
        self.editor.sync_pending(2)
        self.assertFalse(self.editor.pending_format.bold)

    def test_sync_with_selection_uses_first_selected_character(self):
        self.editor.type_text("ab", caret=0)
        self.editor.toggle_attribute("italic", selection=(0, 1))
        self.editor.sync_pending(2, selection=(0, 2))
        self.assertTrue(self.editor.pending_format.italic)

    def test_heading_does_not_continue_on_next_line(self):
        self.editor.type_text("Title", caret=0)
        self.editor.set_block(HEADING_1, caret=5)
        self.editor.press_enter(caret=5)
        self.editor.sync_pending(len(self.doc))
        self.assertEqual(self.editor.pending_format.block, PARAGRAPH)
        self.editor.type_text("body", caret=len(self.doc))
        self.assertEqual(self.doc.format_at(len(self.doc) - 1).block, PARAGRAPH)
        self.assertEqual(self.doc.format_at(0).block, HEADING_1)

    def test_paragraph_format_keeps_the_chosen_typing_format(self):
        """Pressing Center must not forget that Bold was just switched on."""
        self.editor.type_text("hello", caret=0)
        view_sync = lambda *_: self.editor.sync_pending(5)  # what the window does after any change
        self.doc.attach(CallbackObserver(view_sync))
        self.editor.toggle_attribute("bold")
        self.editor.set_alignment(ALIGN_CENTER, caret=5)
        self.assertTrue(self.editor.pending_format.bold)
        self.assertEqual(self.editor.pending_format.align, ALIGN_CENTER)

    def test_undo_resyncs_the_typing_format_with_the_document(self):
        self.editor.type_text("hello", caret=0)
        self.doc.attach(CallbackObserver(lambda: self.editor.sync_pending(5, (0, 5))))
        self.editor.toggle_attribute("bold", selection=(0, 5))
        self.assertTrue(self.editor.pending_format.bold)
        self.editor.undo()
        self.assertFalse(self.editor.pending_format.bold)

    def test_observers_are_notified_when_typing_format_changes(self):
        calls = []
        self.editor.attach(CallbackObserver(lambda: calls.append(1)))
        self.editor.toggle_attribute("bold")
        self.editor.toggle_attribute("bold")
        self.assertEqual(len(calls), 2)
        self.editor.sync_pending(0)  # nothing changes -> no notification
        self.assertEqual(len(calls), 2)


class ParagraphFormattingTests(EditorTestCase):
    def test_heading_applies_to_whole_paragraph_only(self):
        self.editor.type_text("one\ntwo\nthree", caret=0)
        self.editor.set_block(HEADING_1, caret=5)  # inside "two"
        self.assertTrue(self.all_have("block", HEADING_1, 4, 8))
        self.assertTrue(self.all_have("block", PARAGRAPH, 0, 4))
        self.assertTrue(self.all_have("block", PARAGRAPH, 8, 13))

    def test_alignment_for_multi_paragraph_selection(self):
        self.editor.type_text("one\ntwo\nthree", caret=0)
        self.editor.set_alignment(ALIGN_CENTER, caret=0, selection=(2, 6))
        self.assertTrue(self.all_have("align", ALIGN_CENTER, 0, 8))
        self.assertTrue(self.all_have("align", "left", 8, 13))
        self.editor.undo()
        self.assertTrue(self.all_have("align", "left"))

    def test_selection_ending_at_line_start_excludes_next_paragraph(self):
        self.editor.type_text("one\ntwo", caret=0)
        self.editor.set_block(HEADING_1, caret=0, selection=(0, 4))
        self.assertTrue(self.all_have("block", HEADING_1, 0, 4))
        self.assertTrue(self.all_have("block", PARAGRAPH, 4, 7))

    def test_formatting_another_paragraph_does_not_change_the_typing_format(self):
        self.editor.type_text("one\ntwo", caret=0)
        self.editor.sync_pending(7)  # the cursor is at the end of "two"
        self.editor.set_block(HEADING_1, caret=7, selection=(0, 3))  # but only "one" is selected
        self.assertEqual(self.doc.format_at(0).block, HEADING_1)
        self.assertEqual(self.editor.pending_format.block, PARAGRAPH)
        self.editor.set_block(HEADING_1, caret=7)  # the cursor's own paragraph
        self.assertEqual(self.editor.pending_format.block, HEADING_1)

    def test_paragraph_format_on_empty_last_line_changes_only_typing_format(self):
        self.editor.type_text("one\n", caret=0)
        self.editor.set_alignment(ALIGN_CENTER, caret=4)
        self.assertEqual(self.editor.pending_format.align, ALIGN_CENTER)
        self.editor.type_text("two", caret=4)
        self.assertTrue(self.all_have("align", ALIGN_CENTER, 4, 7))
        self.assertTrue(self.all_have("align", "left", 0, 4))


class BulletTests(EditorTestCase):
    def test_toggle_bullets_on_several_paragraphs_and_undo(self):
        self.editor.type_text("one\ntwo", caret=0)
        self.editor.toggle_bullets(caret=0, selection=(0, 7))
        self.assertEqual(self.doc.text, f"{BULLET}one\n{BULLET}two")
        self.editor.toggle_bullets(caret=0, selection=(0, len(self.doc)))
        self.assertEqual(self.doc.text, "one\ntwo")
        self.editor.undo()
        self.assertEqual(self.doc.text, f"{BULLET}one\n{BULLET}two")
        self.editor.undo()
        self.assertEqual(self.doc.text, "one\ntwo")

    def test_enter_continues_and_ends_the_list(self):
        self.editor.toggle_bullets(caret=0)
        self.editor.type_text("item", caret=len(self.doc))
        self.editor.press_enter(caret=len(self.doc))
        self.assertEqual(self.doc.text, f"{BULLET}item\n{BULLET}")
        self.editor.press_enter(caret=len(self.doc))  # empty item ends the list
        self.assertEqual(self.doc.text, f"{BULLET}item\n")


class FindReplaceTests(EditorTestCase):
    def setUp(self):
        super().setUp()
        self.editor.type_text("Cat and cat and CAT", caret=0)

    def test_find_next_wraps_and_respects_case(self):
        self.assertEqual(self.editor.find("cat", 0), (0, 3))
        self.assertEqual(self.editor.find("cat", 1), (8, 11))
        self.assertEqual(self.editor.find("cat", 17), (0, 3))  # wraps around
        self.assertEqual(self.editor.find("cat", 0, match_case=True), (8, 11))
        self.assertIsNone(self.editor.find("dog", 0))

    def test_find_backwards(self):
        self.assertEqual(self.editor.find("cat", 19, backwards=True), (16, 19))
        self.assertEqual(self.editor.find("cat", 0, backwards=True), (16, 19))  # wraps around

    def test_replace_all_is_one_undo_step(self):
        count = self.editor.replace_all("cat", "dog")
        self.assertEqual(count, 3)
        self.assertEqual(self.doc.text, "dog and dog and dog")
        self.editor.undo()
        self.assertEqual(self.doc.text, "Cat and cat and CAT")
        self.editor.redo()
        self.assertEqual(self.doc.text, "dog and dog and dog")

    def test_replace_all_with_empty_text_deletes(self):
        self.editor.replace_all("cat", "", match_case=False)
        self.assertEqual(self.doc.text, " and  and ")

    def test_replace_keeps_format_of_first_character(self):
        self.editor.toggle_attribute("bold", selection=(0, 3))
        self.editor.replace_range(0, 3, "Dog")
        self.assertEqual(self.doc.text, "Dog and cat and CAT")
        self.assertTrue(self.all_have("bold", True, 0, 3))

    def test_is_match(self):
        self.assertTrue(self.editor.is_match(0, 3, "cat"))
        self.assertFalse(self.editor.is_match(0, 3, "cat", match_case=True))


class HistoryTests(EditorTestCase):
    def test_new_action_clears_redo(self):
        self.editor.type_text("ab", caret=0)
        self.editor.undo()
        self.assertTrue(self.editor.history.can_redo)
        self.editor.type_text("cd", caret=0)
        self.assertFalse(self.editor.history.can_redo)

    def test_undo_redo_on_empty_history_is_safe(self):
        self.editor.undo()
        self.editor.redo()
        self.assertEqual(self.doc.text, "")

    def test_history_limit(self):
        history = CommandHistory(limit=3)
        document = Document()
        for _ in range(5):
            history.execute(InsertCommand(document, 0, Snapshot.uniform("ab")))
        self.assertEqual(len(history.entries), 3)

    def test_go_to_any_state(self):
        for caret, text in ((0, "aa"), (2, "bb"), (4, "cc")):
            self.editor.type_text(text, caret=caret)
        history = self.editor.history
        history.go_to(1)
        self.assertEqual(self.doc.text, "aa")
        history.go_to(3)
        self.assertEqual(self.doc.text, "aabbcc")
        history.go_to(0)
        self.assertEqual(self.doc.text, "")

    def test_entries_mark_undone_steps(self):
        self.editor.type_text("aa", caret=0)
        self.editor.type_text("bb", caret=2)
        self.editor.undo()
        self.assertEqual([done for _, done in self.editor.history.entries], [True, False])

    def test_each_editor_has_its_own_history(self):
        other = Editor()
        self.editor.type_text("one", caret=0)
        other.type_text("two", caret=0)
        other.undo()
        self.assertEqual(self.doc.text, "one")
        self.assertTrue(self.editor.history.can_undo)


class DocumentTests(EditorTestCase):
    def test_observers_get_change_descriptions(self):
        recorder = Recorder()
        self.doc.attach(recorder)
        self.editor.type_text("hello", caret=0)
        self.editor.toggle_attribute("bold", selection=(0, 5))
        self.editor.undo()
        self.editor.undo()
        self.assertEqual(recorder.events, [
            DocumentChange(INSERT, 0, 5, caret=5),
            DocumentChange(FORMAT, 0, 5),
            DocumentChange(FORMAT, 0, 5),
            DocumentChange(DELETE, 0, 5, caret=0),
        ])

    def test_detached_observer_is_not_notified(self):
        recorder = Recorder()
        self.doc.attach(recorder)
        self.doc.detach(recorder)
        self.editor.type_text("a", caret=0)
        self.assertEqual(recorder.events, [])

    def test_invalid_range_raises(self):
        with self.assertRaises(IndexError):
            self.doc.delete(0, 5)

    def test_line_col_and_position_of_are_inverse(self):
        self.editor.type_text("ab\ncde\n\nf", caret=0)
        for position in range(len(self.doc) + 1):
            line, col = self.doc.line_col(position)
            self.assertEqual(self.doc.position_of(line, col), position)
        self.assertEqual(self.doc.line_col(4), (2, 1))
        self.assertEqual(self.doc.position_of(99, 0), len(self.doc))  # clamped
        self.assertEqual(self.doc.position_of(1, 99), 2)

    def test_paragraph_helpers(self):
        self.editor.type_text("ab\ncd\n", caret=0)
        self.assertEqual(self.doc.line_start(4), 3)
        self.assertEqual(self.doc.paragraph_range(4, 4), (3, 6))
        self.assertEqual(self.doc.paragraph_range(0, 4), (0, 6))
        self.assertEqual(self.doc.paragraph_starts(0, 6), [0, 3])
        self.assertEqual(self.doc.paragraph_starts(6, 6), [6])
        self.assertEqual(self.doc.word_count, 2)


if __name__ == "__main__":
    unittest.main()
