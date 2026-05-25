from __future__ import annotations

from pathlib import Path

from PyQt5.QtCore import Qt

from PyQt5.QtWidgets import (
    QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QSpinBox, QVBoxLayout, QWidget
)


def _prepare_dialog(dialog: QDialog, min_width: int = 640) -> None:
    dialog.setMinimumWidth(min_width)
    dialog.setStyleSheet(
        "QDialog { background:#11151D; color:#E7EBF4; }"
        "QLabel { color:#E7EBF4; }"
        "QLineEdit, QSpinBox { min-height:26px; padding:4px 7px; background:#0E1219; color:#D8DCE4; border:1px solid #30384A; border-radius:6px; }"
        "QPushButton { min-height:26px; padding:4px 10px; border:1px solid #384154; background:#1E2432; color:#E6EBF5; border-radius:6px; font-weight:700; }"
    )


def _configure_form(layout: QFormLayout) -> None:
    layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
    layout.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
    layout.setFormAlignment(Qt.AlignTop)
    layout.setHorizontalSpacing(14)
    layout.setVerticalSpacing(10)


class FileSettingsDialog(QDialog):
    def __init__(self, project_root: Path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Mock File Settings")
        _prepare_dialog(self, 700)
        self.project_root = Path(project_root)
        self.a2l_edit = QLineEdit(str(self.project_root / "assets/mock_a2l/mock_ecu.a2l"))
        self.elf_edit = QLineEdit(str(self.project_root / "assets/mock_elf/mock_ecu_symbols.elf"))
        self.model_edit = QLineEdit(str(self.project_root / "assets/mock_models/demo_model.py"))
        layout = QFormLayout(self)
        _configure_form(layout)
        layout.addRow("Mock A2L", self._with_browse(self.a2l_edit, "A2L files (*.a2l);;All files (*)"))
        layout.addRow("Mock ELF", self._with_browse(self.elf_edit, "ELF files (*.elf);;All files (*)"))
        layout.addRow("Mock Model", self._with_browse(self.model_edit, "Python files (*.py);;ONNX models (*.onnx);;All files (*)"))
        box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        box.accepted.connect(self.accept)
        box.rejected.connect(self.reject)
        layout.addRow(box)

    def _with_browse(self, edit, filter_text):
        wrap = QHBoxLayout()
        btn = QPushButton("Browse")
        btn.clicked.connect(lambda: self._browse(edit, filter_text))
        wrap.addWidget(edit)
        wrap.addWidget(btn)
        holder = QWidget()
        holder.setLayout(wrap)
        edit.setMinimumWidth(420)
        return holder

    def _browse(self, edit, filter_text):
        path, _ = QFileDialog.getOpenFileName(self, "Select mock file", str(self.project_root), filter_text)
        if path:
            edit.setText(path)

    def values(self):
        return {
            "a2l_path": self.a2l_edit.text(),
            "elf_path": self.elf_edit.text(),
            "model_path": self.model_edit.text(),
        }


class XcpSettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Mock XCP/CAN-FD Settings")
        _prepare_dialog(self, 560)
        self.channel = QLineEdit("MOCK_CANFD_CH0")
        self.arbitration_bitrate = QLineEdit("500000")
        self.data_bitrate = QLineEdit("2000000")
        self.cycle = QSpinBox()
        self.cycle.setRange(10, 1000)
        self.cycle.setValue(50)
        layout = QFormLayout(self)
        _configure_form(layout)
        layout.addRow("Channel", self.channel)
        layout.addRow("Arbitration bitrate", self.arbitration_bitrate)
        layout.addRow("Data bitrate", self.data_bitrate)
        layout.addRow("DAQ cycle [ms]", self.cycle)
        box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        box.accepted.connect(self.accept)
        box.rejected.connect(self.reject)
        layout.addRow(box)

    def values(self):
        return {"cycle_ms": self.cycle.value()}


class ModelBlockDialog(QDialog):
    """Configure a public-safe mock model block.

    Double-clicking a MODEL block opens this dialog.  It intentionally only stores
    a local .py/.onnx path plus input/output dimensions; it never executes the
    selected model in this portfolio mock.
    """

    def __init__(self, project_root: Path, current_meta: dict | None = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configure Mock Model Block")
        _prepare_dialog(self, 720)
        self.project_root = Path(project_root)
        current_meta = current_meta or {}

        self.path_edit = QLineEdit(str(current_meta.get("model_path", "")))
        self.path_edit.setPlaceholderText("Select .py script or .onnx model, or leave empty for placeholder block")

        self.input_spin = QSpinBox()
        self.input_spin.setRange(1, 64)
        self.input_spin.setValue(int(current_meta.get("input_count", 1) or 1))

        self.output_spin = QSpinBox()
        self.output_spin.setRange(1, 64)
        self.output_spin.setValue(int(current_meta.get("output_count", 1) or 1))

        hint = QLabel(
            "This public mock only records model metadata. It does not run proprietary model logic."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color:#9DA7B9; padding:4px 0;")

        layout = QFormLayout(self)
        _configure_form(layout)
        layout.addRow("Model file", self._with_browse())
        layout.addRow("Input ports", self.input_spin)
        layout.addRow("Output ports", self.output_spin)
        layout.addRow(hint)

        box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        box.accepted.connect(self.accept)
        box.rejected.connect(self.reject)
        layout.addRow(box)

    def _with_browse(self):
        wrap = QHBoxLayout()
        btn = QPushButton("Browse")
        btn.clicked.connect(self._browse_model)
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(lambda: self.path_edit.setText(""))
        wrap.addWidget(self.path_edit)
        wrap.addWidget(btn)
        wrap.addWidget(clear_btn)
        holder = QWidget()
        holder.setLayout(wrap)
        self.path_edit.setMinimumWidth(430)
        return holder

    def _browse_model(self):
        start = self.project_root / "assets/mock_models"
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select mock AI model",
            str(start if start.exists() else self.project_root),
            "AI model files (*.py *.onnx);;Python script (*.py);;ONNX model (*.onnx);;All files (*)",
        )
        if path:
            self.path_edit.setText(path)

    def values(self):
        path = self.path_edit.text().strip()
        title = Path(path).name if path else "empty_model"
        return {
            "model_path": path,
            "model_name": title,
            "input_count": self.input_spin.value(),
            "output_count": self.output_spin.value(),
        }
