from __future__ import annotations
import time
from typing import Dict, List

from PySide6.QtCore import Qt, QTimer, QPoint
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QFrame

from models import MacroItem
from scheduler import ItemState


class OverlayWindow(QWidget):
    def __init__(self, items: List[MacroItem], on_stop) -> None:
        super().__init__()
        self._items = items
        self._on_stop = on_stop
        self._drag_pos: QPoint | None = None

        self.setWindowTitle("FavWhite Overlay")
        self.setWindowFlags(
            Qt.Tool |
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        self._labels: Dict[str, QLabel] = {}

        root = QVBoxLayout()
        root.setContentsMargins(10, 10, 10, 10)

        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background: rgba(20, 20, 24, 220);
                border: 1px solid rgba(255,255,255,30);
                border-radius: 12px;
            }
            QLabel { color: #ffffff; font-size: 12px; }
            QPushButton {
                color: #ffffff;
                background: rgba(255,255,255,35);
                border: 1px solid rgba(255,255,255,45);
                padding: 6px 10px;
                border-radius: 10px;
            }
            QPushButton:hover { background: rgba(255,255,255,55); }
        """)

        v = QVBoxLayout(card)
        title = QLabel("FavWhite — Running")
        title.setStyleSheet("font-size: 13px; font-weight: 600;")
        v.addWidget(title)

        for it in items:
            lbl = QLabel(f"{it.name} [{it.key}] — next: ---, uses: 0")
            self._labels[it.name] = lbl
            v.addWidget(lbl)

        row = QHBoxLayout()
        stop_btn = QPushButton("Stop")
        stop_btn.clicked.connect(self._on_stop_clicked)
        row.addStretch(1)
        row.addWidget(stop_btn)
        v.addLayout(row)

        root.addWidget(card)
        self.setLayout(root)

        self._latest_state: Dict[str, ItemState] = {}
        self._timer = QTimer(self)
        self._timer.setInterval(100)
        self._timer.timeout.connect(self._render)
        self._timer.start()

    def set_state(self, states: Dict[str, ItemState]) -> None:
        self._latest_state = states

    def _render(self) -> None:
        now = time.monotonic()
        for it in self._items:
            st = self._latest_state.get(it.name)
            if st is None:
                continue
            remaining = max(0.0, st.next_fire_monotonic - now)
            self._labels[it.name].setText(
                f"{it.name} [{it.key}] — next: {remaining:0.1f}s, uses: {st.uses}"
            )

    def _on_stop_clicked(self) -> None:
        self._on_stop()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_pos is not None:
            delta = event.globalPosition().toPoint() - self._drag_pos
            self.move(self.pos() + delta)
            self._drag_pos = event.globalPosition().toPoint()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        super().mouseReleaseEvent(event)
