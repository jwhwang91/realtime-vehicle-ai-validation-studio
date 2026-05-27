from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

from PyQt5.QtCore import QPoint, QPointF, QRect, Qt, QObject, pyqtSignal
from PyQt5.QtGui import QBrush, QColor, QFontMetrics, QPainter, QPainterPath, QPainterPathStroker, QPen
from PyQt5.QtWidgets import QFrame, QLabel, QScrollArea, QScrollBar, QVBoxLayout, QWidget, QSizePolicy

from .searchable_list import MIME_SIGNAL


_STYLE = {
    "MEASUREMENT": {"header": "#0C5DB8", "role": "ECU IN", "role_color": "#9FD1FF", "port": "#92DDA0"},
    "MODEL": {"header": "#207229", "role": "TimeSeries AI", "role_color": "#9AE6B4", "port": "#92DDA0"},
    "CHARACTERISTIC": {"header": "#D56700", "role": "ECU OUT", "role_color": "#FFE0A6", "port": "#FFD29D"},
    "STRUCT": {"header": "#343D50", "role": "Mock Layer", "role_color": "#CDD6E3", "port": "#92DDA0"},
}


def _label_set_full_text(label: QLabel, text: str) -> None:
    """Store full text separately so visual labels can be elided safely."""
    text = "" if text is None else str(text)
    label.setProperty("full_text", text)
    label.setToolTip(text)
    label.setText(text)


def _label_fit_to_width(label: QLabel) -> None:
    full = str(label.property("full_text") or label.text() or "")
    if not full:
        return
    width = max(24, label.width() - 4)
    metrics = QFontMetrics(label.font())
    label.setText(metrics.elidedText(full, Qt.ElideRight, width))


@dataclass
class EdgeConnection:
    """Independent canvas connection object.

    This replaces the old tuple-based line representation so each edge can keep
    its own source/output port, destination/input port, selected state, and live
    data key for the floating pyqtgraph data-flow monitor.
    """

    edge_id: str
    src_id: str
    src_port: int
    dst_id: str
    dst_port: int
    data_key: str
    label: str
    selected: bool = False
    active: bool = False

    def meta(self) -> dict:
        return {
            "edge_id": self.edge_id,
            "src_id": self.src_id,
            "src_port": self.src_port,
            "dst_id": self.dst_id,
            "dst_port": self.dst_port,
            "data_key": self.data_key,
            "label": self.label,
        }


class NodeWidget(QFrame):
    """Stable QWidget-based Simulink-like block with dynamic ports."""

    def __init__(
        self,
        node_id: str,
        title: str,
        subtitle: str,
        x: int,
        y: int,
        w: int = 130,
        h: int = 72,
        node_type: str = "STRUCT",
        value: str = "0.00",
        meta: Optional[dict] = None,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.node_id = node_id
        self.title = title
        self.subtitle = subtitle
        self.node_type = node_type.upper()
        self.meta = meta or {}
        self._drag_origin: Optional[QPoint] = None
        self._dragging_connection = False
        self._selected = False
        self._connection_kind: Optional[str] = None
        self._connection_port_index: int = 0
        self._font_scale = 1.0
        self._base_height = int(h)
        self.input_count = self._default_input_count()
        self.output_count = self._default_output_count()
        self.input_ports: List[QFrame] = []
        self.output_ports: List[QFrame] = []
        self.setObjectName("canvasNode")
        self.setMinimumSize(w, self._height_for_ports(h))
        self.setFixedSize(w, self._height_for_ports(h))
        self.move(int(x), int(y))
        self.setCursor(Qt.OpenHandCursor)
        self.setMouseTracking(True)
        self.setToolTip(self._tooltip())
        self._build_ui(value)
        self.rebuild_ports(self.input_count, self.output_count)

    def _default_input_count(self) -> int:
        if self.node_type == "MEASUREMENT":
            return 0
        if self.node_type == "MODEL":
            return max(1, int(self.meta.get("input_count", 1) or 1))
        if self.node_type == "CHARACTERISTIC":
            return max(1, int(self.meta.get("input_count", 1) or 1))
        return 0

    def _default_output_count(self) -> int:
        if self.node_type == "STRUCT":
            return 0
        if self.node_type == "MODEL":
            return max(1, int(self.meta.get("output_count", 1) or 1))
        return max(1, int(self.meta.get("output_count", 1) or 1))

    def _height_for_ports(self, base_height: int) -> int:
        max_ports = max(1, int(getattr(self, "input_count", 1)), int(getattr(self, "output_count", 1)))
        # Keep enough vertical room for header, role, title, subtitle and value.
        # The previous compact height clipped text when Windows font rendering was larger.
        if self.node_type == "MODEL":
            return max(base_height, 76 + max_ports * 15)
        if self.node_type == "MEASUREMENT":
            return max(base_height, 88 + max_ports * 6)
        if self.node_type == "CHARACTERISTIC":
            return max(base_height, 94 + max_ports * 10)
        return max(base_height, 72 + max_ports * 10)

    def _tooltip(self) -> str:
        parts = [self.title, self.subtitle]
        if self.meta:
            parts.extend([
                f"Type: {self.meta.get('type', self.node_type)}",
                f"Address: {self.meta.get('address', self.meta.get('ecuAddress', 'mock'))}",
                f"Symbol: {self.meta.get('variable', self.meta.get('symbol', 'mock'))}",
                f"Model: {self.meta.get('model_path', '')}",
                f"Input ports: {self.input_count}",
                f"Output ports: {self.output_count}",
            ])
        return "\n".join(str(p) for p in parts if p)

    def _build_ui(self, value: str) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.header = QLabel()
        self.header.setObjectName("nodeHeader")
        self.header.setFixedHeight(22)
        _label_set_full_text(self.header, self.node_type)
        layout.addWidget(self.header)

        body = QFrame()
        body.setObjectName("nodeBody")
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(8, 4, 8, 4)
        body_layout.setSpacing(0)

        self.role_label = QLabel()
        self.role_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        _label_set_full_text(self.role_label, _STYLE.get(self.node_type, _STYLE["STRUCT"])["role"])
        body_layout.addWidget(self.role_label)

        self.title_label = QLabel()
        self.title_label.setWordWrap(False)
        self.title_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        _label_set_full_text(self.title_label, self.title)
        body_layout.addWidget(self.title_label)

        self.subtitle_label = QLabel()
        self.subtitle_label.setWordWrap(False)
        self.subtitle_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        _label_set_full_text(self.subtitle_label, self.subtitle)
        body_layout.addWidget(self.subtitle_label)

        body_layout.addStretch(1)
        self.value_label = QLabel()
        self.value_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        _label_set_full_text(self.value_label, value)
        body_layout.addWidget(self.value_label)
        layout.addWidget(body, 1)
        self._apply_selected_style(False)
        self.apply_font_scale(self._font_scale)

    def _make_port(self, kind: str, idx: int) -> QFrame:
        style = _STYLE.get(self.node_type, _STYLE["STRUCT"])
        port = QFrame(self)
        port.setObjectName("portIn" if kind == "in" else "portOut")
        port.setFixedSize(10, 10)
        port.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        if kind == "in":
            port.setStyleSheet("QFrame#portIn { background:#9ED7FF; border:1px solid #D9F0FF; border-radius:5px; }")
            port.setToolTip(f"Input port {idx + 1}")
        else:
            port.setStyleSheet(
                f"QFrame#portOut {{ background:{style['port']}; border:1px solid #D5F7DB; border-radius:5px; }}"
            )
            port.setToolTip(f"Output port {idx + 1}")
        port.show()
        return port

    def rebuild_ports(self, input_count: int, output_count: int) -> None:
        for port in self.input_ports + self.output_ports:
            port.setParent(None)
            port.deleteLater()
        self.input_count = max(0, int(input_count))
        self.output_count = max(0, int(output_count))
        self.input_ports = [self._make_port("in", i) for i in range(self.input_count)]
        self.output_ports = [self._make_port("out", i) for i in range(self.output_count)]
        self._layout_ports()
        self.setToolTip(self._tooltip())
        self.update()

    def _layout_ports(self) -> None:
        def place(ports: List[QFrame], side: str) -> None:
            total = len(ports)
            if total <= 0:
                return
            top = 32
            bottom = max(top + 2, self.height() - 18)
            span = max(1, bottom - top)
            for idx, port in enumerate(ports):
                if total == 1:
                    y = self.height() // 2 - 5
                else:
                    y = int(top + (idx + 1) * span / (total + 1) - 5)
                x = -1 if side == "in" else self.width() - 9
                port.move(x, y)
                port.raise_()

        place(self.input_ports, "in")
        place(self.output_ports, "out")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._layout_ports()
        self._refresh_label_fitting()

    def _controller(self) -> Optional["DiagramScene"]:
        parent = self.parentWidget()
        return getattr(parent, "scene_controller", None) if parent else None

    def _apply_selected_style(self, selected: bool) -> None:
        border = "#79B4FF" if selected else "#333742"
        width = 2 if selected else 1
        self.setStyleSheet(
            f"QFrame#canvasNode {{ background:#2D313B; border:{width}px solid {border}; border-radius:10px; }}"
            "QFrame#nodeBody { background:#2D313B; border-bottom-left-radius:9px; border-bottom-right-radius:9px; }"
        )

    def _set_label_font(self, label: QLabel, px_size: int, bold: bool = False) -> None:
        font = label.font()
        font.setPixelSize(max(8, int(px_size)))
        font.setBold(bool(bold))
        label.setFont(font)

    def _refresh_label_fitting(self) -> None:
        for label in (self.header, self.role_label, self.title_label, self.subtitle_label, self.value_label):
            _label_fit_to_width(label)

    def apply_font_scale(self, scale: float) -> None:
        self._font_scale = max(0.78, min(1.18, float(scale)))
        style = _STYLE.get(self.node_type, _STYLE["STRUCT"])

        def px(base: int) -> int:
            return max(8, int(round(base * self._font_scale)))

        self.header.setStyleSheet(
            f"QLabel#nodeHeader {{ background:{style['header']}; color:#F8FBFF; "
            "padding-left:8px; border-top-left-radius:9px; border-top-right-radius:9px; }}"
        )
        self.role_label.setStyleSheet(f"color:{style['role_color']}; background:transparent;")
        self.title_label.setStyleSheet("color:#E7EDF7; background:transparent;")
        self.subtitle_label.setStyleSheet("color:#97A0B2; background:transparent;")
        self.value_label.setStyleSheet("color:#FFFFFF; background:transparent;")

        self._set_label_font(self.header, px(10), True)
        self._set_label_font(self.role_label, px(10), True)
        self._set_label_font(self.title_label, px(10), True)
        self._set_label_font(self.subtitle_label, px(9), False)
        self._set_label_font(self.value_label, px(11), True)
        self._refresh_label_fitting()

    def set_selected(self, selected: bool) -> None:
        self._selected = bool(selected)
        self._apply_selected_style(self._selected)

    def update_value(self, value) -> None:
        if isinstance(value, float):
            text = f"{value:.3f}"
        else:
            text = str(value)
        _label_set_full_text(self.value_label, text)
        _label_fit_to_width(self.value_label)

    def set_io_counts(self, input_count: int, output_count: int) -> None:
        input_count = max(0, int(input_count))
        output_count = max(0, int(output_count))
        self.meta["input_count"] = input_count
        self.meta["output_count"] = output_count
        self.rebuild_ports(input_count, output_count)
        base_h = 96 if self.node_type == "MODEL" else (88 if self.node_type == "CHARACTERISTIC" else 72)
        new_h = self._height_for_ports(base_h)
        if new_h != self.height():
            self.setFixedHeight(new_h)
        self._layout_ports()

    def set_model_config(self, model_path: str = "", input_count: int = 1, output_count: int = 1) -> None:
        model_name = Path(model_path).name if model_path else self.meta.get("name", self.title) or "empty_model"
        self.title = model_name
        self.subtitle = f"IN: {int(input_count)} · OUT: {int(output_count)}"
        self.meta.update({
            "name": model_name,
            "model_path": model_path,
            "input_count": int(input_count),
            "output_count": int(output_count),
            "variable": model_name,
            "symbol": model_name,
        })
        _label_set_full_text(self.title_label, model_name)
        _label_set_full_text(self.subtitle_label, self.subtitle)
        self._refresh_label_fitting()
        self.set_io_counts(int(input_count), int(output_count))
        self.setToolTip(self._tooltip())

    def set_model_file(self, path: str) -> None:
        self.set_model_config(
            path,
            int(self.meta.get("input_count", 1) or 1),
            int(self.meta.get("output_count", 1) or 1),
        )

    def has_input_port(self) -> bool:
        return self.input_count > 0

    def has_output_port(self) -> bool:
        return self.output_count > 0

    def port_center(self, kind: str, index: int = 0) -> QPointF:
        ports = self.output_ports if kind == "out" else self.input_ports
        if ports:
            index = max(0, min(int(index), len(ports) - 1))
            g = ports[index].geometry()
            return QPointF(g.x() + g.width() / 2.0 + self.x(), g.y() + g.height() / 2.0 + self.y())
        if kind == "out":
            return self.center_right()
        return self.center_left()

    def center_right(self) -> QPointF:
        g = self.geometry()
        return QPointF(g.right(), g.y() + g.height() / 2.0)

    def center_left(self) -> QPointF:
        g = self.geometry()
        return QPointF(g.left(), g.y() + g.height() / 2.0)

    def _hit_port(self, pos: QPoint) -> Optional[Tuple[str, int]]:
        hit_pad = 8
        for i, port in enumerate(self.output_ports):
            if port.geometry().adjusted(-hit_pad, -hit_pad, hit_pad, hit_pad).contains(pos):
                return "out", i
        for i, port in enumerate(self.input_ports):
            if port.geometry().adjusted(-hit_pad, -hit_pad, hit_pad, hit_pad).contains(pos):
                return "in", i
        return None

    def mousePressEvent(self, event):
        controller = self._controller()

        if event.button() == Qt.RightButton and controller and controller.connection_preview:
            controller.cancel_connection("Connection canceled.")
            event.accept()
            return

        if event.button() == Qt.LeftButton:
            if controller:
                ctrl = bool(event.modifiers() & Qt.ControlModifier)
                # Simulink-like selection behavior:
                # - Ctrl-click toggles membership in the multi-selection set.
                # - Clicking an already selected block keeps the current group so it can be dragged.
                # - Clicking an unselected block without Ctrl selects only that block.
                if ctrl:
                    controller.toggle_node_selection(self.node_id)
                elif not controller.is_node_selected(self.node_id):
                    controller.select_node(self.node_id)
                else:
                    controller.request_node_info(self.node_id)
                if controller.canvas:
                    controller.canvas.setFocus(Qt.MouseFocusReason)

            hit = self._hit_port(event.pos())
            if controller and controller.connection_preview:
                # Second click completes the connection.  The click must land on a
                # compatible destination port; empty-space clicks keep the preview alive.
                if hit:
                    controller.finish_connection_at(self.mapToParent(event.pos()))
                else:
                    controller.update_connection_preview(self.mapToParent(event.pos()))
                    controller.status_requested.emit("Click a compatible destination port, or press Esc/right-click to cancel.")
                event.accept()
                return

            if hit:
                kind, port_index = hit
                if controller:
                    controller.begin_connection(self.node_id, kind, port_index, self.mapToParent(event.pos()))
                event.accept()
                return

            self._drag_origin = event.pos()
            self.setCursor(Qt.ClosedHandCursor)
            self.raise_()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        controller = self._controller()
        if controller and controller.connection_preview:
            controller.update_connection_preview(self.mapToParent(event.pos()))
            event.accept()
            return
        if self._drag_origin is not None and event.buttons() & Qt.LeftButton:
            new_pos = self.mapToParent(event.pos() - self._drag_origin)
            x = max(0, min(new_pos.x(), max(0, self.parentWidget().width() - self.width())))
            y = max(0, min(new_pos.y(), max(0, self.parentWidget().height() - self.height())))
            delta = QPoint(x - self.x(), y - self.y())
            if controller:
                controller.move_selected_nodes(self.node_id, delta)
            else:
                self.move(x, y)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        # Connections are click-start / click-finish, so releasing the mouse does
        # not complete or cancel the pending wire.
        if self._drag_origin is not None:
            self._drag_origin = None
            self.setCursor(Qt.OpenHandCursor)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            controller = self._controller()
            if controller:
                controller.select_node(self.node_id)
                controller.request_node_info(self.node_id)
                controller.request_node_double_clicked(self.node_id)
            event.accept()
            return
        super().mouseDoubleClickEvent(event)


class CanvasWidget(QFrame):
    def __init__(self, scene: "DiagramScene", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.scene_controller = scene
        self.setObjectName("widgetCanvas")
        self.setAcceptDrops(True)
        self.setFixedSize(1520, 620)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setStyleSheet("QFrame#widgetCanvas { background:#12161F; border:0; }")
        self._font_scale = 1.0
        self._rubber_origin: Optional[QPoint] = None
        self._rubber_rect: QRect = QRect()
        self._rubber_additive = False
        self._rubber_moved = False

    def apply_font_scale(self, scale: float) -> None:
        self._font_scale = max(0.82, min(1.22, float(scale)))
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False)

        painter.setPen(QPen(QColor(255, 255, 255, 18), 1))
        for x in range(0, self.width(), 26):
            painter.drawLine(x, 0, x, self.height())
        for y in range(0, self.height(), 26):
            painter.drawLine(0, y, self.width(), y)

        painter.setRenderHint(QPainter.Antialiasing, True)
        for edge in list(self.scene_controller.edges):
            self._draw_edge(painter, edge)

        preview = self.scene_controller.connection_preview
        if preview:
            start_id, kind, port_index, pt = preview
            node = self.scene_controller.nodes.get(start_id)
            if node:
                a = node.port_center(kind, port_index)
                b = pt
                ppen = QPen(QColor("#FFE000"), 2, Qt.DashLine)
                ppen.setCosmetic(True)
                painter.setPen(ppen)
                self._draw_cubic(painter, a, b)

        if self._rubber_origin is not None and not self._rubber_rect.isNull():
            r = self._rubber_rect.normalized()
            painter.setPen(QPen(QColor("#79B4FF"), 1, Qt.DashLine))
            painter.setBrush(QBrush(QColor(121, 180, 255, 28)))
            painter.drawRect(r)

        self._draw_legend(painter)

    def _draw_edge(self, painter: QPainter, edge: EdgeConnection) -> None:
        path = self.scene_controller.path_for_edge(edge)
        if path.isEmpty():
            return
        is_live = self.scene_controller.edges_active or edge.active
        if edge.selected and not is_live:
            pen = QPen(QColor("#FFE000"), 3)
        else:
            pen = QPen(QColor("#F8FBFF") if is_live else QColor("#7FE18D"), 3 if is_live else 2)
        pen.setCosmetic(True)
        painter.setPen(pen)
        painter.drawPath(path)

    def _draw_cubic(self, painter: QPainter, a: QPointF, b: QPointF) -> None:
        painter.drawPath(self.scene_controller.make_cubic_path(a, b))

    def _draw_legend(self, painter: QPainter) -> None:
        box = QRect(self.width() - 300, 14, 280, 154)
        painter.setPen(QPen(QColor("#333A49"), 1))
        painter.setBrush(QColor("#191F2A"))
        painter.drawRoundedRect(box, 10, 10)
        f = painter.font()
        f.setPointSize(max(8, int(9 * self._font_scale)))
        painter.setFont(f)
        painter.setPen(QColor("#D8E0EE"))
        painter.drawText(box.adjusted(12, 10, -12, -124), Qt.AlignLeft, "Flow Legend")
        painter.setPen(QColor("#A8B1C2"))
        lines = [
            "Independent I/O ports per block",
            "Click output port → click input port",
            "Double-click line → data-flow graph",
            "Esc/right-click → cancel pending wire",
            "Del/Backspace → delete selection",
            "Middle mouse → pan canvas",
            "Running data flow → white lines",
        ]
        for i, text in enumerate(lines):
            painter.drawText(box.adjusted(12, 34 + i * 19, -10, 0), Qt.AlignLeft, text)

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat(MIME_SIGNAL):
            event.acceptProposedAction()
            return
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat(MIME_SIGNAL):
            event.acceptProposedAction()
            return
        super().dragMoveEvent(event)

    def dropEvent(self, event):
        if event.mimeData().hasFormat(MIME_SIGNAL):
            try:
                raw = bytes(event.mimeData().data(MIME_SIGNAL)).decode("utf-8")
                meta = json.loads(raw)
            except Exception:
                event.ignore()
                return
            self.scene_controller.add_signal_node(meta, QPointF(event.pos()))
            event.acceptProposedAction()
            return
        super().dropEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton and self.scene_controller.connection_preview:
            self.scene_controller.cancel_connection("Connection canceled.")
            event.accept()
            return
        if event.button() == Qt.LeftButton:
            if self.scene_controller.connection_preview:
                if not self.scene_controller.finish_connection_at(QPointF(event.pos())):
                    self.scene_controller.status_requested.emit("Click a compatible destination port, or press Esc/right-click to cancel.")
                event.accept()
                return
            edge = self.scene_controller.edge_at_point(QPointF(event.pos()))
            if edge:
                self.scene_controller.select_edge(edge.edge_id)
                self._rubber_origin = None
                self._rubber_rect = QRect()
            else:
                self._rubber_origin = event.pos()
                self._rubber_rect = QRect(event.pos(), event.pos())
                self._rubber_additive = bool(event.modifiers() & Qt.ControlModifier)
                self._rubber_moved = False
            self.setFocus(Qt.MouseFocusReason)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            edge = self.scene_controller.edge_at_point(QPointF(event.pos()))
            if edge:
                self.scene_controller.select_edge(edge.edge_id)
                self.scene_controller.request_edge_flow(edge.edge_id)
                event.accept()
                return
        super().mouseDoubleClickEvent(event)

    def mouseMoveEvent(self, event):
        if self.scene_controller.connection_preview:
            self.scene_controller.update_connection_preview(QPointF(event.pos()))
            event.accept()
            return
        if self._rubber_origin is not None and event.buttons() & Qt.LeftButton:
            self._rubber_rect = QRect(self._rubber_origin, event.pos()).normalized()
            self._rubber_moved = self._rubber_rect.width() > 4 or self._rubber_rect.height() > 4
            self.update()
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        # A wire is committed by the second left-click, not by releasing the mouse.
        if event.button() == Qt.LeftButton and self._rubber_origin is not None:
            rect = self._rubber_rect.normalized()
            moved = self._rubber_moved and rect.width() > 4 and rect.height() > 4
            additive = self._rubber_additive
            self._rubber_origin = None
            self._rubber_rect = QRect()
            self._rubber_moved = False
            if moved:
                self.scene_controller.select_nodes_in_rect(rect, additive=additive)
            elif not additive:
                self.scene_controller.clear_selection()
            self.update()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape and self.scene_controller.connection_preview:
            self.scene_controller.cancel_connection("Connection canceled.")
            event.accept()
            return
        if event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            self.scene_controller.delete_selected_node()
            event.accept()
            return
        super().keyPressEvent(event)


class DiagramScene(QObject):
    """Controller API kept compatible with the previous QGraphicsScene version."""

    node_info_requested = pyqtSignal(dict)
    model_load_requested = pyqtSignal(str, dict)
    edge_flow_requested = pyqtSignal(dict)
    status_requested = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.view: Optional["DiagramView"] = None
        self.canvas: Optional[CanvasWidget] = None
        self.signal_catalog: Dict[str, dict] = {}
        self.nodes: Dict[str, NodeWidget] = {}
        self.node_by_signal: Dict[str, List[NodeWidget]] = {}
        self.edges: List[EdgeConnection] = []
        self.edges_active = False
        self.selected_node_id: Optional[str] = None
        self.selected_node_ids: Set[str] = set()
        self.selected_edge_id: Optional[str] = None
        self.connection_preview: Optional[Tuple[str, str, int, QPointF]] = None
        self._drop_count = 0
        self._model_count = 0
        self._edge_count = 0
        self._font_scale = 1.0

    def bind_canvas(self, canvas: CanvasWidget) -> None:
        self.canvas = canvas
        self.apply_font_scale(self._font_scale)

    def apply_font_scale(self, scale: float) -> None:
        self._font_scale = max(0.82, min(1.22, float(scale)))
        for node in self.nodes.values():
            node.apply_font_scale(self._font_scale)
        if self.canvas:
            self.canvas.apply_font_scale(self._font_scale)

    def set_signal_catalog(self, signals: Iterable[dict]) -> None:
        self.signal_catalog = {s.get("name", ""): dict(s) for s in signals if s.get("name")}
        self.clear()
        self._create_demo_graph()

    def clear(self) -> None:
        for node in list(self.nodes.values()):
            node.setParent(None)
            node.deleteLater()
        self.nodes.clear()
        self.node_by_signal.clear()
        self.edges.clear()
        self.selected_node_id = None
        self.selected_node_ids.clear()
        self.selected_edge_id = None
        self.connection_preview = None
        self._drop_count = 0
        self._model_count = 0
        self._edge_count = 0
        if self.canvas:
            self.canvas.update()

    def clear_user_canvas(self) -> None:
        self.clear()
        if self.canvas:
            self.canvas.update()
        self.status_requested.emit("Canvas cleared. Use A2L drag/drop or Add Model to rebuild the mock graph.")

    def reset_demo_graph(self) -> None:
        self.clear()
        self._create_demo_graph()
        self.status_requested.emit("Demo graph restored.")

    def _meta(self, name: str, kind: str = "MEASUREMENT") -> dict:
        return self.signal_catalog.get(name, {
            "name": name,
            "type": kind,
            "address": "0x00000000",
            "datatype": "MOCK",
            "description": "Synthetic public mock signal",
            "variable": f"mock_{name}",
            "unit": "arb",
        })

    def _subtitle(self, meta: dict) -> str:
        return f"{meta.get('datatype', meta.get('dataType', 'MOCK'))} · {meta.get('address', meta.get('ecuAddress', '0x00000000'))}"

    def _add_node(
        self,
        node_id: str,
        title: str,
        subtitle: str,
        x: int,
        y: int,
        w: int,
        h: int,
        node_type: str,
        value: str = "0.00",
        meta: Optional[dict] = None,
        signal_name: Optional[str] = None,
    ) -> NodeWidget:
        if not self.canvas:
            raise RuntimeError("Canvas is not bound yet")
        node = NodeWidget(node_id, title, subtitle, x, y, w, h, node_type, value, meta, self.canvas)
        node.apply_font_scale(self._font_scale)
        node.show()
        self.nodes[node_id] = node
        if signal_name:
            self.node_by_signal.setdefault(signal_name, []).append(node)
        self.canvas.update()
        return node

    def _connect(self, src_id: str, dst_id: str, src_port: int = 0, dst_port: int = 0) -> bool:
        if src_id == dst_id:
            return False
        if src_id not in self.nodes or dst_id not in self.nodes:
            return False
        src_node = self.nodes[src_id]
        dst_node = self.nodes[dst_id]
        src_port = int(src_port)
        dst_port = int(dst_port)
        if not src_node.has_output_port() or not dst_node.has_input_port():
            return False
        if src_port < 0 or src_port >= src_node.output_count:
            return False
        if dst_port < 0 or dst_port >= dst_node.input_count:
            return False
        # Simulink-style: one source per input port. Pick another input port for another wire.
        if any(e.dst_id == dst_id and e.dst_port == dst_port for e in self.edges):
            return False
        if any(e.src_id == src_id and e.src_port == src_port and e.dst_id == dst_id and e.dst_port == dst_port for e in self.edges):
            return False
        self._edge_count += 1
        data_key = self._edge_data_key(src_node, src_port, dst_node, dst_port)
        label = f"{src_node.title}:out{src_port + 1} → {dst_node.title}:in{dst_port + 1}"
        edge = EdgeConnection(f"edge_{self._edge_count}", src_id, src_port, dst_id, dst_port, data_key, label)
        self.edges.append(edge)
        if self.canvas:
            self.canvas.update()
        return True

    def _edge_data_key(self, src_node: NodeWidget, src_port: int, dst_node: NodeWidget, dst_port: int) -> str:
        if dst_node.node_type == "CHARACTERISTIC":
            return dst_node.meta.get("name") or "ecu_write_value"
        if src_node.node_type in {"MEASUREMENT", "CHARACTERISTIC"}:
            return src_node.meta.get("name") or src_node.title
        if src_node.node_id == "model1":
            return "model1_a" if src_port == 0 else "model1_b"
        if src_node.node_id in {"model2", "model3", "model4"}:
            return src_node.node_id
        safe_title = (src_node.title or src_node.node_id).replace(".", "_").replace(" ", "_")
        return f"{safe_title}_out{src_port + 1}"

    def _create_demo_graph(self) -> None:
        measurements = ["signal1", "signal2", "signal3", "signal4", "signal5", "signal6"]
        y0 = 82
        for idx, name in enumerate(measurements, start=1):
            meta = self._meta(name, "MEASUREMENT")
            self._add_node(f"m{idx}", name, self._subtitle(meta), 120, y0 + (idx - 1) * 94, 150, 90, "MEASUREMENT", "0.00", meta, name)

        self._add_node("model1", "timeseriesAI_model1.py", "IN: 6 · OUT: 2", 420, 170, 190, 166, "MODEL", "0.000 / 0.000", self._model_meta("timeseriesAI_model1.py", "", 6, 2))
        self._add_node("model2", "timeseriesAI_model2.py", "IN: 1 · OUT: 1", 740, 150, 174, 108, "MODEL", "0.00", self._model_meta("timeseriesAI_model2.py", "", 1, 1))
        self._add_node("model3", "timeseriesAI_model3.py", "IN: 1 · OUT: 1", 740, 330, 174, 108, "MODEL", "0.00", self._model_meta("timeseriesAI_model3.py", "", 1, 1))
        self._add_node("model4", "timeseriesAI_model4.py", "IN: 2 · OUT: 1", 1048, 245, 174, 112, "MODEL", "0.00", self._model_meta("timeseriesAI_model4.py", "", 2, 1))
        char_meta = self._meta("signal7", "CHARACTERISTIC")
        char_meta = dict(char_meta)
        char_meta.setdefault("input_count", 1)
        char_meta.setdefault("output_count", 1)
        self._add_node("characteristic", "ecu_write_value", "VALUE · 0xB004342B", 1340, 252, 174, 100, "CHARACTERISTIC", "0.00", char_meta, "signal7")

        for idx in range(1, 7):
            self._connect(f"m{idx}", "model1", 0, idx - 1)
        self._connect("model1", "model2", 0, 0)
        self._connect("model1", "model3", 1, 0)
        self._connect("model2", "model4", 0, 0)
        self._connect("model3", "model4", 0, 1)
        self._connect("model4", "characteristic", 0, 0)

    def _model_meta(self, name: str, path: str = "", input_count: int = 1, output_count: int = 1) -> dict:
        return {
            "name": name,
            "type": "MODEL",
            "description": "Mock TimeSeries AI stage. Double-click to select a .py script or ONNX model and configure I/O counts.",
            "model_path": path,
            "input_count": int(input_count),
            "output_count": int(output_count),
            "datatype": "PY/ONNX",
            "address": "N/A",
            "variable": name,
            "unit": "model output",
            "setting": "mock local file" if path else "empty placeholder block",
            "range": "synthetic",
            "symbol": name,
        }

    def add_signal_node(self, meta: dict, pos: Optional[QPointF] = None):
        name = meta.get("name", "dropped_signal")
        kind = meta.get("type", "MEASUREMENT").upper()
        pos = pos or QPointF(80 + 20 * self._drop_count, 80 + 20 * self._drop_count)
        self._drop_count += 1
        node_id = f"drop_{self._drop_count}_{name}"
        if kind == "CHARACTERISTIC":
            meta = dict(meta)
            meta.setdefault("input_count", 1)
            meta.setdefault("output_count", 1)
            node = self._add_node(node_id, name, self._subtitle(meta), int(pos.x()), int(pos.y()), 150, 88, "CHARACTERISTIC", "0.00", meta, name)
        else:
            meta = dict(meta)
            meta.setdefault("output_count", 1)
            node = self._add_node(node_id, name, self._subtitle(meta), int(pos.x()), int(pos.y()), 130, 72, "MEASUREMENT", "0.00", meta, name)
        self.select_node(node_id)
        self.request_node_info(node_id)
        return node

    def add_model_node(
        self,
        model_path: str = "",
        pos: Optional[QPointF] = None,
        input_count: int = 1,
        output_count: int = 1,
        title: Optional[str] = None,
    ) -> NodeWidget:
        self._model_count += 1
        if title is None:
            title = Path(model_path).name if model_path else f"empty_model_{self._model_count}"
        pos = pos or QPointF(520 + self._model_count * 30, 110 + self._model_count * 35)
        node_id = f"model_custom_{self._model_count}"
        subtitle = f"IN: {int(input_count)} · OUT: {int(output_count)}"
        node = self._add_node(
            node_id,
            title,
            subtitle,
            int(pos.x()),
            int(pos.y()),
            186,
            112,
            "MODEL",
            "0.00",
            self._model_meta(title, model_path, input_count, output_count),
        )
        self.select_node(node_id)
        self.request_node_info(node_id)
        self.status_requested.emit(f"Added empty model block: {title}")
        return node

    def configure_model_node(self, node_id: str, config: dict) -> None:
        node = self.nodes.get(node_id)
        if not node or node.node_type != "MODEL":
            return
        model_path = str(config.get("model_path", "") or "")
        input_count = int(config.get("input_count", node.meta.get("input_count", 1)) or 1)
        output_count = int(config.get("output_count", node.meta.get("output_count", 1)) or 1)
        title = Path(model_path).name if model_path else str(config.get("model_name", node.title) or node.title)
        node.set_model_config(model_path, input_count, output_count)
        node.title = title
        _label_set_full_text(node.title_label, title)
        node._refresh_label_fitting()
        node.meta.update(self._model_meta(title, model_path, input_count, output_count))
        self._prune_invalid_edges_for_node(node_id)
        self.request_node_info(node_id)
        if model_path:
            self.status_requested.emit(f"Configured model block {node_id}: {title} / IN {input_count} / OUT {output_count}")
        else:
            self.status_requested.emit(f"Configured empty model block {node_id}: IN {input_count} / OUT {output_count}")
        if self.canvas:
            self.canvas.update()

    def _prune_invalid_edges_for_node(self, node_id: str) -> None:
        node = self.nodes.get(node_id)
        if not node:
            return
        self.edges = [
            e for e in self.edges
            if not (
                (e.src_id == node_id and e.src_port >= node.output_count)
                or (e.dst_id == node_id and e.dst_port >= node.input_count)
            )
        ]

    def load_model_for_node(self, node_id: str, model_path: str) -> None:
        node = self.nodes.get(node_id)
        if not node or node.node_type != "MODEL":
            return
        self.configure_model_node(
            node_id,
            {
                "model_path": model_path,
                "input_count": int(node.meta.get("input_count", 1) or 1),
                "output_count": int(node.meta.get("output_count", 1) or 1),
            },
        )

    def is_node_selected(self, node_id: str) -> bool:
        return node_id in self.selected_node_ids

    def _apply_node_selection_styles(self) -> None:
        for nid, node in self.nodes.items():
            node.set_selected(nid in self.selected_node_ids)
        if self.canvas:
            self.canvas.update()

    def select_node(self, node_id: Optional[str], additive: bool = False) -> None:
        if node_id not in self.nodes:
            if not additive:
                self.selected_node_ids.clear()
                self.selected_node_id = None
                self._apply_node_selection_styles()
            return
        if not additive:
            self.selected_node_ids = {node_id}
        else:
            self.selected_node_ids.add(node_id)
        self.selected_node_id = node_id
        if self.selected_node_ids:
            self.selected_edge_id = None
            for edge in self.edges:
                edge.selected = False
        self._apply_node_selection_styles()
        self.request_node_info(node_id)

    def toggle_node_selection(self, node_id: str) -> None:
        if node_id not in self.nodes:
            return
        if node_id in self.selected_node_ids:
            self.selected_node_ids.remove(node_id)
            if self.selected_node_id == node_id:
                self.selected_node_id = next(iter(self.selected_node_ids), None)
        else:
            self.selected_node_ids.add(node_id)
            self.selected_node_id = node_id
        if self.selected_node_ids:
            self.selected_edge_id = None
            for edge in self.edges:
                edge.selected = False
        self._apply_node_selection_styles()
        if self.selected_node_id:
            self.request_node_info(self.selected_node_id)
        self.status_requested.emit(f"Selected {len(self.selected_node_ids)} block(s).")

    def select_nodes_in_rect(self, rect: QRect, additive: bool = False) -> None:
        rect = rect.normalized()
        hits = [node_id for node_id, node in self.nodes.items() if rect.intersects(node.geometry())]
        if additive:
            self.selected_node_ids.update(hits)
        else:
            self.selected_node_ids = set(hits)
        self.selected_node_id = hits[-1] if hits else (next(iter(self.selected_node_ids), None) if self.selected_node_ids else None)
        if self.selected_node_ids:
            self.selected_edge_id = None
            for edge in self.edges:
                edge.selected = False
        self._apply_node_selection_styles()
        if self.selected_node_id:
            self.request_node_info(self.selected_node_id)
        self.status_requested.emit(f"Area selected {len(hits)} block(s). Total selected: {len(self.selected_node_ids)}.")

    def move_selected_nodes(self, dragged_node_id: str, delta: QPoint) -> None:
        if dragged_node_id not in self.nodes:
            return
        if dragged_node_id not in self.selected_node_ids:
            self.select_node(dragged_node_id)
        if delta.x() == 0 and delta.y() == 0:
            return
        if not self.canvas:
            return
        selected = [self.nodes[nid] for nid in self.selected_node_ids if nid in self.nodes]
        if not selected:
            return
        # Clamp the group as a group so blocks do not split apart at canvas edges.
        min_x = min(n.x() for n in selected)
        min_y = min(n.y() for n in selected)
        max_x = max(n.x() + n.width() for n in selected)
        max_y = max(n.y() + n.height() for n in selected)
        dx = max(-min_x, min(delta.x(), self.canvas.width() - max_x))
        dy = max(-min_y, min(delta.y(), self.canvas.height() - max_y))
        for node in selected:
            node.move(node.x() + dx, node.y() + dy)
        if self.canvas:
            self.canvas.update()

    def select_edge(self, edge_id: Optional[str]) -> None:
        self.selected_edge_id = edge_id
        self.selected_node_id = None
        self.selected_node_ids.clear()
        for node in self.nodes.values():
            node.set_selected(False)
        for edge in self.edges:
            edge.selected = edge.edge_id == edge_id
        if self.canvas:
            self.canvas.update()

    def clear_selection(self) -> None:
        self.selected_node_id = None
        self.selected_node_ids.clear()
        self.selected_edge_id = None
        for node in self.nodes.values():
            node.set_selected(False)
        for edge in self.edges:
            edge.selected = False
        if self.canvas:
            self.canvas.update()

    def delete_selected_node(self) -> None:
        if self.selected_edge_id:
            edge_id = self.selected_edge_id
            self.edges = [e for e in self.edges if e.edge_id != edge_id]
            self.selected_edge_id = None
            self.status_requested.emit(f"Deleted connection: {edge_id}")
            if self.canvas:
                self.canvas.update()
            return
        node_ids = [nid for nid in self.selected_node_ids if nid in self.nodes]
        if not node_ids and self.selected_node_id in self.nodes:
            node_ids = [self.selected_node_id]
        if not node_ids:
            return
        titles = []
        for node_id in node_ids:
            node = self.nodes.pop(node_id, None)
            if not node:
                continue
            titles.append(node.title)
            node.setParent(None)
            node.deleteLater()
        remove_ids = set(node_ids)
        self.edges = [e for e in self.edges if e.src_id not in remove_ids and e.dst_id not in remove_ids]
        for sig, entries in list(self.node_by_signal.items()):
            self.node_by_signal[sig] = [n for n in entries if n.node_id not in remove_ids]
            if not self.node_by_signal[sig]:
                self.node_by_signal.pop(sig, None)
        self.selected_node_id = None
        self.selected_node_ids.clear()
        self.status_requested.emit(f"Deleted {len(titles)} canvas block(s): {', '.join(titles[:3])}{'...' if len(titles) > 3 else ''}")
        if self.canvas:
            self.canvas.update()

    def request_node_info(self, node_id: str) -> None:
        node = self.nodes.get(node_id)
        if not node:
            return
        meta = dict(node.meta or {})
        meta.setdefault("name", node.title)
        meta.setdefault("type", node.node_type)
        meta.setdefault("description", f"Canvas block: {node.title}")
        meta.setdefault("address", "N/A" if node.node_type == "MODEL" else "mock")
        meta.setdefault("datatype", "PY/ONNX" if node.node_type == "MODEL" else "MOCK")
        meta.setdefault("variable", node.title)
        meta.setdefault("symbol", node.title)
        meta["canvas_node_id"] = node_id
        meta["canvas_subtitle"] = node.subtitle
        meta["input_count"] = node.input_count
        meta["output_count"] = node.output_count
        self.node_info_requested.emit(meta)

    def request_node_double_clicked(self, node_id: str) -> None:
        node = self.nodes.get(node_id)
        if not node:
            return
        if node.node_type == "MODEL":
            self.model_load_requested.emit(node_id, dict(node.meta or {}))
        else:
            self.request_node_info(node_id)
            self.status_requested.emit(f"Selected {node.node_type.lower()} block: {node.title}")


    def runtime_graph(self) -> dict:
        """Return the current canvas as a backend runtime graph.

        This is intentionally backend-oriented, not UI-oriented: it extracts the
        MEASUREMENT blocks currently placed on the canvas, CHARACTERISTIC/STIM
        targets, model blocks, and independent edge connections.  The PyQt
        frontend serializes this graph to JSON and writes it to the SHM config
        block before starting the backend.
        """
        nodes = []
        measurements = []
        characteristics = []
        models = []

        for node_id, node in self.nodes.items():
            meta = dict(node.meta or {})
            entry = {
                "node_id": node_id,
                "type": node.node_type,
                "name": meta.get("name", node.title),
                "title": node.title,
                "address": meta.get("address", meta.get("ecuAddress", "N/A")),
                "datatype": meta.get("datatype", meta.get("dataType", "UNKNOWN")),
                "unit": meta.get("unit", ""),
                "symbol": meta.get("variable", meta.get("symbol", node.title)),
                "model_path": meta.get("model_path", ""),
                "input_count": node.input_count,
                "output_count": node.output_count,
                "position": {"x": node.x(), "y": node.y()},
            }
            nodes.append(entry)
            if node.node_type == "MEASUREMENT":
                measurements.append(entry)
            elif node.node_type == "CHARACTERISTIC":
                characteristics.append(entry)
            elif node.node_type == "MODEL":
                models.append(entry)

        return {
            "nodes": nodes,
            "measurements": measurements,
            "characteristics": characteristics,
            "models": models,
            "edges": [edge.meta() for edge in self.edges],
        }

    def request_edge_flow(self, edge_id: str) -> None:
        edge = self._edge_by_id(edge_id)
        if not edge:
            return
        self.edge_flow_requested.emit(edge.meta())
        self.status_requested.emit(f"Opened data-flow graph: {edge.label} [{edge.data_key}]")

    def _edge_by_id(self, edge_id: str) -> Optional[EdgeConnection]:
        for edge in self.edges:
            if edge.edge_id == edge_id:
                return edge
        return None

    def begin_connection(self, node_id: str, kind: str, port_index: int, pt: QPointF) -> None:
        if node_id not in self.nodes:
            return
        node = self.nodes[node_id]
        if kind == "out" and (not node.has_output_port() or port_index >= node.output_count):
            return
        if kind == "in" and (not node.has_input_port() or port_index >= node.input_count):
            return
        self.connection_preview = (node_id, kind, int(port_index), QPointF(pt))
        port_label = "output" if kind == "out" else "input"
        self.status_requested.emit(
            f"Connection started from {node.title} {port_label} port {int(port_index) + 1}. "
            "Move to a compatible destination port and click; Esc/right-click cancels."
        )
        if self.canvas:
            self.canvas.update()

    def update_connection_preview(self, pt: QPointF) -> None:
        if not self.connection_preview:
            return
        node_id, kind, port_index, _old = self.connection_preview
        self.connection_preview = (node_id, kind, port_index, QPointF(pt))
        if self.canvas:
            self.canvas.update()

    def finish_connection_at(self, pt: QPointF) -> bool:
        preview = self.connection_preview
        if not preview:
            return False
        start_id, kind, start_port, _old = preview
        target = self._node_and_port_at_point(pt, "in" if kind == "out" else "out")
        if not target:
            if self.canvas:
                self.canvas.update()
            return False
        target_id, target_kind, target_port = target
        if target_id == start_id:
            self.status_requested.emit("Connection rejected: source and destination must be different blocks.")
            return False
        if kind == "out" and target_kind == "in":
            src, dst, sp, dp = start_id, target_id, start_port, target_port
        elif kind == "in" and target_kind == "out":
            src, dst, sp, dp = target_id, start_id, target_port, start_port
        else:
            return False
        if self._connect(src, dst, sp, dp):
            self.connection_preview = None
            self.status_requested.emit(
                f"Connected {self.nodes[src].title}:out{sp + 1} → {self.nodes[dst].title}:in{dp + 1}"
            )
            if self.canvas:
                self.canvas.update()
            return True
        self.status_requested.emit("Connection rejected: each input port accepts one source; choose another input port.")
        if self.canvas:
            self.canvas.update()
        return False

    def cancel_connection(self, message: str = "Connection canceled.") -> None:
        if self.connection_preview:
            self.connection_preview = None
            self.status_requested.emit(message)
            if self.canvas:
                self.canvas.update()

    def _node_and_port_at_point(self, pt: QPointF, required_kind: str) -> Optional[Tuple[str, str, int]]:
        point = QPoint(int(pt.x()), int(pt.y()))
        for node_id, node in reversed(list(self.nodes.items())):
            local = node.mapFromParent(point)
            hit = node._hit_port(local)
            if hit and hit[0] == required_kind:
                return node_id, hit[0], hit[1]
        return None

    def _node_at_point(self, pt: QPointF) -> Optional[str]:
        x, y = int(pt.x()), int(pt.y())
        for node_id, node in reversed(list(self.nodes.items())):
            if node.geometry().contains(x, y):
                return node_id
        return None

    def make_cubic_path(self, a: QPointF, b: QPointF) -> QPainterPath:
        dx = max(80.0, abs(b.x() - a.x()) * 0.45)
        qpath = QPainterPath()
        qpath.moveTo(a)
        qpath.cubicTo(QPointF(a.x() + dx, a.y()), QPointF(b.x() - dx, b.y()), b)
        return qpath

    def path_for_edge(self, edge: EdgeConnection) -> QPainterPath:
        if edge.src_id not in self.nodes or edge.dst_id not in self.nodes:
            return QPainterPath()
        a = self.nodes[edge.src_id].port_center("out", edge.src_port)
        b = self.nodes[edge.dst_id].port_center("in", edge.dst_port)
        return self.make_cubic_path(a, b)

    def edge_at_point(self, pt: QPointF) -> Optional[EdgeConnection]:
        stroker = QPainterPathStroker()
        stroker.setWidth(14.0)
        for edge in reversed(self.edges):
            path = self.path_for_edge(edge)
            if not path.isEmpty() and stroker.createStroke(path).contains(pt):
                return edge
        return None

    def update_measurements(self, data: dict) -> None:
        for name, value in data.items():
            for node in self.node_by_signal.get(name, []):
                node.update_value(float(value))
        self._mark_live_edges(data.keys())

    def update_model_outputs(self, data: dict) -> None:
        model1 = self.nodes.get("model1")
        if model1 and ("model1_a" in data or "model1_b" in data):
            model1.update_value(f"{float(data.get('model1_a', 0.0)):.3f} / {float(data.get('model1_b', 0.0)):.3f}")
        for key in ("model2", "model3", "model4"):
            node = self.nodes.get(key)
            if node and key in data:
                node.update_value(float(data[key]))
        if "model4" in data:
            for node_id, node in self.nodes.items():
                if node.node_type == "MODEL" and node_id.startswith("model_custom_"):
                    node.update_value(float(data["model4"]))
        char = self.nodes.get("characteristic")
        if char and "ecu_write_value" in data:
            char.update_value(float(data["ecu_write_value"]))
        for name in ("signal7", "signal8"):
            if name in data:
                for node in self.node_by_signal.get(name, []):
                    node.update_value(float(data[name]))
        self._mark_live_edges(data.keys())

    def _mark_live_edges(self, keys: Iterable[str]) -> None:
        keys = set(keys)
        for edge in self.edges:
            if edge.data_key in keys:
                edge.active = True
        if self.canvas:
            self.canvas.update()

    def set_edges_active(self, active: bool) -> None:
        self.edges_active = bool(active)
        for edge in self.edges:
            edge.active = bool(active)
        if self.canvas:
            self.canvas.update()

    def pulse_active_edges(self) -> None:
        self.set_edges_active(True)


class DiagramView(QScrollArea):
    def __init__(self, scene: DiagramScene, parent=None):
        super().__init__(parent)
        self.scene_controller = scene
        self._middle_panning = False
        self._pan_last: Optional[QPoint] = None
        self.setObjectName("workspaceScroll")
        self.setWidgetResizable(False)
        self.setFrameShape(QFrame.NoFrame)
        self.setMinimumHeight(520)
        self.setFocusPolicy(Qt.StrongFocus)
        self.canvas = CanvasWidget(scene)
        scene.view = self
        scene.bind_canvas(self.canvas)
        self.setWidget(self.canvas)
        self.setStyleSheet("QScrollArea#workspaceScroll { background:#12161F; border:0; }")

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape and self.scene_controller.connection_preview:
            self.scene_controller.cancel_connection("Connection canceled.")
            event.accept()
            return
        if event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            self.scene_controller.delete_selected_node()
            event.accept()
            return
        super().keyPressEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MiddleButton:
            self._middle_panning = True
            self._pan_last = event.pos()
            self.viewport().setCursor(Qt.ClosedHandCursor)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._middle_panning and self._pan_last is not None:
            delta = event.pos() - self._pan_last
            self._pan_last = event.pos()
            hbar: QScrollBar = self.horizontalScrollBar()
            vbar: QScrollBar = self.verticalScrollBar()
            hbar.setValue(hbar.value() - delta.x())
            vbar.setValue(vbar.value() - delta.y())
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MiddleButton and self._middle_panning:
            self._middle_panning = False
            self._pan_last = None
            self.viewport().setCursor(Qt.ArrowCursor)
            event.accept()
            return
        super().mouseReleaseEvent(event)
