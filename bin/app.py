from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path
from typing import List, Optional, Any

from PySide6.QtCore import QTimer, QUrl
from PySide6.QtGui import QIcon, QDesktopServices
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTableWidget, QTableWidgetItem, QMessageBox, QLabel,
    QCheckBox, QComboBox, QHeaderView, QSpinBox, QKeySequenceEdit
)

from models import MacroItem
from storage import load_config, save_config, load_items, write_items, app_resource_path
from input_send import press_key, click_left
from scheduler import MacroScheduler
from overlay import OverlayWindow
from hotkey import GlobalHotkey


ALLOWED_KEYS = ["2", "3", "4", "5", "6", "7"]
DEFAULT_UPDATE_URL = "https://github.com/Kreativscripts/FavWhite"


def _exe_dir() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS).resolve()
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def _read_version_json() -> dict:
    p = _exe_dir() / "version.json"
    if not p.exists():
        return {
            "version": "unknown",
            "version_checker": "https://favnc.pages.dev/bss/whm.json",
            "update_url": DEFAULT_UPDATE_URL,
        }

    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {
            "version": "unknown",
            "version_checker": "https://favnc.pages.dev/bss/whm.json",
            "update_url": DEFAULT_UPDATE_URL,
        }


def _extract_remote_version(payload: Any) -> Optional[str]:
    if payload is None:
        return None
    if isinstance(payload, str):
        return payload.strip()
    if isinstance(payload, dict):
        if isinstance(payload.get("version"), str):
            return payload["version"].strip()
        for v in payload.values():
            if isinstance(v, str):
                return v.strip()
    return None


def check_for_update(parent: QWidget) -> bool:
    local_cfg = _read_version_json()
    local_version = str(local_cfg.get("version", "unknown")).strip()
    checker_url = str(local_cfg.get("version_checker", "")).strip()
    update_url = str(local_cfg.get("update_url", DEFAULT_UPDATE_URL)).strip()

    if not checker_url:
        return True

    try:
        req = urllib.request.Request(
            checker_url,
            headers={"User-Agent": f"FavWhite/{local_version}"}
        )
        with urllib.request.urlopen(req, timeout=3.5) as resp:
            raw = resp.read().decode("utf-8", errors="replace")

        data = json.loads(raw)
        remote_version = _extract_remote_version(data)

        if not remote_version:
            return True

        if remote_version.strip() != local_version:
            QMessageBox.warning(
                parent,
                "Update required",
                "This is the older version of the app. Please go install the updated version on "
                "https://github.com/Kreativscripts/FavWhite"
            )
            QDesktopServices.openUrl(QUrl(update_url))
            return False

        return True

    except Exception:
        return True


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()

        ver = _read_version_json().get("version", "unknown")
        self.setWindowTitle(f"FavWhite ({ver})")
        self.resize(900, 520)
        self.setMinimumSize(760, 420)
        self.setWindowOpacity(0.85)

        icon_path = app_resource_path("assets/icon.ico")
        if icon_path.exists():
            ico = QIcon(str(icon_path))
            self.setWindowIcon(ico)
            QApplication.instance().setWindowIcon(ico)

        self._scheduler: MacroScheduler | None = None
        self._overlay: OverlayWindow | None = None
        self._running: bool = False

        self._cfg = load_config()
        self._items: List[MacroItem] = load_items(self._cfg)

        root = QWidget()
        layout = QVBoxLayout(root)

        header_row = QHBoxLayout()
        lbl_header = QLabel("FavWhite Macro UI")
        lbl_header.setStyleSheet("font-weight: 600; font-size: 13px;")
        header_row.addWidget(lbl_header)
        header_row.addStretch(1)
        layout.addLayout(header_row)

        controls = QHBoxLayout()

        controls.addWidget(QLabel("Hotkey:"))
        self.hotkey_edit = QKeySequenceEdit()
        self.hotkey_edit.setKeySequence(self._cfg.get("hotkey", "Ctrl+Q"))
        controls.addWidget(self.hotkey_edit)

        self.btn_apply_hotkey = QPushButton("Apply hotkey")
        controls.addWidget(self.btn_apply_hotkey)

        controls.addSpacing(16)

        self.chk_tool_use = QCheckBox("Enable tool use")
        self.chk_tool_use.setChecked(bool(self._cfg.get("tool_use", {}).get("enabled", False)))
        controls.addWidget(self.chk_tool_use)

        controls.addWidget(QLabel("delay (ms):"))
        self.spin_tool_delay = QSpinBox()
        self.spin_tool_delay.setRange(10, 5000)
        self.spin_tool_delay.setValue(int(self._cfg.get("tool_use", {}).get("interval_ms", 30)))
        controls.addWidget(self.spin_tool_delay)

        controls.addStretch(1)
        layout.addLayout(controls)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels([
            "Enabled",
            "Name",
            "Key",
            "Interval (ms)",
            "Jitter min (ms)",
            "Jitter max (ms)"
        ])

        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(1, QHeaderView.Stretch)
        hh.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(5, QHeaderView.ResizeToContents)

        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(False)

        layout.addWidget(self.table, stretch=1)

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
        self.btn_apply_hotkey.clicked.connect(self._apply_hotkey)

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

        self._hotkey = GlobalHotkey(self._toggle_hotkey, self._cfg.get("hotkey", "Ctrl+Q"))
        self._hotkey.start()

    def _toggle_hotkey(self) -> None:
        QTimer.singleShot(0, self._toggle_from_ui_thread)

    def _toggle_from_ui_thread(self) -> None:
        if self._running:
            self._stop()
        else:
            self._start()

    def _apply_hotkey(self) -> None:
        seq = self.hotkey_edit.keySequence().toString().strip()
        if not seq:
            QMessageBox.warning(self, "Invalid hotkey", "Pick a hotkey first.")
            return

        self._cfg["hotkey"] = seq
        save_config(self._cfg)

        try:
            self._hotkey.set_hotkey(seq)
        except Exception:
            QMessageBox.warning(self, "Hotkey failed", "Could not register that hotkey.")
            return

        QMessageBox.information(self, "Hotkey saved", f"Hotkey set to: {seq}")

    def closeEvent(self, event):
        try:
            self._hotkey.stop()
        except Exception:
            pass
        self._stop()
        event.accept()

    def _load_into_table(self) -> None:
        self.table.setRowCount(0)
        for it in self._items:
            self._append_item(it)

    def _append_item(self, it: MacroItem) -> None:
        r = self.table.rowCount()
        self.table.insertRow(r)

        enabled = QCheckBox()
        enabled.setChecked(it.enabled)
        enabled.setStyleSheet("margin-left:10px;")
        self.table.setCellWidget(r, 0, enabled)

        self.table.setItem(r, 1, QTableWidgetItem(it.name))

        key_box = QComboBox()
        key_box.addItems(ALLOWED_KEYS)
        key_box.setCurrentText(it.key if it.key in ALLOWED_KEYS else "2")
        self.table.setCellWidget(r, 2, key_box)

        self.table.setItem(r, 3, QTableWidgetItem(str(it.interval_ms)))
        self.table.setItem(r, 4, QTableWidgetItem(str(it.jitter_min_ms)))
        self.table.setItem(r, 5, QTableWidgetItem(str(it.jitter_max_ms)))

    def _read_table_items(self) -> List[MacroItem]:
        items: List[MacroItem] = []

        for r in range(self.table.rowCount()):
            enabled_widget = self.table.cellWidget(r, 0)
            enabled = enabled_widget.isChecked() if isinstance(enabled_widget, QCheckBox) else True

            name = self.table.item(r, 1).text().strip() if self.table.item(r, 1) else "Item"

            key_widget = self.table.cellWidget(r, 2)
            key = key_widget.currentText().strip() if isinstance(key_widget, QComboBox) else "2"
            if key not in ALLOWED_KEYS:
                key = "2"

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

    def _add_row(self) -> None:
        self._append_item(MacroItem(name="NewItem", key="2", interval_ms=1000))

    def _remove_selected(self) -> None:
        rows = sorted({i.row() for i in self.table.selectedIndexes()}, reverse=True)
        for r in rows:
            self.table.removeRow(r)

    def _save(self) -> None:
        self._items = self._read_table_items()

        self._cfg["tool_use"] = {
            "enabled": bool(self.chk_tool_use.isChecked()),
            "interval_ms": int(self.spin_tool_delay.value()),
        }

        seq = self.hotkey_edit.keySequence().toString().strip()
        if seq:
            self._cfg["hotkey"] = seq

        cfg = write_items(self._cfg, self._items)
        save_config(cfg)

        QMessageBox.information(self, "Saved", "Saved into favwhite.cfg")

    def _start(self) -> None:
        if self._running:
            return

        self._items = self._read_table_items()

        tool_enabled = bool(self.chk_tool_use.isChecked())
        tool_delay = int(self.spin_tool_delay.value())

        if not any(i.enabled for i in self._items) and not tool_enabled:
            QMessageBox.warning(self, "Nothing enabled", "Enable at least one macro item or enable tool use.")
            return

        def on_stop():
            self._stop()

        self._overlay = OverlayWindow(
            self._items,
            on_stop=on_stop,
            tool_use_enabled=tool_enabled,
            tool_use_interval_ms=tool_delay
        )

        def on_tick(snapshot):
            if self._overlay:
                self._overlay.set_state(snapshot)

        self._scheduler = MacroScheduler(
            items=self._items,
            send_fn=press_key,
            on_tick=on_tick,
            tool_use_enabled=tool_enabled,
            tool_use_interval_ms=tool_delay,
            tool_use_fn=click_left
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

    icon_path = app_resource_path("assets/icon.ico")
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    temp = QWidget()
    temp.setWindowIcon(app.windowIcon())

    if not check_for_update(temp):
        return

    w = MainWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
