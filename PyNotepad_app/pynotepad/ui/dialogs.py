"""Small informational windows."""
from __future__ import annotations

import tkinter as tk

from pynotepad import APP_NAME, __version__
from pynotepad.ui.actions import Action
from pynotepad.ui.theme import Fonts, ThemeManager, px


def _window(root: tk.Misc, themes: ThemeManager, title: str) -> tk.Toplevel:
    window = tk.Toplevel(root)
    window.title(title)
    window.configure(background=themes.theme.toolbar, padx=px(24), pady=px(18))
    window.transient(root.winfo_toplevel())
    window.resizable(False, False)
    window.bind("<Escape>", lambda event: window.destroy())
    return window


def show_shortcuts(root: tk.Misc, themes: ThemeManager, fonts: Fonts, actions: dict[str, Action]) -> None:
    theme = themes.theme
    window = _window(root, themes, "Keyboard shortcuts")
    tk.Label(window, text="Keyboard shortcuts", font=(fonts.ui, 14, "bold"), background=theme.toolbar,
             foreground=theme.text).grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, px(10)))
    groups: dict[str, list[Action]] = {}
    for action in actions.values():
        if action.key and action.group:
            groups.setdefault(action.group, []).append(action)
    columns = [list(groups.items())[0::2], list(groups.items())[1::2]]
    for column, items in enumerate(columns):
        row = 1
        for group, group_actions in items:
            tk.Label(window, text=group.upper(), font=(fonts.ui, 8, "bold"), background=theme.toolbar,
                     foreground=theme.accent).grid(row=row, column=column * 2, columnspan=2, sticky="w",
                                                   pady=(px(10), px(2)), padx=(px(0 if column == 0 else 28), 0))
            row += 1
            for action in group_actions:
                tk.Label(window, text=action.label, font=(fonts.ui, 10), background=theme.toolbar,
                         foreground=theme.text).grid(row=row, column=column * 2, sticky="w",
                                                     padx=(px(0 if column == 0 else 28), px(16)))
                tk.Label(window, text=action.accelerator, font=(fonts.ui, 10), background=theme.toolbar,
                         foreground=theme.muted).grid(row=row, column=column * 2 + 1, sticky="w")
                row += 1
    window.focus_set()


def show_about(root: tk.Misc, themes: ThemeManager, fonts: Fonts) -> None:
    theme = themes.theme
    window = _window(root, themes, f"About {APP_NAME}")
    tk.Label(window, text=APP_NAME, font=(fonts.ui, 20, "bold"), background=theme.toolbar,
             foreground=theme.accent).pack(anchor="w")
    tk.Label(window, text=f"Version {__version__}", font=(fonts.ui, 10), background=theme.toolbar,
             foreground=theme.muted).pack(anchor="w")
    body = (
        "A rich-text notepad with tabs, formatting and a full undo/redo history.\n\n"
        "Design patterns used:\n"
        "  Command, Memento, Composite - undo and redo\n"
        "  Observer - the window follows the model, themes\n"
        "  Facade - the Editor class\n"
        "  Strategy - file formats (.pnote, .txt, .html)\n"
    )
    tk.Label(window, text=body, justify="left", font=(fonts.ui, 10), background=theme.toolbar,
             foreground=theme.text).pack(anchor="w", pady=(px(12), 0))
    window.focus_set()
