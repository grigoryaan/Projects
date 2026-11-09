from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, fields


def settings_path() -> str:
    home = os.environ.get("PYNOTEPAD_HOME") or os.path.join(os.path.expanduser("~"), ".pynotepad")
    return os.path.join(home, "settings.json")


@dataclass
class Settings:
    theme: str = "light"
    zoom: float = 1.0
    wrap: bool = True
    show_history: bool = True
    show_status_bar: bool = True
    geometry: str = "1240x800"

    @classmethod
    def load(cls, path: str | None = None) -> Settings:
        settings = cls()
        try:
            with open(path or settings_path(), encoding="utf-8") as file:
                data = json.load(file)
        except (OSError, ValueError):
            return settings
        if isinstance(data, dict):
            for field in fields(cls):
                value = data.get(field.name)
                if type(value) is type(field.default):
                    setattr(settings, field.name, value)
        return settings

    def save(self, path: str | None = None) -> None:
        path = path or settings_path()
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as file:
                json.dump(asdict(self), file, indent=2)
        except OSError:
            pass
