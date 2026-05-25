from __future__ import annotations

import os
import platform
import subprocess
from pathlib import Path

from _backend.interface import BackendInterface, BackendRuntimeConfig
from _backend.python.xcp_worker import _XcpThread


class _InferenceThread(_XcpThread):
    """Async mock inference loop.

    This uses QThread and Qt signals so the GUI stays responsive while replay
    data is generated. The C++ source remains buildable as portfolio evidence,
    but the public PyQt demo does not launch an external binary by default.
    """


class CppSharedMemBackend(BackendInterface):
    """Safe public mock bridge for the C++ backend layer.

    The original version tried to launch any built xcp_backend file. A ZIP made
    on Linux can contain a Linux ELF named xcp_backend; launching that on
    Windows is pointless and can trigger OS/native errors. For portfolio use,
    this bridge now defaults to an in-process QThread simulator and only launches
    the external C++ process when E2E_MOCK_LAUNCH_CPP=1 is explicitly set.
    """

    def __init__(self, project_root, parent=None):
        super().__init__(parent)
        self.project_root = Path(project_root)
        self._thread = None
        self._process = None

    def _candidate_exe(self) -> Path | None:
        system = platform.system().lower()
        names = ["xcp_backend.exe"] if system == "windows" else ["xcp_backend"]
        for name in names:
            for rel in [
                Path("_backend/cpp/build/Release") / name,
                Path("_backend/cpp/build/Debug") / name,
                Path("_backend/cpp/build") / name,
            ]:
                path = self.project_root / rel
                if path.exists():
                    return path
        return None

    def _should_launch_external_cpp(self) -> bool:
        return os.environ.get("E2E_MOCK_LAUNCH_CPP", "").strip() == "1"

    def start(self, config: BackendRuntimeConfig) -> None:
        if self.is_running():
            return

        if self._should_launch_external_cpp():
            exe = self._candidate_exe()
            if exe is not None:
                try:
                    self._process = subprocess.Popen(
                        [str(exe), "--mock"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    self.signals.status_changed.emit(f"External C++ mock backend launched: {exe.name}")
                except Exception as exc:
                    self.signals.error.emit(f"could not launch C++ mock backend: {exc}")
            else:
                self.signals.status_changed.emit("External C++ mock backend not found; using Qt async simulator")
        else:
            self.signals.status_changed.emit("Using Qt async simulator; C++ mock source is included for portfolio review")

        self._thread = _InferenceThread(config, self.project_root)
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
        if self._process:
            self._process.terminate()
            try:
                self._process.wait(timeout=1.0)
            except subprocess.TimeoutExpired:
                self._process.kill()
            self._process = None
        self.signals.status_changed.emit("Mock backend stopped")

    def is_running(self) -> bool:
        return self._thread is not None and self._thread.isRunning()
