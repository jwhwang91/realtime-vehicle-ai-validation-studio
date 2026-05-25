from pathlib import Path

from _utility.a2l_parser import parse_a2l
from _utility.elf_utils import load_mock_symbols

ROOT = Path(__file__).resolve().parents[1]


def test_mock_a2l_parse():
    parsed = parse_a2l(ROOT / "assets/mock_a2l/mock_ecu.a2l")
    assert len(parsed["measurements"]) == 6
    assert len(parsed["characteristics"]) == 2
    assert parsed["measurements"][0]["name"] == "signal1"


def test_mock_elf_symbols():
    symbols = load_mock_symbols(ROOT / "assets/mock_elf/mock_ecu_symbols.elf")
    assert "signal1" in symbols
    assert symbols["signal8"]["address"] == "0x10100070"
