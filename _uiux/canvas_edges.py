from __future__ import annotations

from PyQt5.QtGui import QColor, QPainterPath, QPen
from PyQt5.QtWidgets import QGraphicsPathItem


class EdgeItem(QGraphicsPathItem):
    """Curved connection between two graph nodes.

    Important PyQt stability note:
    The first drag/drop build used QTimer.singleShot() for every edge pulse.
    At 16 ms replay this creates hundreds of short-lived timers per second.
    On some Windows/PyQt5 builds that can terminate the process with
    0xC0000409 instead of a Python traceback. This implementation keeps the
    visual pulse state inside the item and lets the scene/main window decide
    when edges are active. No per-edge timer objects are created.
    """

    def __init__(self, src, dst, color="#7FE18D"):
        super().__init__()
        self.src = src
        self.dst = dst
        self.base_color = QColor(color)
        self.active_color = QColor("#F8FBFF")
        self.setZValue(-10)
        self.src.output_edges.append(self)
        self.dst.input_edges.append(self)
        self._active = False
        self.refresh()
        self._update_pen()

    def refresh(self):
        sx, sy = self.src.center_right()
        dx, dy = self.dst.center_left()
        path = QPainterPath()
        path.moveTo(sx, sy)
        span = max(80.0, abs(dx - sx) * 0.45)
        path.cubicTo(sx + span, sy, dx - span, dy, dx, dy)
        self.setPath(path)

    def set_active(self, active: bool) -> None:
        active = bool(active)
        if self._active != active:
            self._active = active
            self._update_pen()
        self.refresh()

    def _update_pen(self):
        if self._active:
            pen = QPen(self.active_color, 2.8)
        else:
            color = QColor(self.base_color)
            color.setAlphaF(0.92)
            pen = QPen(color, 2.2)
        pen.setCosmetic(True)
        self.setPen(pen)

    def pulse_once(self):
        # Backward-compatible name. Keep edges active during replay without
        # scheduling timers from inside QGraphicsItems.
        self.set_active(True)


class Port:
    def __init__(self, name: str, direction: str):
        self.name = name
        self.direction = direction
