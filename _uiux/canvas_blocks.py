from __future__ import annotations

from PyQt5.QtCore import QRectF, Qt
from PyQt5.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PyQt5.QtWidgets import QGraphicsItem, QStyle, QStyleOptionGraphicsItem, QWidget


_TYPE_STYLE = {
    "MEASUREMENT": {"header": "#0C5DB8", "role": "ECU IN", "role_color": "#9FD1FF"},
    "MODEL": {"header": "#207229", "role": "TimeSeries AI", "role_color": "#9AE6B4"},
    "CHARACTERISTIC": {"header": "#D56700", "role": "ECU OUT", "role_color": "#FFE0A6"},
    "STRUCT": {"header": "#343D50", "role": "Mock Layer", "role_color": "#CDD6E3"},
}


class BlockItem(QGraphicsItem):
    """Dark Simulink-like node used by the mock XCP canvas."""

    def __init__(
        self,
        title: str,
        subtitle: str,
        x: float,
        y: float,
        w: float = 130,
        h: float = 72,
        node_type: str = "STRUCT",
        value: str = "0.00",
        meta: dict | None = None,
    ):
        super().__init__()
        self.title = title
        self.subtitle = subtitle
        self.node_type = node_type.upper()
        self.value = value
        self.meta = meta or {}
        self.rect = QRectF(0, 0, w, h)
        self.input_edges = []
        self.output_edges = []
        self.setFlags(
            QGraphicsItem.ItemIsMovable
            | QGraphicsItem.ItemIsSelectable
            | QGraphicsItem.ItemSendsGeometryChanges
        )
        self.setAcceptHoverEvents(True)
        self.setToolTip(self._tooltip())
        self.setPos(x, y)

    def _tooltip(self) -> str:
        parts = [self.title, self.subtitle]
        if self.meta:
            parts.extend(
                [
                    f"Type: {self.meta.get('type', self.node_type)}",
                    f"Address: {self.meta.get('address', self.meta.get('ecuAddress', 'mock'))}",
                    f"Symbol: {self.meta.get('variable', self.meta.get('symbol', 'mock'))}",
                ]
            )
        return "\n".join(str(p) for p in parts if p)

    def boundingRect(self) -> QRectF:
        return self.rect.adjusted(-9, -9, 9, 9)

    def center_right(self):
        p = self.scenePos()
        return p.x() + self.rect.width(), p.y() + self.rect.height() / 2.0

    def center_left(self):
        p = self.scenePos()
        return p.x(), p.y() + self.rect.height() / 2.0

    def update_value(self, value):
        if isinstance(value, float):
            self.value = f"{value:.3f}"
        else:
            self.value = str(value)
        self.update()

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionHasChanged:
            for edge in self.input_edges + self.output_edges:
                edge.refresh()
        return super().itemChange(change, value)

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: QWidget | None = None):
        painter.setRenderHint(QPainter.Antialiasing, True)
        style = _TYPE_STYLE.get(self.node_type, _TYPE_STYLE["STRUCT"])
        selected = bool(option.state & QStyle.State_Selected)

        body_path = QPainterPath()
        body_path.addRoundedRect(self.rect, 10, 10)
        painter.fillPath(body_path, QColor("#2D313B"))
        painter.setPen(QPen(QColor("#6A7281" if selected else "#333742"), 2.0 if selected else 1.0))
        painter.drawPath(body_path)

        header_rect = QRectF(0, 0, self.rect.width(), 22)
        header_path = QPainterPath()
        header_path.addRoundedRect(header_rect, 10, 10)
        painter.fillPath(header_path, QColor(style["header"]))
        painter.fillRect(QRectF(0, 12, self.rect.width(), 10), QColor(style["header"]))

        painter.setPen(Qt.NoPen)
        if self.node_type in {"MODEL", "CHARACTERISTIC"}:
            painter.setBrush(QColor("#9ED7FF"))
            painter.drawEllipse(QRectF(-5, self.rect.height() / 2.0 - 5, 10, 10))
        if self.node_type != "STRUCT":
            painter.setBrush(QColor("#92DDA0" if self.node_type != "CHARACTERISTIC" else "#FFD29D"))
            painter.drawEllipse(QRectF(self.rect.width() - 5, self.rect.height() / 2.0 - 5, 10, 10))

        painter.setPen(QColor("#F8FBFF"))
        font = QFont()
        font.setPointSize(7)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(QRectF(8, 3, self.rect.width() - 16, 16), Qt.AlignLeft | Qt.AlignVCenter, self.node_type)

        body_font = QFont()
        body_font.setPointSize(7)
        painter.setFont(body_font)
        painter.setPen(QColor(style["role_color"]))
        painter.drawText(QRectF(8, 28, self.rect.width() - 16, 14), Qt.AlignLeft | Qt.AlignVCenter, style["role"])

        title_font = QFont()
        title_font.setPointSize(7)
        title_font.setBold(True)
        painter.setFont(title_font)
        painter.setPen(QColor("#E7EDF7"))
        painter.drawText(QRectF(8, 42, self.rect.width() - 16, 16), Qt.AlignLeft | Qt.AlignVCenter, self.title)

        sub_font = QFont()
        sub_font.setPointSize(6)
        painter.setFont(sub_font)
        painter.setPen(QColor("#97A0B2"))
        painter.drawText(QRectF(8, 58, self.rect.width() - 16, 15), Qt.AlignLeft | Qt.AlignVCenter, self.subtitle)

        val_font = QFont()
        val_font.setPointSize(7)
        val_font.setBold(True)
        painter.setFont(val_font)
        painter.setPen(QColor("#FFFFFF"))
        painter.drawText(QRectF(8, self.rect.height() - 21, self.rect.width() - 16, 16), Qt.AlignLeft | Qt.AlignVCenter, self.value)


class SignalBlock(BlockItem):
    def __init__(self, title, subtitle, x, y, w=130, h=78, meta=None):
        super().__init__(title, subtitle, x, y, w, h, "MEASUREMENT", "0.00", meta)


class ModelBlock(BlockItem):
    def __init__(self, title, subtitle, x, y, w=150, h=90, value="0.00", meta=None):
        super().__init__(title, subtitle, x, y, w, h, "MODEL", value, meta)


class CharBlock(BlockItem):
    def __init__(self, title, subtitle, x, y, w=150, h=88, meta=None):
        super().__init__(title, subtitle, x, y, w, h, "CHARACTERISTIC", "0.00", meta)


class StructBlock(BlockItem):
    def __init__(self, title, subtitle, x, y, w=150, h=78, meta=None):
        super().__init__(title, subtitle, x, y, w, h, "STRUCT", "", meta)
