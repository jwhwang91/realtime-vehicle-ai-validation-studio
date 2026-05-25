from __future__ import annotations

import importlib.util
import math
from pathlib import Path
from typing import Callable, Dict

from PyQt5.QtCore import QThread, pyqtSignal

from _backend.interface import BackendInterface, BackendRuntimeConfig


class _XcpThread(QThread):
    data = pyqtSignal(dict)
    output = pyqtSignal(dict)
    status = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, config: BackendRuntimeConfig, project_root: Path, parent=None):
        super().__init__(parent)
        self.config = config
        self.project_root = Path(project_root)
        self._running = False
        self._calculate = self._load_model(config.model_path)

    def _load_model(self, model_path: str) -> Callable[[Dict[str, float]], Dict[str, float]]:
        path = Path(model_path) if model_path else self.project_root / "assets" / "mock_models" / "demo_model.py"
        if not path.exists():
            return lambda inputs: {"model4": 0.0, "ecu_write_value": 0.0}
        spec = importlib.util.spec_from_file_location("demo_model", str(path))
        if spec is None or spec.loader is None:
            return lambda inputs: {"model4": 0.0, "ecu_write_value": 0.0}
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return getattr(module, "calculate")

    def stop(self) -> None:
        self._running = False

    @staticmethod
    def _mock_measurements(tick: int) -> Dict[str, float]:
        t = float(tick)
        return {
            "signal1": 82.0 + 8.0 * math.sin(t / 12.0),
            "signal2": 4.2 + 1.4 * math.sin(t / 15.0 + 0.4),
            "signal3": 0.14 + 0.035 * math.sin(t / 10.0 + 1.0),
            "signal4": 0.88 - 0.18 * math.exp(-((t - 80.0) / 18.0) ** 2),
            "signal5": 46.0 + 12.0 * math.sin(t / 19.0),
            "signal6": 0.33 + 0.17 * math.sin(t / 11.0 + 0.7),
        }

    def run(self) -> None:
        self._running = True
        self.status.emit("Mock XCP/CAN-FD replay running")
        tick = 0
        cycle_ms = max(10, int(self.config.cycle_ms or 16))
        names = self.config.measurement_names or [f"signal{i}" for i in range(1, 7)]
        while self._running:
            sample = self._mock_measurements(tick)
            filtered = {name: round(float(sample.get(name, 0.0)), 4) for name in names}
            try:
                out = {k: round(float(v), 4) for k, v in self._calculate(filtered).items()}
            except Exception as exc:  # portfolio demo safety
                self.error.emit(f"model error: {exc}")
                out = {"model4": 0.0, "ecu_write_value": 0.0, "signal7": 0.0, "signal8": 0.0}
            self.data.emit(filtered)
            self.output.emit(out)
            tick += 1
            self.msleep(cycle_ms)
        self.status.emit("Mock XCP/CAN-FD replay stopped")


class PythonXcpBackend(BackendInterface):
    def __init__(self, project_root, parent=None):
        super().__init__(parent)
        self.project_root = Path(project_root)
        self._thread = None

    def start(self, config: BackendRuntimeConfig) -> None:
        if self.is_running():
            return
        self._thread = _XcpThread(config, self.project_root)
        self._thread.data.connect(self.signals.data_received)
        self._thread.output.connect(self.signals.model_output)
        self._thread.status.connect(self.signals.status_changed)
        self._thread.error.connect(self.signals.error)
        self._thread.finished.connect(self.signals.stopped)
        self._thread.start()

    def stop(self) -> None:
        if self._thread:
            self._thread.stop()
            self._thread.wait(1500)
            self._thread = None

    def is_running(self) -> bool:
        return self._thread is not None and self._thread.isRunning()
