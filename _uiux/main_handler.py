from __future__ import annotations

import time
from pathlib import Path
from typing import Dict, List

from PyQt5.QtCore import QPointF, Qt, QTimer
from PyQt5.QtGui import QColor, QKeySequence, QPainter, QPen
from PyQt5.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QFileDialog,
    QShortcut,
    QSplitter,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from _backend import get_backend
from _backend.interface import BackendRuntimeConfig
from _utility.a2l_parser import parse_a2l
from .canvas_scene import DiagramScene, DiagramView
from .dialogs import FileSettingsDialog, ModelBlockDialog, XcpSettingsDialog
from .model_monitor import ModelMonitorWindow
from .plot_window import EdgeFlowWindow, SignalPlotWindow
from .searchable_list import SearchableList


class LiveChartWidget(QWidget):
    """Small embedded live chart matching the HTML mock bottom dock."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(190)
        self.history: List[Dict[str, float]] = []

    def append_sample(self, row: Dict[str, float]) -> None:
        normalized = {k: float(v) for k, v in row.items() if _is_number(v)}
        if not normalized:
            return
        merged = dict(self.history[-1]) if self.history else {}
        merged.update(normalized)
        self.history.append(merged)
        if len(self.history) > 140:
            self.history.pop(0)
        self.update()

    def clear(self) -> None:
        self.history.clear()
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        rect = self.rect().adjusted(8, 8, -8, -8)
        painter.fillRect(rect, QColor("#FFFFFF"))
        painter.setPen(QPen(QColor("#E7EAF0"), 1))
        for x in range(rect.left() + 42, rect.right(), 70):
            painter.drawLine(x, rect.top() + 10, x, rect.bottom() - 28)
        for y in range(rect.top() + 24, rect.bottom() - 20, 38):
            painter.drawLine(rect.left() + 42, y, rect.right() - 16, y)

        series = [
            ("signal1", QColor("#1F4FD8"), 65.0, 95.0, "signal1"),
            ("signal3", QColor("#0F766E"), 0.08, 0.20, "signal3"),
            ("model4", QColor("#D946EF"), -0.2, 1.1, "model4"),
            ("ecu_write_value", QColor("#D97706"), -0.2, 1.1, "ECU Write"),
        ]
        for key, color, vmin, vmax, _label in series:
            self._draw_series(painter, rect, key, color, vmin, vmax)

        painter.setFont(self.font())
        base_y = rect.bottom() - 12
        for i, (_key, color, _vmin, _vmax, label) in enumerate(series):
            x = rect.left() + 54 + i * 120
            painter.setPen(Qt.NoPen)
            painter.setBrush(color)
            painter.drawRect(x, base_y - 4, 12, 3)
            painter.setPen(QColor("#334155"))
            painter.drawText(x + 17, base_y, label)

    def _draw_series(self, painter: QPainter, rect, key: str, color: QColor, vmin: float, vmax: float):
        rows = [r for r in self.history if key in r]
        if len(rows) < 2:
            return
        left = rect.left() + 44
        right = rect.right() - 26
        top = rect.top() + 18
        bottom = rect.bottom() - 30
        width = max(1, right - left)
        height = max(1, bottom - top)
        painter.setPen(QPen(color, 2))
        last = None
        for i, row in enumerate(rows):
            x = left + i / max(len(rows) - 1, 1) * width
            y = bottom - (row[key] - vmin) / max(vmax - vmin, 1e-9) * height
            y = max(top, min(bottom, y))
            if last is not None:
                painter.drawLine(int(last[0]), int(last[1]), int(x), int(y))
            last = (x, y)


def _is_number(value) -> bool:
    try:
        float(value)
        return True
    except Exception:
        return False


class MainWindow(QMainWindow):
    def __init__(self, project_root: Path, parent=None):
        super().__init__(parent)
        self.project_root = Path(project_root)
        self.setWindowTitle("XCP-Based AI Validation Interface Mock — PyQt5")
        self.files = {
            "a2l_path": str(self.project_root / "assets/mock_a2l/mock_ecu.a2l"),
            "elf_path": str(self.project_root / "assets/mock_elf/mock_ecu_symbols.elf"),
            "model_path": str(self.project_root / "assets/mock_models/demo_model.py"),
        }
        self.cycle_ms = 16
        self.backend = None
        self.measurements: List[dict] = []
        self.characteristics: List[dict] = []
        self._last_measurements: Dict[str, float] = {}
        self._last_outputs: Dict[str, float] = {}
        self._last_tick_ts = None
        self._jitter_values: List[float] = []
        # Keep graph/monitor as true floating windows, not embedded child widgets.
        self.monitor = ModelMonitorWindow(None)
        self.plot = SignalPlotWindow(None)
        self.edge_flow_windows: Dict[str, EdgeFlowWindow] = {}
        self._all_live_values: Dict[str, float] = {}
        self._responsive_font_scale = 1.0
        self._setup_ui()
        self._load_signal_catalog()
        QTimer.singleShot(0, self._apply_responsive_fonts)

    def _setup_ui(self):
        root = QWidget()
        root.setObjectName("xcpRoot")
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(14, 14, 14, 14)
        root_layout.setSpacing(0)

        frame = QFrame()
        frame.setObjectName("xcpFrame")
        frame_layout = QVBoxLayout(frame)
        frame_layout.setContentsMargins(0, 0, 0, 0)
        frame_layout.setSpacing(0)

        frame_layout.addWidget(self._topline())
        frame_layout.addWidget(self._toolbar())

        body_splitter = QSplitter(Qt.Horizontal)
        body_splitter.setObjectName("xcpLayout")
        body_splitter.addWidget(self._sidebar())
        body_splitter.addWidget(self._main_area())
        body_splitter.setSizes([280, 1160])
        frame_layout.addWidget(body_splitter, 1)

        root_layout.addWidget(frame)
        self.setCentralWidget(root)
        self._apply_local_styles()

    def _topline(self) -> QFrame:
        bar = QFrame()
        bar.setObjectName("xcpTopline")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(8)

        file_btn = QPushButton("📁 File / Dir")
        file_btn.setObjectName("chipMuted")
        file_btn.clicked.connect(self._open_file_settings)
        layout.addWidget(file_btn)
        layout.addWidget(QLabel("Calibration metadata: <b>omitted</b>"))
        layout.addWidget(QLabel("Build symbols: <b>omitted</b>"))
        update_btn = QPushButton("UPDATE")
        update_btn.setEnabled(False)
        layout.addWidget(update_btn)
        xcp_btn = QPushButton("XCP Setting")
        xcp_btn.clicked.connect(self._open_xcp_settings)
        layout.addWidget(xcp_btn)
        conn_btn = QPushButton("XCP Connection")
        conn_btn.setObjectName("chipYellow")
        conn_btn.setEnabled(False)
        layout.addWidget(conn_btn)
        layout.addStretch(1)
        self.run_status = QLabel("<b>Offline</b>")
        self.jitter_avg = QLabel("Avg: <b>—</b>")
        self.jitter_max = QLabel("Max: <b>—</b>")
        layout.addWidget(self.run_status)
        layout.addWidget(QLabel("Jitter:"))
        layout.addWidget(self.jitter_avg)
        layout.addWidget(self.jitter_max)
        return bar

    def _toolbar(self) -> QFrame:
        bar = QFrame()
        bar.setObjectName("xcpToolbar")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(12, 7, 12, 7)
        layout.setSpacing(8)
        self.all_graph_btn = QPushButton("ALL Graph")
        self.all_graph_btn.clicked.connect(self._show_all_graph)
        layout.addWidget(self.all_graph_btn)
        self.add_model_btn = QPushButton("Add Model")
        self.add_model_btn.clicked.connect(self._add_model_from_button)
        layout.addWidget(self.add_model_btn)
        for text in ["Save Canvas", "Open Canvas"]:
            btn = QPushButton(text)
            btn.setEnabled(False)
            layout.addWidget(btn)
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self.scene_clear_requested if hasattr(self, 'scene_clear_requested') else lambda: None)
        # Reconnect after scene creation in _main_area; keep button enabled for real canvas clearing.
        self.clear_canvas_btn = clear_btn
        layout.addWidget(clear_btn)
        self.start_btn = QPushButton("Start")
        self.start_btn.setObjectName("startGlow")
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setEnabled(False)
        self.start_btn.clicked.connect(self._xcp_start)
        self.stop_btn.clicked.connect(self._xcp_stop)
        layout.addWidget(self.start_btn)
        layout.addWidget(self.stop_btn)
        layout.addStretch(1)
        layout.addWidget(QLabel("public mock session"))
        return bar

    def _sidebar(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("xcpSidebar")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.tabs = QTabWidget()
        self.tabs.setObjectName("xcpTabs")
        self.measurement_list = SearchableList("measurements")
        self.characteristic_list = SearchableList("characteristics")
        self.tabs.addTab(self.measurement_list, "MEASUREMENT")
        self.tabs.addTab(self.characteristic_list, "CHARACTERISTIC")
        self.measurement_list.signal_selected.connect(self._show_signal_info)
        self.characteristic_list.signal_selected.connect(self._show_signal_info)
        self.measurement_list.signal_double_clicked.connect(self._add_signal_from_list)
        self.characteristic_list.signal_double_clicked.connect(self._add_signal_from_list)
        self.measurement_list.visible_count_changed.connect(lambda _v, _t: self._update_sidebar_count())
        self.characteristic_list.visible_count_changed.connect(lambda _v, _t: self._update_sidebar_count())
        self.tabs.currentChanged.connect(lambda _idx: self._update_sidebar_count())
        layout.addWidget(self.tabs, 1)
        self.signal_count = QLabel("0 Signals")
        self.signal_count.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.signal_count.setObjectName("signalCount")
        layout.addWidget(self.signal_count)
        return panel

    def _main_area(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.scene = DiagramScene(self)
        self.scene.node_info_requested.connect(self._show_signal_info)
        self.scene.model_load_requested.connect(self._load_model_for_node)
        self.scene.edge_flow_requested.connect(self._open_edge_flow_graph)
        self.scene.status_requested.connect(self._append_status)
        self.view = DiagramView(self.scene)
        if hasattr(self, "clear_canvas_btn"):
            try:
                self.clear_canvas_btn.clicked.disconnect()
            except Exception:
                pass
            self.clear_canvas_btn.clicked.connect(self.scene.reset_demo_graph)
        self.delete_shortcut = QShortcut(QKeySequence.Delete, self)
        self.delete_shortcut.activated.connect(self.scene.delete_selected_node)
        self.backspace_shortcut = QShortcut(QKeySequence(Qt.Key_Backspace), self)
        self.backspace_shortcut.activated.connect(self.scene.delete_selected_node)
        self.esc_shortcut = QShortcut(QKeySequence(Qt.Key_Escape), self)
        self.esc_shortcut.activated.connect(lambda: self.scene.cancel_connection("Connection canceled."))
        layout.addWidget(self.view, 1)
        layout.addWidget(self._bottom_dock())
        return panel

    def _bottom_dock(self) -> QFrame:
        dock = QFrame()
        dock.setObjectName("bottomDock")
        layout = QHBoxLayout(dock)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        info_panel = QFrame()
        info_panel.setObjectName("bottomPanel")
        info_layout = QVBoxLayout(info_panel)
        title_row = QHBoxLayout()
        title_row.addWidget(QLabel("📌 Signal Info"))
        title_row.addStretch(1)
        self.selected_type = QLabel("MEASUREMENT")
        self.selected_type.setObjectName("tinyStat")
        title_row.addWidget(self.selected_type)
        info_layout.addLayout(title_row)
        self.info_table = QTableWidget(0, 2)
        self.info_table.setHorizontalHeaderLabels(["Field", "Value"])
        self.info_table.verticalHeader().setVisible(False)
        self.info_table.horizontalHeader().setStretchLastSection(True)
        info_layout.addWidget(self.info_table)
        info_panel.setMinimumWidth(420)
        layout.addWidget(info_panel)

        chart_panel = QFrame()
        chart_panel.setObjectName("bottomPanel")
        chart_layout = QVBoxLayout(chart_panel)
        chart_title = QHBoxLayout()
        chart_title.addWidget(QLabel("Real Time Data"))
        chart_title.addStretch(1)
        tag = QLabel("synthetic replay · live update")
        tag.setObjectName("tinyStat")
        chart_title.addWidget(tag)
        chart_layout.addLayout(chart_title)
        self.chart = LiveChartWidget()
        chart_layout.addWidget(self.chart)
        caption = QLabel("Visible traces: signal1, signal3, model4, ECU write. This is synthetic replay data only.")
        caption.setObjectName("chartCaption")
        chart_layout.addWidget(caption)
        layout.addWidget(chart_panel, 1)
        return dock

    def _apply_local_styles(self):
        self.setStyleSheet(
            self.styleSheet()
            + """
            QWidget#xcpRoot { background: #0B0D12; }
            QFrame#xcpFrame { background: #0D1018; border: 1px solid #1F2431; border-radius: 18px; }
            QFrame#xcpTopline, QFrame#xcpToolbar { background: #151922; border-bottom: 1px solid #2A3141; color: #D7DCE7; }
            QFrame#xcpToolbar { background: #11151D; }
            QPushButton { border: 1px solid #384154; background: #1E2432; color: #E6EBF5; border-radius: 6px; padding: 5px 10px; font-weight: 800; }
            QPushButton:disabled { opacity: .45; background: #1E2432; color: #7F8795; }
            QPushButton#chipYellow { background: #F3E000; color: #0B0B0B; border-color: #F3E000; }
            QPushButton#chipMuted { background: #1B202C; color: #97A1B4; }
            QPushButton#startGlow { background: #FFFFFF; color: #05070C; border-color: #FFFFFF; }
            QFrame#xcpSidebar { background: #11151D; border-right: 1px solid #2A3141; }
            QTabWidget::pane { border: 0; }
            QTabBar::tab { background: #161B26; color: #C9D1DD; padding: 10px 14px; font-weight: 800; border-right: 1px solid #2A3141; }
            QTabBar::tab:selected { background: #1C212C; color: #FFFFFF; border-bottom: 2px solid #FFE000; }
            QLineEdit { background: #0E1219; border: 1px solid #30384A; color: #D8DCE4; border-radius: 6px; padding: 8px 10px; }
            QListWidget { background: #11151D; border: 0; color: #D9E0EC; outline: 0; }
            QListWidget::item { padding: 7px 12px; border-bottom: 1px solid #1C2230; }
            QListWidget::item:selected { background: #24314F; color: #FFFFFF; border-left: 3px solid #79B4FF; }
            QLabel#signalCount { background: #131823; color: #DFE4EF; border-top: 1px solid #2A3141; padding: 8px 12px; }
            QFrame#bottomDock { background: #171C25; border-top: 1px solid #2A3141; }
            QFrame#bottomPanel { background: #171C25; border-right: 1px solid #2A3141; padding: 8px; }
            QLabel#tinyStat { background: #252B39; color: #EDF2FA; border-radius: 9px; padding: 2px 8px; }
            QLabel#chartCaption { color: #9DA7B9; font-size: 11px; }
            QTableWidget { background: #1F232C; color: #E7EBF4; border: 1px solid #2A3141; border-radius: 10px; gridline-color: #2A3141; }
            QHeaderView::section { background: #252B39; color: #D8DDE8; border: 0; padding: 5px; }
            """
        )

    def _load_signal_catalog(self):
        try:
            parsed = parse_a2l(Path(self.files["a2l_path"]))
            self.measurements = parsed["measurements"]
            self.characteristics = parsed["characteristics"]
            self.measurement_list.set_items(self.measurements)
            self.characteristic_list.set_items(self.characteristics)
            self._update_sidebar_count()
            self.scene.set_signal_catalog(self.measurements + self.characteristics)
            self._append_status(
                f"Loaded mock A2L: {len(self.measurements)} measurements, {len(self.characteristics)} characteristics"
            )
            self.measurement_list.select_first()
        except Exception as exc:
            self.measurements = []
            self.characteristics = []
            self._append_status(f"A2L load failed: {exc}")

    def _update_sidebar_count(self):
        if not hasattr(self, "signal_count") or not hasattr(self, "tabs"):
            return
        current = self.tabs.currentIndex() if hasattr(self, "tabs") else 0
        widget = self.measurement_list if current == 0 else self.characteristic_list
        label = "Measurements" if current == 0 else "Characteristics"
        visible = widget.visible_count() if hasattr(widget, "visible_count") else widget.list.count()
        total = widget.total_count() if hasattr(widget, "total_count") else widget.list.count()
        if visible == total:
            self.signal_count.setText(f"{total} {label}")
        else:
            self.signal_count.setText(f"{visible} / {total} {label}")

    def _apply_responsive_fonts(self):
        if self.width() <= 0 or self.height() <= 0:
            return
        scale = max(0.88, min(1.20, min(self.width() / 1480.0, self.height() / 920.0)))
        if abs(scale - getattr(self, "_responsive_font_scale", 1.0)) < 0.015:
            return
        self._responsive_font_scale = scale

        base_pt = max(9, int(round(10 * scale)))
        font = self.font()
        font.setPointSize(base_pt)
        self.setFont(font)

        # Apply readable but compact fonts to the dense tool widgets.  This avoids
        # squeezed dialog/table/list text on Windows high-DPI displays.
        for widget in self.findChildren(QWidget):
            wf = widget.font()
            wf.setPointSize(base_pt)
            widget.setFont(wf)

        if hasattr(self, "info_table"):
            self.info_table.verticalHeader().setDefaultSectionSize(max(22, int(26 * scale)))
            self.info_table.horizontalHeader().setDefaultSectionSize(max(24, int(28 * scale)))
            self.info_table.resizeRowsToContents()
        if hasattr(self, "measurement_list"):
            self.measurement_list.apply_font_scale(scale)
        if hasattr(self, "characteristic_list"):
            self.characteristic_list.apply_font_scale(scale)
        if hasattr(self, "scene"):
            self.scene.apply_font_scale(scale)

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(0, self._apply_responsive_fonts)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._apply_responsive_fonts()

    def _runtime_config(self) -> BackendRuntimeConfig:
        return BackendRuntimeConfig(
            measurement_names=[s["name"] for s in self.measurements],
            output_names=[s["name"] for s in self.characteristics],
            a2l_path=self.files["a2l_path"],
            elf_path=self.files["elf_path"],
            model_path=self.files["model_path"],
            cycle_ms=self.cycle_ms,
        )

    def _open_file_settings(self):
        dlg = FileSettingsDialog(self.project_root, self)
        if dlg.exec_():
            self.files.update(dlg.values())
            self._load_signal_catalog()

    def _open_xcp_settings(self):
        dlg = XcpSettingsDialog(self)
        if dlg.exec_():
            self.cycle_ms = int(dlg.values()["cycle_ms"])
            self._append_status(f"Mock cycle set to {self.cycle_ms} ms")

    def _xcp_start(self):
        self.backend = get_backend(use_cpp=True, project_root=self.project_root, parent=self)
        self.backend.signals.status_changed.connect(self._on_status)
        self.backend.signals.data_received.connect(self._on_xcp_data)
        self.backend.signals.model_output.connect(self._on_model_output)
        self.backend.signals.error.connect(self._on_error)
        self.backend.signals.stopped.connect(lambda: self._on_status("Backend stopped"))
        self.backend.start(self._runtime_config())
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.run_status.setText("<b>Online</b>")
        self._last_tick_ts = None
        self._jitter_values.clear()
        self.scene.set_edges_active(True)

    def _xcp_stop(self):
        if self.backend:
            self.backend.stop()
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.run_status.setText("<b>Offline</b>")
        self.jitter_avg.setText("Avg: <b>—</b>")
        self.jitter_max.setText("Max: <b>—</b>")
        self._jitter_values.clear()
        self.scene.set_edges_active(False)

    def _on_status(self, text):
        self._append_status(text)

    def _on_error(self, text):
        self._append_status("ERROR: " + text)
        QMessageBox.warning(self, "Mock backend error", text)

    def _on_xcp_data(self, data):
        self._last_measurements = {k: float(v) for k, v in data.items() if _is_number(v)}
        self.scene.update_measurements(self._last_measurements)
        self._update_snapshot_table(data, "DAQ")
        self._all_live_values.update(self._last_measurements)
        self._all_live_values.update(self._last_outputs)
        self.plot.append_sample(data)
        self.chart.append_sample({**self._last_measurements, **self._last_outputs})
        self._append_edge_flow_samples()
        self._update_jitter()
        self.scene.pulse_active_edges()

    def _on_model_output(self, data):
        self._last_outputs = {k: float(v) for k, v in data.items() if _is_number(v)}
        self.scene.update_model_outputs(self._last_outputs)
        self._update_snapshot_table(data, "MODEL_OUT")
        self.monitor.update_outputs(data)
        self._all_live_values.update(self._last_outputs)
        self.plot.append_sample(data)
        self.chart.append_sample({**self._last_measurements, **self._last_outputs})
        self._append_edge_flow_samples()

    def _update_snapshot_table(self, values, role):
        # Reuse the model monitor table as the external table window; bottom dock stays visually close to the HTML mock.
        return None

    def _show_signal_info(self, meta: dict):
        self.selected_type.setText(meta.get("type", "SIGNAL"))
        rows = [
            ("Name", meta.get("name", "")),
            ("Description", meta.get("description", "")),
            ("ECU_ADDRESS", meta.get("address", meta.get("ecuAddress", ""))),
            ("Data Type", meta.get("datatype", meta.get("dataType", ""))),
            ("Conversion/Symbol", meta.get("variable", "")),
            ("Unit", meta.get("unit", "")),
            ("Setting", meta.get("setting", "")),
            ("Range", meta.get("range", "")),
            ("Symbol", meta.get("symbol", meta.get("name", ""))),
            ("Canvas Node", meta.get("canvas_node_id", "")),
            ("Canvas Subtitle", meta.get("canvas_subtitle", "")),
            ("Model Path", meta.get("model_path", "")),
            ("Input Count", meta.get("input_count", "")),
            ("Output Count", meta.get("output_count", "")),
        ]
        self.info_table.setRowCount(len(rows))
        for r, (field, value) in enumerate(rows):
            self.info_table.setItem(r, 0, QTableWidgetItem(str(field)))
            self.info_table.setItem(r, 1, QTableWidgetItem(str(value)))
        self.info_table.resizeRowsToContents()

    def _add_signal_from_list(self, meta: dict):
        self.scene.add_signal_node(meta)
        self._append_status(f"Added canvas node from A2L list: {meta.get('name', 'unknown')}")

    def _clear_dropped_nodes_note(self):
        if hasattr(self, "scene"):
            self.scene.reset_demo_graph()
        else:
            self._append_status("Canvas is not ready yet.")

    def _show_all_graph(self):
        self.plot.show()
        self.plot.raise_()
        self.plot.activateWindow()
        self.monitor.show()
        self.monitor.raise_()
        self.monitor.activateWindow()
        self._append_status("ALL Graph opened as floating pyqtgraph monitor.")

    def _add_model_from_button(self):
        node = self.scene.add_model_node()
        self._append_status(f"Added empty model block: {node.title}. Double-click it to choose .py/.onnx and I/O counts.")

    def _open_edge_flow_graph(self, edge_meta: dict):
        edge_id = str(edge_meta.get("edge_id", ""))
        if not edge_id:
            return
        window = self.edge_flow_windows.get(edge_id)
        if window is None:
            window = EdgeFlowWindow(edge_meta, None)
            self.edge_flow_windows[edge_id] = window
        window.show()
        window.raise_()
        window.activateWindow()
        self._append_edge_flow_samples()

    def _append_edge_flow_samples(self):
        if not getattr(self, "edge_flow_windows", None):
            return
        combined = {**self._last_measurements, **self._last_outputs, **self._all_live_values}
        for edge_id, window in list(self.edge_flow_windows.items()):
            if not window.isVisible():
                continue
            window.append_sample(combined)

    def _load_model_for_node(self, node_id: str, meta: dict):
        # Double-clicking a MODEL block now opens a full configuration dialog:
        # file path + input count + output count.
        dlg = ModelBlockDialog(self.project_root, meta, self)
        if not dlg.exec_():
            self._append_status("Model configuration canceled.")
            return
        self.scene.configure_model_node(node_id, dlg.values())

    def _update_jitter(self):
        now = time.perf_counter()
        if self._last_tick_ts is not None:
            cycle_ms = (now - self._last_tick_ts) * 1000.0
            jitter = abs(cycle_ms - float(self.cycle_ms)) * 0.055 + 0.85
            self._jitter_values.append(jitter)
            if len(self._jitter_values) > 180:
                self._jitter_values.pop(0)
            avg = sum(self._jitter_values) / len(self._jitter_values)
            mx = max(self._jitter_values)
            self.jitter_avg.setText(f"Avg: <b>{avg:.2f} ms</b>")
            self.jitter_max.setText(f"Max: <b>{mx:.2f} ms</b>")
        self._last_tick_ts = now

    def closeEvent(self, event):
        # Ensure the async replay thread is stopped before Qt starts deleting
        # widgets. Also close floating graph windows created without a parent.
        try:
            if self.backend and self.backend.is_running():
                self.backend.stop()
            if hasattr(self, "plot"):
                self.plot.close()
            if hasattr(self, "monitor"):
                self.monitor.close()
            for window in getattr(self, "edge_flow_windows", {}).values():
                window.close()
        finally:
            super().closeEvent(event)

    def _append_status(self, text):
        self.statusBar().showMessage(text, 6000)
