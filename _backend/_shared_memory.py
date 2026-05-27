"""Public-safe shared-memory-shaped backend bridge.

The original architecture uses a frontend -> backend command/config block and
backend -> frontend data snapshot block.  The command/config block carries the
runtime JSON generated from the current canvas state: XCP settings, selected
MEASUREMENT/CHARACTERISTIC blocks, model files, and canvas edges.

This public mock does not map a real OS shared memory object by default because
that would be platform-specific and unnecessary for a GitHub demo.  Instead, it
keeps the same protocol shape in an in-process SHM emulator:

    PyQt canvas
    -> BackendRuntimeConfig
    -> JSON runtime payload
    -> seqlock-style config block
    -> backend worker reads config
    -> seqlock-style DAQ/model snapshot blocks
    -> PyQt frontend graph update

The C++ mock backend contains a matching ``shm_layout.h`` structure so reviewers
can see how this boundary would map to a production-oriented backend process.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock
from typing import Dict, List, Optional
import json
import time

MAX_SIGNALS = 64
MAX_NAME_LEN = 43
MAX_CONFIG_JSON_BYTES = 32 * 1024


@dataclass
class ControlBlock:
    command: str = "IDLE"
    run_state: str = "STOPPED"
    backend_status: str = "READY"
    tick_count: int = 0
    jitter_ms: float = 0.0
    status_message: str = "mock backend ready"


@dataclass
class JsonConfigBlock:
    """Seqlock-style JSON config block.

    ``seq`` is odd while a writer is updating and even when the payload is
    stable.  Readers retry until they see the same even sequence before/after
    the read.
    """

    seq: int = 0
    payload_json: str = "{}"
    updated_at: float = 0.0

    def write(self, payload: Dict) -> None:
        text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        encoded = text.encode("utf-8")
        if len(encoded) > MAX_CONFIG_JSON_BYTES:
            raise ValueError(f"runtime config JSON too large: {len(encoded)} bytes")
        self.seq += 1  # odd: writer active
        self.payload_json = text
        self.updated_at = time.time()
        self.seq += 1  # even: stable

    def read(self) -> Dict:
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

    def write(self, values: Dict[str, float]) -> None:
        self.seq += 1  # odd: writer active
        now = time.time()
        self.values = {k: SignalEntry(k, float(v), now) for k, v in values.items()}
        self.seq += 1  # even: stable

    def read(self) -> Dict[str, float]:
        return {k: v.value for k, v in self.values.items()}


class SharedMemoryEmulator:
    """In-process mock of the frontend/backend SHM boundary."""

    def __init__(self) -> None:
        self.control = ControlBlock()
        self.config = JsonConfigBlock()
        self.shm_in = ShmSnapshotBlock()   # backend -> frontend measurements
        self.shm_out = ShmSnapshotBlock()  # backend -> frontend model/STIM outputs
        self._lock = Lock()

    def write_command(self, command: str) -> None:
        with self._lock:
            self.control.command = command
            self.control.status_message = f"command={command}"

    def write_runtime_config(self, payload: Dict) -> None:
        with self._lock:
            self.config.write(payload)
            self.control.status_message = "runtime config JSON written"

    def read_runtime_config(self) -> Dict:
        with self._lock:
            # For this in-process mock the lock already guarantees coherence.
            # The seq field is still updated like a seqlock to mirror the real design.
            return self.config.read()

    def write_inputs(self, values: Dict[str, float]) -> None:
        with self._lock:
            self.shm_in.write(values)
            self.control.tick_count += 1

    def read_inputs(self) -> Dict[str, float]:
        with self._lock:
            return self.shm_in.read()

    def write_outputs(self, values: Dict[str, float]) -> None:
        with self._lock:
            self.shm_out.write(values)

    def read_outputs(self) -> Dict[str, float]:
        with self._lock:
            return self.shm_out.read()

    def set_running(self, running: bool) -> None:
        with self._lock:
            self.control.run_state = "RUNNING" if running else "STOPPED"
            self.control.backend_status = "ONLINE" if running else "READY"


def _compact_signal(entry: Dict) -> Dict:
    """Return only backend-relevant public-safe signal fields."""
    name = entry.get("name", "")
    return {
        "name": name,
        "role": entry.get("type", entry.get("role", "MEASUREMENT")),
        "address": entry.get("address", entry.get("ecuAddress", "0x00000000")),
        "datatype": entry.get("datatype", entry.get("dataType", "UNKNOWN")),
        "unit": entry.get("unit", ""),
        "symbol": entry.get("variable", entry.get("symbol", name)),
        "conversion": entry.get("conversion", "identity"),
    }


def build_runtime_config_payload(config) -> Dict:
    """Serialize the current PyQt canvas/runtime state to backend JSON.

    This is the payload that the Python frontend writes to the SHM config block
    before the backend begins DAQ setup.
    """
    measurements = config.measurement_entries or [
        {"name": name, "type": "MEASUREMENT", "address": "0x00000000", "datatype": "UNKNOWN"}
        for name in config.measurement_names
    ]
    characteristics = config.characteristic_entries or [
        {"name": name, "type": "CHARACTERISTIC", "address": "0x00000000", "datatype": "UNKNOWN"}
        for name in config.output_names
    ]

    payload = {
        "schema": "vehicle_ai_validation_runtime_config.v1",
        "public_mock": True,
        "created_at": time.time(),
        "command": "START",
        "transport": {
            "kind": config.xcp_settings.get("transport", "MOCK_CANFD_XCP"),
            "cycle_ms": int(config.cycle_ms or config.xcp_settings.get("cycle_ms", 50)),
            "hardware_context": "VN-series CAN-FD interface + development ECU in internal prototype; synthetic mock here",
            "a2l_path": config.a2l_path,
            "elf_path": config.elf_path,
            "no_real_channel_settings": True,
        },
        "daq": {
            "measurements": [_compact_signal(s) for s in measurements[:MAX_SIGNALS]],
        },
        "stim": {
            "characteristics": [_compact_signal(s) for s in characteristics[:MAX_SIGNALS]],
        },
        "models": [
            n for n in getattr(config, "canvas_nodes", [])
            if str(n.get("type", "")).upper() == "MODEL"
        ],
        "canvas": {
            "nodes": getattr(config, "canvas_nodes", []),
            "edges": getattr(config, "canvas_edges", []),
        },
    }
    if config.model_path:
        payload["default_model_path"] = config.model_path
    return payload


# Backward compatibility with earlier mock code/tests.
def make_config_dict(measurements: List[Dict], characteristics: List[Dict], model_path: str) -> Dict:
    return {
        "transport": "MOCK_CANFD_XCP",
        "daq_cycle_ms": 50,
        "measurements": measurements[:MAX_SIGNALS],
        "characteristics": characteristics[:MAX_SIGNALS],
        "model_path": model_path,
    }
