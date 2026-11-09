from __future__ import annotations

import sys
import tkinter as tk

from pynotepad.settings import Settings
from pynotepad.ui.app import App


def enable_sharp_text_on_windows() -> None:
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except (AttributeError, OSError):
            pass


def main(argv: list[str] | None = None) -> None:
    enable_sharp_text_on_windows()
    root = tk.Tk()
    app = App(root, Settings.load())
    app.start(sys.argv[1:] if argv is None else argv)
    root.mainloop()


if __name__ == "__main__":
    main()
