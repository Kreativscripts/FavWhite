from __future__ import annotations

import time
from typing import Callable, Optional, Set

from pynput import keyboard


_MOD_ALIASES = {
    "ctrl": {keyboard.Key.ctrl, keyboard.Key.ctrl_l, keyboard.Key.ctrl_r},
    "alt": {keyboard.Key.alt, keyboard.Key.alt_l, keyboard.Key.alt_r, keyboard.Key.alt_gr},
    "shift": {keyboard.Key.shift, keyboard.Key.shift_l, keyboard.Key.shift_r},
    "win": {keyboard.Key.cmd, keyboard.Key.cmd_l, keyboard.Key.cmd_r},
    "meta": {keyboard.Key.cmd, keyboard.Key.cmd_l, keyboard.Key.cmd_r},
    "super": {keyboard.Key.cmd, keyboard.Key.cmd_l, keyboard.Key.cmd_r},
}

_SPECIAL_KEYS = {
    "space": keyboard.Key.space,
    "tab": keyboard.Key.tab,
    "enter": keyboard.Key.enter,
    "return": keyboard.Key.enter,
    "esc": keyboard.Key.esc,
    "escape": keyboard.Key.esc,
}


def _norm_piece(s: str) -> str:
    return (s or "").strip().lower()


def _parse_hotkey(seq: str) -> tuple[Set[keyboard.Key], Optional[str], Optional[keyboard.Key]]:
    """
    Returns: (required_mod_keys, required_char, required_special_key)
    required_char is for normal keys like 'q' or '7'
    required_special_key is for Key.space, Key.enter, etc
    """
    s = (seq or "").strip()
    if not s:
        s = "Ctrl+Q"

    parts = [_norm_piece(p) for p in s.split("+") if _norm_piece(p)]
    if not parts:
        parts = ["ctrl", "q"]

    required_mods: Set[keyboard.Key] = set()
    main = parts[-1]
    mods = parts[:-1]

    for m in mods:
        if m in ("control",):
            m = "ctrl"
        if m in ("windows",):
            m = "win"
        required_mods |= _MOD_ALIASES.get(m, set())

    if main in _SPECIAL_KEYS:
        return required_mods, None, _SPECIAL_KEYS[main]

    if len(main) == 1:
        return required_mods, main, None

    # F-keys like F8
    if main.startswith("f") and main[1:].isdigit():
        try:
            n = int(main[1:])
            return required_mods, None, getattr(keyboard.Key, f"f{n}")
        except Exception:
            pass

    # fallback: treat unknown as char first char
    return required_mods, main[:1], None


class GlobalHotkey:
    def __init__(self, callback: Callable[[], None], hotkey_sequence: str = "Ctrl+Q") -> None:
        self._callback = callback
        self._listener: Optional[keyboard.Listener] = None

        self._pressed: Set[object] = set()
        self._debounce_until = 0.0

        self._mods: Set[keyboard.Key] = set()
        self._main_char: Optional[str] = None
        self._main_special: Optional[keyboard.Key] = None

        self.set_hotkey(hotkey_sequence)

    def set_hotkey(self, hotkey_sequence: str) -> None:
        self._mods, self._main_char, self._main_special = _parse_hotkey(hotkey_sequence)

        if self._listener is not None:
            self.stop()
            self.start()

    def start(self) -> None:
        if self._listener is not None:
            return

        def on_press(key):
            try:
                self._pressed.add(key)
                self._maybe_fire()
            except Exception:
                # don't crash the listener thread
                pass

        def on_release(key):
            try:
                if key in self._pressed:
                    self._pressed.remove(key)
            except Exception:
                pass

        self._listener = keyboard.Listener(on_press=on_press, on_release=on_release)
        self._listener.start()

    def stop(self) -> None:
        try:
            if self._listener is not None:
                self._listener.stop()
        except Exception:
            pass
        self._listener = None
        self._pressed.clear()

    def _mods_satisfied(self) -> bool:
        if not self._mods:
            return True
        return any(m in self._pressed for m in self._mods)

    def _main_satisfied(self) -> bool:
        if self._main_special is not None:
            return self._main_special in self._pressed

        if self._main_char is not None:
            for k in self._pressed:
                if isinstance(k, keyboard.KeyCode) and k.char:
                    if k.char.lower() == self._main_char.lower():
                        return True
        return False

    def _maybe_fire(self) -> None:
        now = time.monotonic()
        if now < self._debounce_until:
            return

        if self._mods_satisfied() and self._main_satisfied():
            self._debounce_until = now + 0.35
            self._callback()
