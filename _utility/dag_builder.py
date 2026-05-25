from __future__ import annotations

from typing import Dict, Iterable, List


def build_input_groups(measurements: Iterable[Dict], max_payload_bytes: int = 64) -> List[Dict]:
    """Group mock measurements into CAN-FD-like ODT chunks.

    Each FLOAT32 signal is treated as 4 bytes. This is a public-safe approximation
    used only for UI/backend demo configuration.
    """
    groups = []
    current = {"odt_id": 0, "signals": [], "payload_bytes": 0}
    for sig in measurements:
        if current["payload_bytes"] + 4 > max_payload_bytes:
            groups.append(current)
            current = {"odt_id": len(groups), "signals": [], "payload_bytes": 0}
        current["signals"].append(sig)
        current["payload_bytes"] += 4
    if current["signals"]:
        groups.append(current)
    return groups


def build_output_sigs(characteristics: Iterable[Dict]) -> List[Dict]:
    return [{**sig, "writable": True, "transport": "MOCK_STIM"} for sig in characteristics]
