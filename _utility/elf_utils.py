from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, Optional

_SYMBOL_RE = re.compile(rb"SYMBOL\s+(\w+)\s+(0x[0-9A-Fa-f]+)\s+(\w+)")
_PLAIN_RE = re.compile(rb"^(0x[0-9A-Fa-f]+)\s+(\w+)\s+(\w+).*$", re.M)


def load_mock_symbols(path: Path) -> Dict[str, Dict[str, str]]:
    """Load a public mock symbol map.

    Supports both legacy lines:
        SYMBOL VehSpd_kph 0x70001000 FLOAT32_IEEE
    and the current public mock lines:
        0x10100000 mock_symbol_01 signal1
    """

    data = Path(path).read_bytes()
    symbols: Dict[str, Dict[str, str]] = {}
    for name, addr, dtype in _SYMBOL_RE.findall(data):
        symbols[name.decode()] = {"address": addr.decode(), "datatype": dtype.decode(), "variable": name.decode()}
    for addr, variable, signal in _PLAIN_RE.findall(data):
        symbols[signal.decode()] = {
            "address": addr.decode(),
            "datatype": "MOCK",
            "variable": variable.decode(),
        }
    return symbols


def resolve_symbol_link(path: Path, symbol_name: str) -> Optional[Dict[str, str]]:
    return load_mock_symbols(path).get(symbol_name)


def update_a2l_addresses_from_mock_elf(a2l_entries, elf_path: Path):
    symbols = load_mock_symbols(elf_path)
    updated = []
    for entry in a2l_entries:
        new_entry = dict(entry)
        if entry.get("name") in symbols:
            new_entry.update(symbols[entry["name"]])
        updated.append(new_entry)
    return updated
