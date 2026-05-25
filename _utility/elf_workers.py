from __future__ import annotations

from pathlib import Path

from PyQt5.QtCore import QThread, pyqtSignal

from .elf_utils import load_mock_symbols


class ElfLoaderWorker(QThread):
    loaded = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, elf_path: Path, parent=None):
        super().__init__(parent)
        self.elf_path = Path(elf_path)

    def run(self):
        try:
            self.loaded.emit(load_mock_symbols(self.elf_path))
        except Exception as exc:
            self.error.emit(str(exc))


class A2LUpdateWorker(QThread):
    finished_update = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, entries, elf_path: Path, parent=None):
        super().__init__(parent)
        self.entries = entries
        self.elf_path = Path(elf_path)

    def run(self):
        try:
            symbols = load_mock_symbols(self.elf_path)
            updated = []
            for entry in self.entries:
                item = dict(entry)
                if item.get("name") in symbols:
                    item.update(symbols[item["name"]])
                updated.append(item)
            self.finished_update.emit(updated)
        except Exception as exc:
            self.error.emit(str(exc))
