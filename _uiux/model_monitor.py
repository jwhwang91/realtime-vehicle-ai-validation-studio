from __future__ import annotations

from PyQt5.QtWidgets import QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget


class ModelMonitorWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Mock Model Monitor")
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Output", "Value"])
        layout = QVBoxLayout(self)
        layout.addWidget(self.table)

    def update_outputs(self, outputs):
        self.table.setRowCount(len(outputs))
        for row, (name, value) in enumerate(outputs.items()):
            self.table.setItem(row, 0, QTableWidgetItem(name))
            self.table.setItem(row, 1, QTableWidgetItem(f"{float(value):.4f}"))
