from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any, Dict


@dataclass
class MacroItem:
    name: str
    key: str
    interval_ms: int
    jitter_min_ms: int = 0
    jitter_max_ms: int = 0
    enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "MacroItem":
        return MacroItem(
            name=str(d.get("name", "Item")),
            key=str(d.get("key", "2")),
            interval_ms=int(d.get("interval_ms", 1000)),
            jitter_min_ms=int(d.get("jitter_min_ms", 0)),
            jitter_max_ms=int(d.get("jitter_max_ms", 0)),
            enabled=bool(d.get("enabled", True)),
        )
