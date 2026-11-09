"""The application window: builds the interface and connects the parts.

Structure
    Workspace (model: tabs)  --events-->  App  -->  TabBar, PageView per tab,
                                                    Toolbar, HistoryPanel, FindBar, StatusBar
Every user command (menu, toolbar button, shortcut) is an Action; the methods below
are what those actions call. They translate a request such as "make it bold" into a
call to the Editor of the active tab, and never touch text or history themselves.
"""
from __future__ import annotations

import os
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

from pynotepad import APP_NAME
from pynotepad.core.file_formats import HTML, format_for_path
from pynotepad.core.formatting import (
    ALIGN_CENTER,
    ALIGN_LEFT,
    ALIGN_RIGHT,
    HEADING_1,
    HEADING_2,
    HEADING_3,
    PARAGRAPH,
)
from pynotepad.core.observer import EventObserver
from pynotepad.core.workspace import ACTIVATED, ADDED, REMOVED, UPDATED, Page, PageEvent, Workspace
from pynotepad.settings import Settings
from pynotepad.ui import dialogs
from pynotepad.ui.actions import MAC, Action
from pynotepad.ui.clipboard import Clipboard
from pynotepad.ui.find_bar import FindBar
from pynotepad.ui.history_panel import HistoryPanel
from pynotepad.ui.page_view import PageView, shortcut_key
from pynotepad.ui.status_bar import StatusBar
from pynotepad.ui.tab_bar import TabBar
from pynotepad.ui.theme import THEMES, LIGHT, Fonts, ThemeManager, available_families, init_scaling, observe_theme, px
from pynotepad.ui.toolbar import Toolbar
from pynotepad.ui.widgets import Tooltip  # noqa: F401  (re-exported for tests)

ZOOM_MIN, ZOOM_MAX, ZOOM_STEP = 0.5, 3.0, 0.1
OPEN_TYPES = [
    ("All supported", "*.pnote *.txt *.md *.log *.csv *.json *.py"),
    (f"{APP_NAME} document", "*.pnote"),
    ("Plain text", "*.txt"),
    ("All files", "*.*"),
]
SAVE_TYPES = [(f"{APP_NAME} document", "*.pnote"), ("Plain text", "*.txt")]


class App:
    def __init__(self, root: tk.Tk, settings: Settings | None = None) -> None:
        self.root = root
        self.settings = settings or Settings()
        init_scaling(root)
        self.fonts = Fonts.detect(root)
        self.families = available_families(root)
        self.themes = ThemeManager(THEMES.get(self.settings.theme, LIGHT))
        self.workspace = Workspace()
        self.clipboard = Clipboard(root)
        self.views: dict[Page, PageView] = {}
        self._visible_view: PageView | None = None
        self._lossy_confirmed: set[Page] = set()
        self._status_job: str | None = None

        self.zoom = min(ZOOM_MAX, max(ZOOM_MIN, self.settings.zoom))
        self.wrap_var = tk.BooleanVar(root, self.settings.wrap)
        self.history_var = tk.BooleanVar(root, self.settings.show_history)
        self.status_var = tk.BooleanVar(root, self.settings.show_status_bar)
        self.dark_var = tk.BooleanVar(root, self.themes.theme.name == "dark")

        self.actions: dict[str, Action] = {}
        self._build_actions()
        root.title(APP_NAME)
        root.geometry(self.settings.geometry)
        root.minsize(px(760), px(480))
        self._configure_ttk()
        self._build_layout()
        self._build_menus()
        self._bind_keys()
        observe_theme(root, self.themes, self._restyle)

        self.workspace.attach(EventObserver(self._on_workspace_event))
        root.protocol("WM_DELETE_WINDOW", self.quit)

    # ===== actions =============================================================

    def _build_actions(self) -> None:
        def add(action_id: str, label: str, run, key: str | None = None, shift: bool = False,
                ctrl: bool = True, text_only: bool = False, group: str = "") -> None:
            self.actions[action_id] = Action(label, run, key, shift, ctrl, text_only, group)

        file_, edit, fmt, view_, tabs = "File", "Edit", "Format", "View", "Tabs"
        add("new", "New tab", self.new_tab, "n", group=file_)
        add("open", "Open…", self.open_files, "o", group=file_)
        add("save", "Save", lambda: self.save(), "s", group=file_)
        add("save_as", "Save as…", lambda: self.save_as(), "s", shift=True, group=file_)
        add("export_html", "Export as HTML…", self.export_html)
        add("close_tab", "Close tab", lambda: self.close_tab(), "w", group=file_)
        add("quit", "Exit", self.quit, "q", group=file_)

        add("undo", "Undo", self.undo, "z", text_only=True, group=edit)
        add("redo", "Redo", self.redo, "y", text_only=True, group=edit)
        add("cut", "Cut", lambda: self._view_do(PageView.cut), "x", text_only=True, group=edit)
        add("copy", "Copy", lambda: self._view_do(PageView.copy), "c", text_only=True, group=edit)
        add("paste", "Paste", lambda: self._view_do(PageView.paste), "v", text_only=True, group=edit)
        add("select_all", "Select all", lambda: self._view_do(PageView.select_all), "a", text_only=True, group=edit)
        add("find", "Find…", lambda: self.show_find(False), "f", group=edit)
        add("replace", "Find and replace…", lambda: self.show_find(True), "h", group=edit)
        add("find_next", "Find next", lambda: self.find_bar.find_next(False), "f3", ctrl=False, group=edit)
        add("find_prev", "Find previous", lambda: self.find_bar.find_next(True), "f3", shift=True, ctrl=False,
            group=edit)
        add("goto_line", "Go to line…", self.goto_line, "g", group=edit)
        add("timestamp", "Insert date and time", self.insert_timestamp, "f5", ctrl=False, group=edit)

        add("bold", "Bold", lambda: self.toggle_attribute("bold"), "b", text_only=True, group=fmt)
        add("italic", "Italic", lambda: self.toggle_attribute("italic"), "i", text_only=True, group=fmt)
        add("underline", "Underline", lambda: self.toggle_attribute("underline"), "u", text_only=True, group=fmt)
        add("strike", "Strikethrough", lambda: self.toggle_attribute("strike"), "x", shift=True, text_only=True,
            group=fmt)
        add("normal", "Normal text", lambda: self.set_block(PARAGRAPH), "n", shift=True, text_only=True, group=fmt)
        add("h1", "Heading 1", lambda: self.set_block(HEADING_1), "1", text_only=True, group=fmt)
        add("h2", "Heading 2", lambda: self.set_block(HEADING_2), "2", text_only=True, group=fmt)
        add("h3", "Heading 3", lambda: self.set_block(HEADING_3), "3", text_only=True, group=fmt)
        add("align_left", "Align left", lambda: self.set_alignment(ALIGN_LEFT), "l", text_only=True, group=fmt)
        add("align_center", "Align center", lambda: self.set_alignment(ALIGN_CENTER), "e", text_only=True, group=fmt)
        add("align_right", "Align right", lambda: self.set_alignment(ALIGN_RIGHT), "r", text_only=True, group=fmt)
        add("bullets", "Bullet list", self.toggle_bullets, "l", shift=True, text_only=True, group=fmt)
        add("larger", "Increase font size", lambda: self.change_font_size(+1), "bracketright", text_only=True,
            group=fmt)
        add("smaller", "Decrease font size", lambda: self.change_font_size(-1), "bracketleft", text_only=True,
            group=fmt)
        add("clear_format", "Clear formatting", self.clear_formatting, "space", text_only=True, group=fmt)

        add("toggle_wrap", "Word wrap", lambda: self._flip(self.wrap_var, self.apply_wrap))
        add("toggle_history", "History panel", lambda: self._flip(self.history_var, self.apply_history_panel),
            "j", group=view_)
        add("toggle_status", "Status bar", lambda: self._flip(self.status_var, self.apply_status_bar))
        add("toggle_theme", "Dark theme", lambda: self._flip(self.dark_var, self.apply_theme), "d", shift=True,
            group=view_)
        add("zoom_in", "Zoom in", lambda: self.zoom_by(+1), "plus", group=view_)
        add("zoom_out", "Zoom out", lambda: self.zoom_by(-1), "minus", group=view_)
        add("zoom_reset", "Reset zoom", lambda: self.zoom_by(0), "0", group=view_)

        add("next_tab", "Next tab", lambda: self.switch_tab(+1), "tab", group=tabs)
        add("prev_tab", "Previous tab", lambda: self.switch_tab(-1), "tab", shift=True, group=tabs)
        add("shortcuts", "Keyboard shortcuts", lambda: dialogs.show_shortcuts(
            self.root, self.themes, self.fonts, self.actions), "f1", ctrl=False)
        add("about", f"About {APP_NAME}", lambda: dialogs.show_about(self.root, self.themes, self.fonts))

    # ===== interface construction ==============================================

    def _build_layout(self) -> None:
        root = self.root
        self.tab_bar = TabBar(root, self.themes, self.fonts, on_select=self.workspace.activate,
                              on_close=lambda page: self.close_tab(page), on_new=self.new_tab,
                              on_context=self._show_tab_menu)
        self.tab_bar.pack(fill=tk.X)
        self.toolbar = Toolbar(root, self.themes, self.fonts, self.families, self)
        self.toolbar.pack(fill=tk.X)
        self._rule = tk.Frame(root, height=1)
        self._rule.pack(fill=tk.X)

        self.status_bar = StatusBar(root, self.themes, self.fonts)
        self.status_bar.set_values(encoding="UTF-8")
        self.body = tk.Frame(root)
        self.body.pack(fill=tk.BOTH, expand=True)
        self.find_bar = FindBar(root, self.themes, self.fonts, lambda: self.active_view, self.status_bar.flash)
        self.find_bar.configure_packing(before=self.body)

        self._side_rule = tk.Frame(self.body, width=1)
        self.history_panel = HistoryPanel(self.body, self.themes, self.fonts)
        self.history_panel.bind("<<HistoryJump>>", lambda event: self._focus_after_history_jump())
        self.editor_area = tk.Frame(self.body)
        self.editor_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.apply_history_panel()
        self.apply_status_bar()

    def _configure_ttk(self) -> None:
        self.style = ttk.Style(self.root)
        self.style.theme_use("clam")

    def _restyle(self) -> None:
        theme = self.themes.theme
        root, style = self.root, self.style
        root.configure(background=theme.chrome)
        self._rule.configure(background=theme.border)
        self._side_rule.configure(background=theme.border)
        self.body.configure(background=theme.chrome)
        self.editor_area.configure(background=theme.page)

        style.configure("Tool.TCombobox", fieldbackground=theme.page, background=theme.toolbar,
                        foreground=theme.text, arrowcolor=theme.text, bordercolor=theme.border,
                        lightcolor=theme.page, darkcolor=theme.page, padding=px(3), relief="flat",
                        selectbackground=theme.page, selectforeground=theme.text)
        style.map("Tool.TCombobox",
                  fieldbackground=[("readonly", theme.page)], foreground=[("readonly", theme.text)],
                  selectbackground=[("readonly", theme.page)], selectforeground=[("readonly", theme.text)],
                  bordercolor=[("focus", theme.accent)], arrowcolor=[("disabled", theme.muted)])
        for orient in ("Vertical", "Horizontal"):
            name = f"Page.{orient}.TScrollbar"
            style.layout(name, [(f"{orient}.Scrollbar.trough", {"sticky": "nswe", "children": [
                (f"{orient}.Scrollbar.thumb", {"expand": "1", "sticky": "nswe"})]})])
            style.configure(name, troughcolor=theme.page, background=theme.border, bordercolor=theme.page,
                            lightcolor=theme.border, darkcolor=theme.border, gripcount=0, width=px(11))
            style.map(name, background=[("active", theme.muted), ("pressed", theme.muted)],
                      lightcolor=[("active", theme.muted)], darkcolor=[("active", theme.muted)])
        for box in self.toolbar.comboboxes:  # the drop-down lists are plain Tk listboxes
            try:
                popdown = box.tk.call("ttk::combobox::PopdownWindow", str(box))
                box.tk.call(f"{popdown}.f.l", "configure", "-background", theme.toolbar, "-foreground", theme.text,
                            "-selectbackground", theme.selection, "-selectforeground", theme.text,
                            "-borderwidth", 0, "-highlightthickness", 0)
            except tk.TclError:
                pass
        self.dark_var.set(theme.name == "dark")
        for menu in self._menus:  # honored on Linux; Windows and macOS keep their native menus
            menu.configure(background=theme.toolbar, foreground=theme.text, activebackground=theme.selection,
                           activeforeground=theme.text, disabledforeground=theme.muted, borderwidth=0)

    def _build_menus(self) -> None:
        root = self.root
        menubar = tk.Menu(root)
        self._menus: list[tk.Menu] = [menubar]
        self._menu_actions: dict[str, tuple[tk.Menu, int]] = {}

        def command(menu: tk.Menu, action_id: str) -> None:
            action = self.actions[action_id]
            menu.add_command(label=action.label, accelerator=action.accelerator, command=action.run)
            self._menu_actions[action_id] = (menu, menu.index("end"))

        def toggle(menu: tk.Menu, action_id: str, variable: tk.BooleanVar, apply) -> None:
            action = self.actions[action_id]
            menu.add_checkbutton(label=action.label, accelerator=action.accelerator, variable=variable,
                                 command=apply)

        def fill(menu: tk.Menu, *items: str | None) -> None:
            for item in items:
                if item is None:
                    menu.add_separator()
                else:
                    command(menu, item)

        file_menu = tk.Menu(menubar, tearoff=False)
        fill(file_menu, "new", "open", None, "save", "save_as", "export_html", None, "close_tab", "quit")
        edit_menu = tk.Menu(menubar, tearoff=False, postcommand=self._refresh_edit_menu)
        fill(edit_menu, "undo", "redo", None, "cut", "copy", "paste", "select_all", None, "find", "replace",
             "find_next", "find_prev", "goto_line", None, "timestamp")
        format_menu = tk.Menu(menubar, tearoff=False)
        fill(format_menu, "bold", "italic", "underline", "strike", None, "normal", "h1", "h2", "h3", None,
             "align_left", "align_center", "align_right", "bullets", None, "larger", "smaller", "clear_format")
        view_menu = tk.Menu(menubar, tearoff=False)
        toggle(view_menu, "toggle_wrap", self.wrap_var, self.apply_wrap)
        toggle(view_menu, "toggle_history", self.history_var, self.apply_history_panel)
        toggle(view_menu, "toggle_status", self.status_var, self.apply_status_bar)
        toggle(view_menu, "toggle_theme", self.dark_var, self.apply_theme)
        view_menu.add_separator()
        fill(view_menu, "zoom_in", "zoom_out", "zoom_reset", None, "next_tab", "prev_tab")
        help_menu = tk.Menu(menubar, tearoff=False)
        fill(help_menu, "shortcuts", "about")

        for label, menu in (("File", file_menu), ("Edit", edit_menu), ("Format", format_menu),
                            ("View", view_menu), ("Help", help_menu)):
            menubar.add_cascade(label=label, menu=menu)
        root.configure(menu=menubar)

        self.context_menu = tk.Menu(root, tearoff=False)
        fill(self.context_menu, "cut", "copy", "paste", "select_all", None, "bold", "italic", "underline")
        self.tab_menu = tk.Menu(root, tearoff=False)
        self._menus += [file_menu, edit_menu, format_menu, view_menu, help_menu, self.context_menu, self.tab_menu]

    def _refresh_edit_menu(self) -> None:
        """Undo and Redo entries name the step they would revert."""
        view = self.active_view
        history = view.editor.history if view else None
        for action_id, description, can in (
                ("undo", history.undo_description if history else None, bool(history and history.can_undo)),
                ("redo", history.redo_description if history else None, bool(history and history.can_redo))):
            menu, index = self._menu_actions[action_id]
            label = self.actions[action_id].label
            menu.entryconfigure(index, label=f"{label}  “{description}”" if description else label,
                                state=tk.NORMAL if can else tk.DISABLED)

    # ===== keyboard ============================================================

    def _bind_keys(self) -> None:
        modifier = "Command" if MAC else "Control"
        self._shortcuts: dict[tuple[str, bool], Action] = {}
        for action in self.actions.values():
            if not action.key:
                continue
            if action.ctrl:
                self._shortcuts[(action.key, action.shift)] = action
            else:
                sequence = f"<{'Shift-' if action.shift else ''}{action.key.upper()}>"
                self.root.bind(sequence, lambda event, a=action: (a.run(), "break")[1])
        self._shortcuts[("z", True)] = self.actions["redo"]  # Ctrl+Shift+Z is the other common Redo
        self.root.bind(f"<{modifier}-Key>", lambda event: self.handle_shortcut(event, in_text=False))

    def handle_shortcut(self, event: tk.Event, in_text: bool = True) -> str | None:
        """Runs the action bound to a Ctrl+key press. Returns "break" if it was handled."""
        key = shortcut_key(event)
        shift = bool(event.state & 0x1)
        if key == "iso_left_tab":
            key, shift = "tab", True
        elif key in ("plus", "equal"):
            key, shift = "plus", False  # Ctrl+= and Ctrl+Shift+= both zoom in
        action = self._shortcuts.get((key, shift))
        if action is None or (action.text_only and not in_text):
            return None
        action.run()
        return "break"

    # ===== model events ========================================================

    @property
    def active_view(self) -> PageView | None:
        return self.views.get(self.workspace.active) if self.workspace.active else None

    def start(self, paths: list[str] | None = None) -> None:
        """Opens the given files, or an empty tab if there are none."""
        for path in paths or []:
            self._open_path(path)
        if not self.workspace.pages:
            self.workspace.new_page()
        self._restyle()
        self.root.after_idle(self.focus_editor)

    def _on_workspace_event(self, event: PageEvent) -> None:
        page = event.page
        if event.kind == ADDED:
            view = PageView(self.editor_area, page, self.themes, self.fonts, self.clipboard,
                            self._text_shortcut, zoom=self.zoom, wrap=self.wrap_var.get())
            view.on_status_change = self._schedule_status_update
            view.on_zoom_request = self.zoom_by
            view.text.bind("<Button-2>" if MAC else "<Button-3>", self._show_context_menu)
            self.views[page] = view
            self.tab_bar.add(page)
        elif event.kind == REMOVED:
            view = self.views.pop(page)
            if self._visible_view is view:
                self._visible_view = None
            view.destroy()
            self.tab_bar.remove(page)
            self._lossy_confirmed.discard(page)
        elif event.kind == ACTIVATED:
            self._show(page)
        elif event.kind == UPDATED:
            self.tab_bar.refresh(page)
            if page is self.workspace.active:
                self._update_title()
                self.history_panel.set_title(page.title)

    def _text_shortcut(self, event: tk.Event) -> str | None:
        return self.handle_shortcut(event, in_text=True)

    def _show(self, page: Page) -> None:
        if self._visible_view is not None:
            self._visible_view.frame.pack_forget()
        view = self.views[page]
        view.frame.pack(fill=tk.BOTH, expand=True)
        self._visible_view = view
        self.tab_bar.select(page)
        self.toolbar.bind_editor(page.editor)
        self.history_panel.show(page.editor.history, page.title)
        self.find_bar.on_page_changed()
        self._update_title()
        self._update_status()
        view.focus()

    def _update_title(self) -> None:
        page = self.workspace.active
        if page is not None:
            self.root.title(f"{'● ' if page.modified else ''}{page.title} — {APP_NAME}")

    def _schedule_status_update(self) -> None:
        if self._status_job is None:
            self._status_job = self.root.after_idle(self._update_status)

    def _update_status(self) -> None:
        self._status_job = None
        view = self.active_view
        if view is None:
            return
        doc = view.document
        line, column = doc.line_col(view.caret())
        selection = view.selection()
        selected = selection[1] - selection[0] if selection else 0
        self.status_bar.set_values(
            position=f"Ln {line}, Col {column + 1}",
            selection=f"{selected} selected" if selected else "",
            words=f"{doc.word_count} words",
            characters=f"{len(doc)} characters",
            zoom=f"{round(view.zoom * 100)}%",
        )

    # ===== handlers used by the toolbar =======================================

    def focus_editor(self) -> None:
        view = self.active_view
        if view is not None:
            view.focus()

    def _view_do(self, method) -> None:
        view = self.active_view
        if view is not None:
            method(view)

    def undo(self) -> None:
        view = self.active_view
        if view is not None:
            view.editor.undo()
            view.focus()

    def redo(self) -> None:
        view = self.active_view
        if view is not None:
            view.editor.redo()
            view.focus()

    def toggle_attribute(self, name: str) -> None:
        view = self.active_view
        if view is not None:
            view.editor.toggle_attribute(name, view.selection())
            view.focus()

    def set_font_family(self, family: str) -> None:
        view = self.active_view
        if view is not None:
            view.editor.set_font_family(family, view.selection())

    def set_font_size(self, size: int) -> None:
        view = self.active_view
        if view is not None:
            view.editor.set_font_size(size, view.selection())

    def change_font_size(self, delta: int) -> None:
        view = self.active_view
        if view is not None:
            view.editor.change_font_size(delta, view.selection())
            view.focus()

    def set_text_color(self, color: str) -> None:
        view = self.active_view
        if view is not None:
            view.editor.set_text_color(color, view.selection())
            view.focus()

    def set_highlight(self, color: str) -> None:
        view = self.active_view
        if view is not None:
            view.editor.set_highlight(color, view.selection())
            view.focus()

    def set_block(self, block: str) -> None:
        view = self.active_view
        if view is not None:
            view.editor.set_block(block, view.caret(), view.selection())
            view.focus()

    def set_alignment(self, align: str) -> None:
        view = self.active_view
        if view is not None:
            view.editor.set_alignment(align, view.caret(), view.selection())
            view.focus()

    def toggle_bullets(self) -> None:
        view = self.active_view
        if view is not None:
            view.editor.toggle_bullets(view.caret(), view.selection())
            view.focus()

    def clear_formatting(self) -> None:
        view = self.active_view
        if view is not None:
            view.editor.clear_formatting(view.selection())
            view.focus()

    def insert_timestamp(self) -> None:
        view = self.active_view
        if view is not None:
            view.editor.insert_timestamp(view.caret(), view.selection())
            view.focus()

    def goto_line(self) -> None:
        view = self.active_view
        if view is None:
            return
        last_line = view.document.line_col(len(view.document))[0]
        number = simpledialog.askinteger("Go to line", f"Line number (1 – {last_line}):", parent=self.root,
                                         minvalue=1, maxvalue=last_line)
        if number:
            view.set_caret(view.document.position_of(number, 0))
            view.focus()

    def show_find(self, replace: bool) -> None:
        self.find_bar.open(replace)

    # ===== view options ========================================================

    @staticmethod
    def _flip(variable: tk.BooleanVar, apply) -> None:
        variable.set(not variable.get())
        apply()

    def apply_wrap(self) -> None:
        for view in self.views.values():
            view.set_wrap(self.wrap_var.get())

    def apply_history_panel(self) -> None:
        if self.history_var.get():
            self._side_rule.pack(side=tk.RIGHT, fill=tk.Y)
            self.history_panel.pack(side=tk.RIGHT, fill=tk.Y, before=self._side_rule)
        else:
            self.history_panel.pack_forget()
            self._side_rule.pack_forget()

    def apply_status_bar(self) -> None:
        if self.status_var.get():
            self.status_bar.pack(side=tk.BOTTOM, fill=tk.X, before=self.body)
        else:
            self.status_bar.pack_forget()

    def apply_theme(self) -> None:
        self.themes.set(THEMES["dark" if self.dark_var.get() else "light"])

    def zoom_by(self, step: int) -> None:
        """step +1 / -1 zooms by 10%, 0 resets to 100%."""
        self.zoom = 1.0 if step == 0 else round(min(ZOOM_MAX, max(ZOOM_MIN, self.zoom + step * ZOOM_STEP)), 2)
        for view in self.views.values():
            view.set_zoom(self.zoom)
        self._update_status()

    def switch_tab(self, step: int) -> None:
        pages = self.workspace.pages
        if len(pages) > 1 and self.workspace.active in pages:
            index = pages.index(self.workspace.active)
            self.workspace.activate(pages[(index + step) % len(pages)])

    def _focus_after_history_jump(self) -> None:
        self.focus_editor()

    # ===== context menus =======================================================

    def _show_context_menu(self, event: tk.Event) -> str:
        view = self.active_view
        if view is not None:
            # A right click outside the selection moves the cursor there, like most editors.
            view.focus()
            selection = view.selection()
            point = view.text.index(f"@{event.x},{event.y}")
            offset = view._offset(str(point))
            if not selection or not selection[0] <= offset <= selection[1]:
                view.set_caret(offset)
        self.context_menu.tk_popup(event.x_root, event.y_root)
        return "break"

    def _show_tab_menu(self, page: Page, event: tk.Event) -> None:
        menu = self.tab_menu
        menu.delete(0, tk.END)
        menu.add_command(label="Save", command=lambda: self.save(page))
        menu.add_command(label="Close", command=lambda: self.close_tab(page))
        others = [other for other in self.workspace.pages if other is not page]
        menu.add_command(label="Close other tabs", state=tk.NORMAL if others else tk.DISABLED,
                         command=lambda: [self.close_tab(other) or None for other in others])
        menu.tk_popup(event.x_root, event.y_root)

    # ===== files and tabs ======================================================

    def new_tab(self) -> None:
        self.workspace.new_page()

    def open_files(self) -> None:
        paths = filedialog.askopenfilenames(parent=self.root, title="Open", filetypes=OPEN_TYPES)
        for path in paths:
            self._open_path(path)

    def _open_path(self, path: str) -> None:
        try:
            self.workspace.open_file(path)
        except (OSError, ValueError) as error:
            messagebox.showerror("Cannot open file", f"{os.path.basename(path)}\n\n{error}", parent=self.root)

    def save(self, page: Page | None = None) -> bool:
        page = page or self.workspace.active
        if page is None:
            return False
        if page.path is None:
            return self.save_as(page)
        return self._write(page, page.path)

    def save_as(self, page: Page | None = None) -> bool:
        page = page or self.workspace.active
        if page is None:
            return False
        path = filedialog.asksaveasfilename(
            parent=self.root, title="Save as", defaultextension=".pnote", filetypes=SAVE_TYPES,
            initialfile=os.path.splitext(page.title)[0])
        return bool(path) and self._write(page, path)

    def _write(self, page: Page, path: str) -> bool:
        file_format = format_for_path(path)
        if file_format.lossy and page.editor.document.has_formatting() and page not in self._lossy_confirmed:
            keep_going = messagebox.askyesno(
                "Formatting will be lost",
                "Plain text files cannot store formatting (bold, headings, colors ...).\n\n"
                f"Save as {os.path.basename(path)} anyway?\n\nUse the .pnote format to keep the formatting.",
                parent=self.root)
            if not keep_going:
                return False
            self._lossy_confirmed.add(page)
        try:
            self.workspace.save(page, path)
        except OSError as error:
            messagebox.showerror("Cannot save file", f"{os.path.basename(path)}\n\n{error}", parent=self.root)
            return False
        self.status_bar.flash(f"Saved {page.title}")
        return True

    def export_html(self) -> None:
        page = self.workspace.active
        if page is None:
            return
        path = filedialog.asksaveasfilename(
            parent=self.root, title="Export as HTML", defaultextension=".html",
            filetypes=[("HTML page", "*.html")], initialfile=os.path.splitext(page.title)[0])
        if not path:
            return
        try:
            self.workspace.export(page, path, HTML)
        except OSError as error:
            messagebox.showerror("Cannot export", str(error), parent=self.root)
            return
        self.status_bar.flash(f"Exported {os.path.basename(path)}")

    def _confirm_discard(self, page: Page) -> bool:
        """Asks what to do with unsaved changes. False means: cancel what you were doing."""
        if not page.modified:
            return True
        self.workspace.activate(page)
        answer = messagebox.askyesnocancel("Unsaved changes", f"Save changes to “{page.title}”?",
                                           parent=self.root, icon="warning")
        if answer is None:
            return False
        return self.save(page) if answer else True

    def close_tab(self, page: Page | None = None) -> bool:
        page = page or self.workspace.active
        if page is None or not self._confirm_discard(page):
            return False
        self.workspace.close_page(page)
        return True

    def quit(self) -> None:
        for page in self.workspace.pages:
            if not self._confirm_discard(page):
                return
        self.settings.theme = self.themes.theme.name
        self.settings.zoom = self.zoom
        self.settings.wrap = self.wrap_var.get()
        self.settings.show_history = self.history_var.get()
        self.settings.show_status_bar = self.status_var.get()
        self.settings.geometry = f"{self.root.winfo_width()}x{self.root.winfo_height()}"
        self.settings.save()
        self.root.destroy()
