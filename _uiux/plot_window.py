from __future__ import annotations

from collections import defaultdict, deque
from typing import Dict

from PyQt5.QtWidgets import QMainWindow, QTabWidget, QWidget, QVBoxLayout

try:
    import pyqtgraph as pg
except Exception:  # pragma: no cover - only used when dependency is missing locally.
    pg = None


class SignalPlotWindow(QMainWindow):
    """Floating pyqtgraph-based ALL Graph window.

    The window stays independent from the main GUI and receives live samples from
    the async mock backend.  It is intentionally public-safe: only synthetic mock
    values are plotted.
    """

    def __init__(self, parent=None, maxlen: int = 240):
        super().__init__(parent)
        self.setWindowTitle("ALL Graph — pyqtgraph floating monitor")
        self.maxlen = int(maxlen)
        self.buffers: Dict[str, deque] = defaultdict(lambda: deque(maxlen=self.maxlen))
        self.resize(980, 620)
        self._curves: Dict[str, object] = {}
        self._build_ui()

    def _build_ui(self) -> None:
        if pg is None:
            from PyQt5.QtWidgets import QLabel

            label = QLabel(
                "pyqtgraph is not installed.\n\nRun: pip install -r requirements.txt",
                self,
            )
            label.setStyleSheet("background:#11151D;color:#E7EBF4;font-size:15px;padding:24px;")
            self.setCentralWidget(label)
            return

        pg.setConfigOptions(antialias=True, background="#11151D", foreground="#D7DCE7")
        tabs = QTabWidget()
        tabs.addTab(self._make_plot_tab("Mock DAQ Measurements", ["signal1", "signal2", "signal3", "signal4", "signal5", "signal6"]), "DAQ")
        tabs.addTab(self._make_plot_tab("Mock Model / ECU Outputs", ["model1_a", "model1_b", "model2", "model3", "model4", "ecu_write_value"]), "Model / ECU")
        self.setCentralWidget(tabs)

    def _make_plot_tab(self, title: str, keys: list[str]) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        if pg is None:
            return page
        plot = pg.PlotWidget(title=title)
        plot.showGrid(x=True, y=True, alpha=0.25)
        plot.addLegend(offset=(12, 12))
        layout.addWidget(plot)
        palette = ["#79B4FF", "#9AE6B4", "#FFE000", "#D946EF", "#FB923C", "#F87171", "#67E8F9"]
        for i, key in enumerate(keys):
            curve = plot.plot([], [], pen=pg.mkPen(palette[i % len(palette)], width=2), name=key)
            self._curves[key] = curve
        return page

    def append_sample(self, values):
        for k, v in values.items():
            try:
                self.buffers[k].append(float(v))
            except Exception:
                continue
        self._refresh()

    def clear(self) -> None:
        self.buffers.clear()
        self._refresh()

    def _refresh(self) -> None:
        if pg is None:
            return
        for key, curve in self._curves.items():
            values = list(self.buffers.get(key, []))
            x = list(range(len(values)))
            curve.setData(x, values)


class EdgeFlowWindow(QMainWindow):
    """Floating pyqtgraph window for one independent canvas connection."""

    def __init__(self, edge_meta: dict, parent=None, maxlen: int = 240):
        super().__init__(parent)
        self.edge_meta = dict(edge_meta or {})
        self.data_key = str(self.edge_meta.get("data_key", ""))
        self.maxlen = int(maxlen)
        self.buffer = deque(maxlen=self.maxlen)
        self.setWindowTitle(f"Data Flow — {self.edge_meta.get('label', self.data_key)}")
        self.resize(760, 420)
        self._curve = None
        self._build_ui()

    def _build_ui(self) -> None:
        if pg is None:
            from PyQt5.QtWidgets import QLabel

            label = QLabel(
                "pyqtgraph is not installed.\n\nRun: pip install -r requirements.txt",
                self,
            )
            label.setStyleSheet("background:#11151D;color:#E7EBF4;font-size:15px;padding:24px;")
            self.setCentralWidget(label)
            return

        pg.setConfigOptions(antialias=True, background="#11151D", foreground="#D7DCE7")
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(8, 8, 8, 8)
        label = self.edge_meta.get("label", self.data_key)
        plot = pg.PlotWidget(title=f"{label}  |  key={self.data_key}")
        plot.showGrid(x=True, y=True, alpha=0.25)
        plot.addLegend(offset=(12, 12))
        self._curve = plot.plot([], [], pen=pg.mkPen("#F8FBFF", width=2), name=self.data_key or "value")
        layout.addWidget(plot)
        self.setCentralWidget(page)

    def append_sample(self, values: dict) -> None:
        if not self.data_key:
            return
        if self.data_key not in values:
            return
        try:
            self.buffer.append(float(values[self.data_key]))
        except Exception:
            return
        self._refresh()

    def _refresh(self) -> None:
        if pg is None or self._curve is None:
            return
        values = list(self.buffer)
        self._curve.setData(list(range(len(values))), values)
