from __future__ import annotations
import sys
from typing import List

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTableWidget, QTableWidgetItem, QMessageBox, QLabel, QCheckBox
)

from models import MacroItem
from storage import load_config, save_config, load_items, write_items
from input_send import press_key
from scheduler import MacroScheduler
from overlay import OverlayWindow
from hotkey import GlobalHotkey


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle("FavWhite")
        self.resize(820, 420)

        # runtime state
        self._scheduler: MacroScheduler | None = None
        self._overlay: OverlayWindow | None = None
        self._running: bool = False

        # load config
        self._cfg = load_config()
        self._items: List[MacroItem] = load_items(self._cfg)

        # global hotkey (Ctrl+Q)
        self._hotkey = GlobalHotkey(self._toggle_hotkey)
        self._hotkey.start()

        # ---------------- UI ----------------
        root = QWidget()
        layout = QVBoxLayout(root)

        header = QLabel("FavWhite Macro UI — Hotkey: Ctrl + Q (Start/Stop)")
        layout.addWidget(header)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels([
            "Enabled",
            "Name",
            "Key",
            "Interval (ms)",
            "Jitter min (ms)",
            "Jitter max (ms)"
        ])
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)

        btn_row = QHBoxLayout()

        self.btn_add = QPushButton("Add")
        self.btn_remove = QPushButton("Remove")
        self.btn_save = QPushButton("Save")
        self.btn_start = QPushButton("Start")
        self.btn_stop = QPushButton("Stop")

        self.btn_add.clicked.connect(self._add_row)
        self.btn_remove.clicked.connect(self._remove_selected)
        self.btn_save.clicked.connect(self._save)
        self.btn_start.clicked.connect(self._start)
        self.btn_stop.clicked.connect(self._stop)

        btn_row.addWidget(self.btn_add)
        btn_row.addWidget(self.btn_remove)
        btn_row.addStretch(1)
        btn_row.addWidget(self.btn_save)
        btn_row.addWidget(self.btn_start)
        btn_row.addWidget(self.btn_stop)

        layout.addLayout(btn_row)

        root.setLayout(layout)
        self.setCentralWidget(root)

        self._load_into_table()

    # ---------------- HOTKEY ----------------

    def _toggle_hotkey(self) -> None:
        """
        Called from pynput thread.
        MUST schedule into Qt thread.
        """
        QTimer.singleShot(0, self._toggle_from_ui_thread)

    def _toggle_from_ui_thread(self) -> None:
        if self._running:
            self._stop()
        else:
            self._start()

    # ---------------- WINDOW EVENTS ----------------

    def closeEvent(self, event):
        try:
            self._hotkey.stop()
        except Exception:
            pass

        self._stop()
        event.accept()

    # ---------------- TABLE LOAD/SAVE ----------------

    def _load_into_table(self) -> None:
        self.table.setRowCount(0)
        for it in self._items:
            self._append_item(it)

    def _append_item(self, it: MacroItem) -> None:
        r = self.table.rowCount()
        self.table.insertRow(r)

        enabled = QCheckBox()
        enabled.setChecked(it.enabled)
        self.table.setCellWidget(r, 0, enabled)

        self.table.setItem(r, 1, QTableWidgetItem(it.name))
        self.table.setItem(r, 2, QTableWidgetItem(it.key))
        self.table.setItem(r, 3, QTableWidgetItem(str(it.interval_ms)))
        self.table.setItem(r, 4, QTableWidgetItem(str(it.jitter_min_ms)))
        self.table.setItem(r, 5, QTableWidgetItem(str(it.jitter_max_ms)))

    def _read_table_items(self) -> List[MacroItem]:
        items: List[MacroItem] = []

        for r in range(self.table.rowCount()):
            enabled_widget = self.table.cellWidget(r, 0)
            enabled = enabled_widget.isChecked() if isinstance(enabled_widget, QCheckBox) else True

            name = self.table.item(r, 1).text().strip() if self.table.item(r, 1) else "Item"
            key = self.table.item(r, 2).text().strip() if self.table.item(r, 2) else "1"

            def _int(col: int, default: int) -> int:
                try:
                    return int(self.table.item(r, col).text().strip())
                except Exception:
                    return default

            interval_ms = max(50, _int(3, 1000))
            jmin = max(0, _int(4, 0))
            jmax = max(jmin, _int(5, 0))

            items.append(MacroItem(
                name=name,
                key=key,
                interval_ms=interval_ms,
                jitter_min_ms=jmin,
                jitter_max_ms=jmax,
                enabled=enabled
            ))

        return items

    # ---------------- BUTTON ACTIONS ----------------

    def _add_row(self) -> None:
        self._append_item(MacroItem(name="NewItem", key="1", interval_ms=1000))

    def _remove_selected(self) -> None:
        rows = sorted({i.row() for i in self.table.selectedIndexes()}, reverse=True)
        for r in rows:
            self.table.removeRow(r)

    def _save(self) -> None:
        self._items = self._read_table_items()
        cfg = write_items(self._cfg, self._items)
        save_config(cfg)
        QMessageBox.information(self, "Saved", "Saved into favwhite.cfg")

    # ---------------- START/STOP ----------------

    def _start(self) -> None:
        if self._running:
            return

        self._items = self._read_table_items()

        if not any(i.enabled for i in self._items):
            QMessageBox.warning(self, "Nothing enabled", "Enable at least one item.")
            return

        def on_stop():
            self._stop()

        self._overlay = OverlayWindow(self._items, on_stop=on_stop)

        def on_tick(snapshot):
            if self._overlay:
                self._overlay.set_state(snapshot)

        self._scheduler = MacroScheduler(
            self._items,
            send_fn=press_key,
            on_tick=on_tick
        )

        self._scheduler.start()

        self._running = True
        self.hide()
        self._overlay.show()

    def _stop(self) -> None:
        if not self._running:
            return

        if self._scheduler:
            self._scheduler.stop()
            self._scheduler = None

        if self._overlay:
            self._overlay.close()
            self._overlay = None

        self._running = False
        self.show()
        self.raise_()
        self.activateWindow()


def main() -> None:
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
