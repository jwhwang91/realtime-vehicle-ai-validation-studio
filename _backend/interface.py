from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from PyQt5.QtCore import QObject, pyqtSignal


class BackendSignals(QObject):
    status_changed = pyqtSignal(str)
    data_received = pyqtSignal(dict)
    model_output = pyqtSignal(dict)
    error = pyqtSignal(str)
    stopped = pyqtSignal()


@dataclass
class BackendRuntimeConfig:
    measurement_names: List[str] = field(default_factory=list)
    output_names: List[str] = field(default_factory=list)
    a2l_path: str = ""
    elf_path: str = ""
    model_path: str = ""
    cycle_ms: int = 50


class BackendInterface(QObject):
    """Qt-compatible backend base class.

    Do not inherit from ``abc.ABC`` together with QObject. PyQt's metaclass and
    ABCMeta conflict on some Python/PyQt builds. Subclasses still expose the
    same contract: start(), stop(), and is_running().
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.signals = BackendSignals()

    def start(self, config: BackendRuntimeConfig) -> None:
        raise NotImplementedError

    def stop(self) -> None:
        raise NotImplementedError

    def is_running(self) -> bool:
        raise NotImplementedError

    def set_daq_running(self, enabled: bool) -> None:
        self.signals.status_changed.emit("DAQ running" if enabled else "DAQ paused")

    def wait_for_stop(self, timeout_ms: int = 1500) -> None:
        return None
