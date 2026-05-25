from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List

_ENTRY_RE = re.compile(
    r"/begin\s+(MEASUREMENT|CHARACTERISTIC)\s+(\w+)\s+\"([^\"]*)\"(?P<body>.*?)/end\s+\1",
    re.S,
)
_ADDR_RE = re.compile(r"(?:ECU_ADDRESS\s+|VALUE\s+)(0x[0-9A-Fa-f]+)")
_UNIT_RE = re.compile(r"PHYS_UNIT\s+\"([^\"]+)\"")
_SYMBOL_RE = re.compile(r"SYMBOL_LINK\s+\"([^\"]+)\"")
_SETTING_RE = re.compile(r"MOCK_SETTING\s+\"([^\"]+)\"")
_RANGE_RE = re.compile(r"MOCK_RANGE\s+\"([^\"]+)\"")
_KNOWN_TYPES = ["FLOAT32_IEEE", "SLONG", "ULONG", "UWORD", "SWORD", "UBYTE", "SBYTE", "FLOAT"]


def _first_datatype(block: str) -> str:
    tokens = re.split(r"\s+", block.replace('"', ' '))
    for token in tokens:
        if token in _KNOWN_TYPES:
            return token
    return "UNKNOWN"


def parse_a2l(path: Path) -> Dict[str, List[Dict]]:
    """Parse the small public mock A2L subset used by the demo UI.

    The parser intentionally supports only a tiny safe subset: MEASUREMENT,
    CHARACTERISTIC, ECU_ADDRESS/VALUE, PHYS_UNIT, SYMBOL_LINK, and mock-only
    display metadata. It is not a production A2L parser.
    """

    text = Path(path).read_text(encoding="utf-8", errors="ignore")
    measurements: List[Dict] = []
    characteristics: List[Dict] = []
    for index, match in enumerate(_ENTRY_RE.finditer(text), start=1):
        kind, name, desc = match.group(1), match.group(2), match.group(3)
        block = match.group(0)
        addr = _ADDR_RE.search(block)
        unit = _UNIT_RE.search(block)
        symbol = _SYMBOL_RE.search(block)
        setting = _SETTING_RE.search(block)
        range_text = _RANGE_RE.search(block)
        item = {
            "name": name,
            "description": desc,
            "type": kind,
            "address": addr.group(1).upper().replace("X", "x") if addr else "0x00000000",
            "ecuAddress": addr.group(1).upper().replace("X", "x") if addr else "0x00000000",
            "unit": unit.group(1) if unit else "",
            "datatype": _first_datatype(block),
            "dataType": _first_datatype(block),
            "variable": symbol.group(1) if symbol else f"mock_symbol_{index:02d}",
            "setting": setting.group(1) if setting else "mock setting",
            "range": range_text.group(1) if range_text else "mock range",
            "symbol": name,
        }
        if kind == "MEASUREMENT":
            measurements.append(item)
        else:
            characteristics.append(item)
    return {"measurements": measurements, "characteristics": characteristics}


def make_converter(datatype: str):
    return lambda raw: float(raw)
