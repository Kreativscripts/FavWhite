from __future__ import annotations
import random
import time
import threading
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

from models import MacroItem


@dataclass
class ItemState:
    uses: int = 0
    next_fire_monotonic: float = 0.0
    last_fire_monotonic: float = 0.0


class MacroScheduler:
    """Runs MacroItem timers in a background thread."""

    def __init__(
        self,
        items: List[MacroItem],
        send_fn: Callable[[str], None],
        on_tick: Optional[Callable[[Dict[str, ItemState]], None]] = None,
    ) -> None:
        self._items = items
        self._send_fn = send_fn
        self._on_tick = on_tick

        self._lock = threading.Lock()
        self._states: Dict[str, ItemState] = {i.name: ItemState() for i in items}

        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        self._stop.clear()
        now = time.monotonic()
        with self._lock:
            for it in self._items:
                st = self._states[it.name]
                st.uses = 0
                st.last_fire_monotonic = 0.0
                st.next_fire_monotonic = now + (it.interval_ms / 1000.0)

        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)

    def snapshot(self) -> Dict[str, ItemState]:
        with self._lock:
            return {k: ItemState(v.uses, v.next_fire_monotonic, v.last_fire_monotonic) for k, v in self._states.items()}

    def _run_loop(self) -> None:
        tick_sleep = 0.10
        while not self._stop.is_set():
            now = time.monotonic()

            with self._lock:
                for it in self._items:
                    if not it.enabled:
                        continue

                    st = self._states[it.name]
                    if now >= st.next_fire_monotonic:
                        self._send_fn(it.key)
                        st.uses += 1
                        st.last_fire_monotonic = now

                        jitter = 0.0
                        if it.jitter_max_ms > 0 and it.jitter_max_ms >= it.jitter_min_ms:
                            jitter_ms = random.randint(it.jitter_min_ms, it.jitter_max_ms)
                            jitter = jitter_ms / 1000.0

                        st.next_fire_monotonic = now + (it.interval_ms / 1000.0) + jitter

            if self._on_tick is not None:
                self._on_tick(self.snapshot())

            time.sleep(tick_sleep)
