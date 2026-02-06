from __future__ import annotations
from typing import Callable
from pynput import keyboard


class GlobalHotkey:
    """
    Registers Ctrl+Q global hotkey.
    Runs the callback from pynput's thread, so callback MUST be thread-safe.
    """
    def __init__(self, callback: Callable[[], None]) -> None:
        self._callback = callback
        self._listener = keyboard.GlobalHotKeys({
            "<ctrl>+q": self._callback
        })

    def start(self) -> None:
        self._listener.start()

    def stop(self) -> None:
        try:
            self._listener.stop()
        except Exception:
            pass
