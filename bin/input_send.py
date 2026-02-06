from __future__ import annotations
from pynput.keyboard import Controller, Key

_keyboard = Controller()

_SPECIAL = {
    "enter": Key.enter,
    "esc": Key.esc,
    "escape": Key.esc,
    "tab": Key.tab,
    "space": Key.space,
    "shift": Key.shift,
    "ctrl": Key.ctrl,
    "control": Key.ctrl,
    "alt": Key.alt,
    "backspace": Key.backspace,
    "delete": Key.delete,
    "up": Key.up,
    "down": Key.down,
    "left": Key.left,
    "right": Key.right,
    "home": Key.home,
    "end": Key.end,
    "pageup": Key.page_up,
    "pagedown": Key.page_down,
}


def _normalize_key(s: str) -> str:
    return s.strip().lower()


def press_key(key_str: str) -> None:
    """Sends a key press to the OS."""
    k = _normalize_key(key_str)
    special = _SPECIAL.get(k)
    if special is not None:
        _keyboard.press(special)
        _keyboard.release(special)
        return

    if len(k) == 1:
        _keyboard.press(k)
        _keyboard.release(k)
        return
