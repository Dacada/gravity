import json
import os
from pathlib import Path
from typing import Optional

from gravity.config.schema import AppConfig


def load_config(path: Optional[Path] = None) -> AppConfig:
    config_path = _resolve_config_path(path)

    try:
        data = json.loads(config_path.read_text())
    except FileNotFoundError:
        raise RuntimeError(f"Config file not found: {config_path}")

    return AppConfig.model_validate(data)


def _resolve_config_path(explicit: Optional[Path]) -> Path:
    if explicit is not None:
        return explicit

    xdg = os.environ.get("XDG_CONFIG_HOME")
    if xdg:
        candidate = Path(xdg) / "gravity" / "config.json"
        if candidate.exists():
            return candidate

    candidate = Path.home() / ".config" / "gravity" / "config.json"
    if candidate.exists():
        return candidate

    raise RuntimeError("No configuration file found")
