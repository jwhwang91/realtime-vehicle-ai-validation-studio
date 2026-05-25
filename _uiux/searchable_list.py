from __future__ import annotations

import json

from PyQt5.QtCore import QMimeData, QSize, Qt, pyqtSignal
from PyQt5.QtGui import QDrag
from PyQt5.QtWidgets import QLineEdit, QListWidget, QListWidgetItem, QVBoxLayout, QWidget


MIME_SIGNAL = "application/x-a2l-signal"


class DraggableSignalList(QListWidget):
    signal_selected = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setSelectionMode(QListWidget.SingleSelection)
        self.itemSelectionChanged.connect(self._emit_selection)

    def _emit_selection(self):
        item = self.currentItem()
        if item:
            self.signal_selected.emit(item.data(Qt.UserRole) or {"name": item.text()})

    def startDrag(self, supported_actions):
        item = self.currentItem()
        if not item:
            return
        meta = item.data(Qt.UserRole) or {"name": item.text()}
        mime = QMimeData()
        mime.setData(MIME_SIGNAL, json.dumps(meta).encode("utf-8"))
        mime.setText(meta.get("name", item.text()))
        drag = QDrag(self)
        drag.setMimeData(mime)
        drag.exec_(Qt.CopyAction)


class SearchableList(QWidget):
    signal_selected = pyqtSignal(dict)
    signal_double_clicked = pyqtSignal(dict)
    visible_count_changed = pyqtSignal(int, int)

    def __init__(self, title: str = "signals", parent=None):
        super().__init__(parent)
        self._items = []
        self.search = QLineEdit()
        self.search.setPlaceholderText(f"Search {title}...")
        self.list = DraggableSignalList()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.addWidget(self.search)
        layout.addWidget(self.list)
        self.search.textChanged.connect(self._filter)
        self.list.signal_selected.connect(self.signal_selected)
        self.list.itemDoubleClicked.connect(self._emit_double_clicked)

    def set_items(self, items):
        self._items = [dict(x) if isinstance(x, dict) else {"name": str(x)} for x in items]
        self.list.clear()
        for meta in self._items:
            label = meta.get("name", "unknown")
            address = meta.get("address", meta.get("ecuAddress", "0x00000000"))
            datatype = meta.get("datatype", meta.get("dataType", "UNKNOWN"))
            item = QListWidgetItem(f"{label}\n{meta.get('type', 'SIGNAL')} · {datatype} · {address}")
            item.setData(Qt.UserRole, meta)
            self.list.addItem(item)
        self._filter(self.search.text())


    def apply_font_scale(self, scale: float) -> None:
        scale = max(0.88, min(1.20, float(scale)))
        font = self.font()
        font.setPointSize(max(9, int(round(10 * scale))))
        self.setFont(font)
        self.search.setFont(font)
        self.list.setFont(font)
        row_h = max(48, int(round(56 * scale)))
        for row in range(self.list.count()):
            self.list.item(row).setSizeHint(self.list.item(row).sizeHint().expandedTo(QSize(10, row_h)))

    def current_signal(self):
        item = self.list.currentItem()
        return item.data(Qt.UserRole) if item else None

    def total_count(self) -> int:
        return len(self._items)

    def visible_count(self) -> int:
        return sum(1 for row in range(self.list.count()) if not self.list.item(row).isHidden())

    def select_first(self):
        if self.list.count() > 0:
            self.list.setCurrentRow(0)

    def _emit_double_clicked(self, item):
        self.signal_double_clicked.emit(item.data(Qt.UserRole) or {"name": item.text()})

    def _filter(self, text):
        q = text.lower().strip()
        visible = 0
        for row in range(self.list.count()):
            item = self.list.item(row)
            meta = item.data(Qt.UserRole) or {}
            haystack = " ".join(str(v) for v in meta.values()).lower()
            hidden = q not in haystack
            item.setHidden(hidden)
            if not hidden:
                visible += 1
        self.visible_count_changed.emit(visible, self.list.count())
