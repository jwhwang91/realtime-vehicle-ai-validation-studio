"""Shared-memory-shaped mock layer.

The original design uses compact control/config/data blocks and seqlock-style
snapshots. This public mock keeps those concepts without mapping OS shared memory.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock
from typing import Dict, List
import json
import time

MAX_SIGNALS = 64
MAX_NAME_LEN = 43


@dataclass
class ControlBlock:
    command: str = "IDLE"
    run_state: str = "STOPPED"
    backend_status: str = "READY"
    tick_count: int = 0
    jitter_ms: float = 0.0
    status_message: str = "mock backend ready"


@dataclass
class ConfigBlock:
    payload_json: str = "{}"

    def as_dict(self) -> Dict:
        return json.loads(self.payload_json or "{}")


@dataclass
class SignalEntry:
    name: str
    value: float = 0.0
    timestamp: float = 0.0

    def __post_init__(self) -> None:
        if len(self.name) > MAX_NAME_LEN:
            self.name = self.name[:MAX_NAME_LEN]


@dataclass
class ShmSnapshotBlock:
    seq: int = 0
    values: Dict[str, SignalEntry] = field(default_factory=dict)


class SharedMemoryEmulator:
    def __init__(self) -> None:
        self.control = ControlBlock()
        self.config = ConfigBlock()
        self.shm_in = ShmSnapshotBlock()
        self.shm_out = ShmSnapshotBlock()
        self._lock = Lock()

    def configure(self, payload: Dict) -> None:
        with self._lock:
            self.config.payload_json = json.dumps(payload)
            self.control.status_message = "configuration loaded"

    def write_inputs(self, values: Dict[str, float]) -> None:
        with self._lock:
            self.shm_in.seq += 1
            now = time.time()
            self.shm_in.values = {k: SignalEntry(k, float(v), now) for k, v in values.items()}
            self.shm_in.seq += 1

    def read_inputs(self) -> Dict[str, float]:
        with self._lock:
            return {k: v.value for k, v in self.shm_in.values.items()}

    def write_outputs(self, values: Dict[str, float]) -> None:
        with self._lock:
            self.shm_out.seq += 1
            now = time.time()
            self.shm_out.values = {k: SignalEntry(k, float(v), now) for k, v in values.items()}
            self.shm_out.seq += 1

    def read_outputs(self) -> Dict[str, float]:
        with self._lock:
            return {k: v.value for k, v in self.shm_out.values.items()}


def make_config_dict(measurements: List[Dict], characteristics: List[Dict], model_path: str) -> Dict:
    return {
        "transport": "MOCK_CANFD_XCP",
        "daq_cycle_ms": 50,
        "measurements": measurements[:MAX_SIGNALS],
        "characteristics": characteristics[:MAX_SIGNALS],
        "model_path": model_path,
    }
