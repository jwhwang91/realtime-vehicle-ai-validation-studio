from __future__ import annotations

import math
import os
import platform
import subprocess
from pathlib import Path
from typing import Dict

from _backend._shared_memory import SharedMemoryEmulator, build_runtime_config_payload
from _backend.interface import BackendInterface, BackendRuntimeConfig
from _backend.python.xcp_worker import _XcpThread


class _ShmBackedInferenceThread(_XcpThread):
    """Async mock backend loop driven by the SHM runtime config block.

    In the internal architecture, the PyQt frontend serializes the current
    canvas/XCP configuration to JSON and writes it to the command/config SHM
    block.  A C++ backend process reads it, configures DAQ/STIM, then publishes
    realtime measurement/model snapshots through SHM.

    This public demo keeps that exact protocol shape, but uses a safe in-process
    QThread simulator so the GitHub project runs without Vector hardware,
    production A2L/ELF files, or real ECU access.
    """

    def __init__(self, config: BackendRuntimeConfig, project_root: Path, shm: SharedMemoryEmulator, parent=None):
        super().__init__(config, project_root, parent)
        self.shm = shm
        self.runtime_payload = shm.read_runtime_config()

    def run(self) -> None:
        self._running = True
        self.shm.set_running(True)

        transport = self.runtime_payload.get("transport", {})
        daq = self.runtime_payload.get("daq", {})
        stim = self.runtime_payload.get("stim", {})
        measurements = daq.get("measurements", [])
        characteristics = stim.get("characteristics", [])
        names = [s.get("name") for s in measurements if s.get("name")]
        if not names:
            names = self.config.measurement_names or [f"signal{i}" for i in range(1, 7)]

        cycle_ms = max(10, int(transport.get("cycle_ms") or self.config.cycle_ms or 16))
        self.status.emit(
            "SHM runtime config accepted: "
            f"{len(measurements)} DAQ / {len(characteristics)} STIM / "
            f"{len(self.runtime_payload.get('canvas', {}).get('edges', []))} canvas edges"
        )
        self.status.emit("Public mock backend running from SHM config block; no real ECU access")

        tick = 0
        while self._running:
            sample = self._mock_measurements(tick)
            filtered = {name: round(float(sample.get(name, 0.0)), 4) for name in names}
            self.shm.write_inputs(filtered)

            try:
                out = {k: round(float(v), 4) for k, v in self._calculate(filtered).items()}
            except Exception as exc:
                self.error.emit(f"model error: {exc}")
                out = {"model4": 0.0, "ecu_write_value": 0.0, "signal7": 0.0, "signal8": 0.0}

            # In the internal architecture, these values would be consumed by a
            # backend STIM/write path and reflected to the frontend via SHM.
            self.shm.write_outputs(out)
            self.data.emit(self.shm.read_inputs())
            self.output.emit(self.shm.read_outputs())
            tick += 1
            self.msleep(cycle_ms)

        self.shm.write_command("STOP")
        self.shm.set_running(False)
        self.status.emit("SHM-backed public mock backend stopped")


class CppSharedMemBackend(BackendInterface):
    """Public-safe bridge for the C++ backend architecture.

    Important distinction:
      - The real architecture is: PyQt frontend writes JSON config to SHM,
        C++ backend reads it, configures DAQ/STIM, and publishes realtime data
        back through SHM.
      - This public repo defaults to an in-process SHM emulator so it can run
        without Vector hardware or real ECU/A2L/ELF assets.
      - The buildable C++ mock source remains in ``_backend/cpp`` to show the
        production-oriented backend boundary.
    """

    def __init__(self, project_root, parent=None):
        super().__init__(parent)
        self.project_root = Path(project_root)
        self._thread = None
        self._process = None
        self._shm = SharedMemoryEmulator()

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

        runtime_payload = build_runtime_config_payload(config)
        self._shm.write_runtime_config(runtime_payload)
        self._shm.write_command("START")

        daq_count = len(runtime_payload.get("daq", {}).get("measurements", []))
        stim_count = len(runtime_payload.get("stim", {}).get("characteristics", []))
        model_count = len(runtime_payload.get("models", []))
        edge_count = len(runtime_payload.get("canvas", {}).get("edges", []))
        self.signals.status_changed.emit(
            "Frontend wrote runtime JSON to SHM config block: "
            f"DAQ={daq_count}, STIM={stim_count}, models={model_count}, edges={edge_count}"
        )

        if self._should_launch_external_cpp():
            exe = self._candidate_exe()
            if exe is not None:
                try:
                    self._process = subprocess.Popen(
                        [str(exe), "--mock-shm"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    self.signals.status_changed.emit(f"External C++ mock backend launched: {exe.name}")
                except Exception as exc:
                    self.signals.error.emit(f"could not launch C++ mock backend: {exc}")
            else:
                self.signals.status_changed.emit("External C++ mock backend not found; using SHM QThread simulator")
        else:
            self.signals.status_changed.emit(
                "Using in-process SHM emulator; C++ mock source shows the matching process boundary"
            )

        self._thread = _ShmBackedInferenceThread(config, self.project_root, self._shm)
        self._thread.data.connect(self.signals.data_received)
        self._thread.output.connect(self.signals.model_output)
        self._thread.status.connect(self.signals.status_changed)
        self._thread.error.connect(self.signals.error)
        self._thread.finished.connect(self.signals.stopped)
        self._thread.start()

    def stop(self) -> None:
        self._shm.write_command("STOP")
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
        self._shm.set_running(False)
        self.signals.status_changed.emit("Mock backend stopped")

    def is_running(self) -> bool:
        return self._thread is not None and self._thread.isRunning()
