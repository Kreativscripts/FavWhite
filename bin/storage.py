from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

from models import MacroItem


DEFAULT_CONFIG: Dict[str, Any] = {
    "hotkey": "Ctrl+Q",
    "overlay": {"x": 40, "y": 40, "always_on_top": True, "opacity": 0.95},
    "tool_use": {"enabled": False, "interval_ms": 30},
    "items": [
        {"name": "Gumdrop",      "key": "2", "interval_ms": 3000, "jitter_min_ms": 0,   "jitter_max_ms": 0,   "enabled": True},
        {"name": "Jelly Beans",  "key": "3", "interval_ms": 9500, "jitter_min_ms": 0,   "jitter_max_ms": 0,   "enabled": True},
        {"name": "Snowflake",    "key": "7", "interval_ms": 9500, "jitter_min_ms": 200, "jitter_max_ms": 400, "enabled": True},
        {"name": "Stinger",      "key": "6", "interval_ms": 9500, "jitter_min_ms": 0,   "jitter_max_ms": 0,   "enabled": True},
    ],
}


def _resource_base_dir() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS).resolve()
    return Path(__file__).resolve().parent


def _exe_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def app_resource_path(rel: str) -> Path:
    return _resource_base_dir() / rel


def _appdata_cfg_path() -> Path:
    appdata = os.getenv("APPDATA")
    if appdata:
        return Path(appdata) / "FavWhite" / "favwhite.cfg"
    return Path.home() / ".favwhite" / "favwhite.cfg"


def cfg_path() -> Path:
    return _exe_dir() / "favwhite.cfg"


def _is_writable_dir(d: Path) -> bool:
    try:
        d.mkdir(parents=True, exist_ok=True)
        test = d / ".write_test"
        test.write_text("x", encoding="utf-8")
        test.unlink(missing_ok=True)
        return True
    except Exception:
        return False


def resolve_cfg_path() -> Path:
    primary = cfg_path()
    if _is_writable_dir(primary.parent):
        return primary

    fallback = _appdata_cfg_path()
    fallback.parent.mkdir(parents=True, exist_ok=True)
    return fallback


def _deep_merge(defaults: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(defaults)
    for k, v in (user or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def load_config() -> Dict[str, Any]:
    p = resolve_cfg_path()
    if p.exists():
        with p.open("r", encoding="utf-8") as f:
            cfg = json.load(f)
        merged = _deep_merge(DEFAULT_CONFIG, cfg)
        save_config(merged)
        return merged

    save_config(DEFAULT_CONFIG)
    return dict(DEFAULT_CONFIG)


def save_config(cfg: Dict[str, Any]) -> None:
    p = resolve_cfg_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)


def load_items(cfg: Dict[str, Any]) -> List[MacroItem]:
    items_raw = cfg.get("items", [])
    return [MacroItem.from_dict(x) for x in items_raw]


def write_items(cfg: Dict[str, Any], items: List[MacroItem]) -> Dict[str, Any]:
    cfg["items"] = [i.to_dict() for i in items]
    return cfg
