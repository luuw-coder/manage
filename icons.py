"""Biểu tượng vẽ bằng code (không cần tệp ảnh)."""
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap, QPolygonF


def make_icon(name, color="#e8e9ec", size=18):
    scale = 2
    pm = QPixmap(size * scale, size * scale)
    pm.fill(Qt.transparent)
    pm.setDevicePixelRatio(scale)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.scale(size / 24.0, size / 24.0)
    pen = QPen(QColor(color), 2.0)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)
    P = QPointF
    if name == "pin":
        p.drawLine(P(12, 14), P(12, 22))
        p.drawPolygon(QPolygonF([P(9, 3), P(15, 3), P(14, 10), P(18, 14), P(6, 14), P(10, 10)]))
    elif name == "search":
        p.drawEllipse(QRectF(4, 4, 13, 13))
        p.drawLine(P(15, 15), P(21, 21))
    elif name == "reload":
        p.drawArc(QRectF(4, 4, 16, 16), 60 * 16, 280 * 16)
        p.drawLine(P(18, 3), P(18, 8))
        p.drawLine(P(18, 8), P(13, 8))
    elif name == "grid":
        for x, y in ((4, 4), (13, 4), (4, 13), (13, 13)):
            p.drawRect(QRectF(x, y, 7, 7))
    elif name == "list":
        for y in (6, 12, 18):
            p.drawLine(P(8, y), P(20, y))
            p.drawPoint(P(4, y))
    elif name == "opacity":
        p.drawEllipse(QRectF(3, 3, 18, 18))
        p.drawLine(P(12, 3), P(12, 21))
        p.setBrush(QColor(color))
        p.drawPie(QRectF(3, 3, 18, 18), 90 * 16, 180 * 16)
    elif name == "minus":
        p.drawLine(P(5, 12), P(19, 12))
    elif name == "expand":
        p.drawRect(QRectF(5, 5, 14, 14))
    elif name == "plus":
        p.drawLine(P(12, 5), P(12, 19))
        p.drawLine(P(5, 12), P(19, 12))
    p.end()
    return QIcon(pm)
