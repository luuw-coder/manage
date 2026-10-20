"""Biểu tượng vẽ bằng code (không cần tệp ảnh) và biểu tượng mục."""
import math
import os

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPainterPath, QPen, QPixmap, QPolygonF

CATEGORY_ICONS = ["stack", "user", "music", "image", "gif", "film", "heart",
                  "cube", "clapper", "pen", "doc", "folder", "star", "camera"]
CATEGORY_COLORS = ["#35c3e8", "#ff6b6b", "#ffa94d", "#ffd43b", "#51cf66",
                   "#63e6be", "#74c0fc", "#b197fc", "#f783ac", "#adb5bd"]


def _poly(p, pts, close=False):
    poly = QPolygonF([QPointF(x, y) for x, y in pts])
    if close:
        p.drawPolygon(poly)
    else:
        p.drawPolyline(poly)


def _line(p, x1, y1, x2, y2):
    p.drawLine(QPointF(x1, y1), QPointF(x2, y2))


def make_icon(name, color="#e8e9ec", size=18):
    scale = 2
    pm = QPixmap(size * scale, size * scale)
    pm.fill(Qt.transparent)
    pm.setDevicePixelRatio(scale)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.scale(size / 24.0, size / 24.0)
    pen = QPen(QColor(color), 1.9)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)
    R = QRectF
    if name == "pin":
        _line(p, 12, 14, 12, 22)
        _poly(p, [(9, 3), (15, 3), (14, 10), (18, 14), (6, 14), (10, 10)], True)
    elif name == "reload":
        p.drawArc(R(4, 4, 16, 16), 60 * 16, 280 * 16)
        _line(p, 18, 3, 18, 8)
        _line(p, 18, 8, 13, 8)
    elif name == "shrink":
        _poly(p, [(4, 14), (10, 14), (10, 20)])
        _poly(p, [(20, 10), (14, 10), (14, 4)])
        _line(p, 14, 10, 21, 3)
        _line(p, 3, 21, 10, 14)
    elif name == "eyeoff":
        p.drawEllipse(R(2, 7, 20, 10))
        p.drawEllipse(R(9.5, 9.5, 5, 5))
        _line(p, 4, 4, 20, 20)
    elif name == "moho":
        _poly(p, [(20, 4), (20, 12), (5, 12)])
        _poly(p, [(10, 7), (5, 12), (10, 17)])
    elif name == "filter":
        _poly(p, [(3, 4), (21, 4), (14, 12), (14, 20), (10, 18), (10, 12)], True)
    elif name == "folderplus":
        _poly(p, [(3, 7), (3, 5), (9, 5), (11, 7)])
        p.drawRoundedRect(R(3, 7, 18, 12), 2, 2)
        _line(p, 12, 10, 12, 16)
        _line(p, 9, 13, 15, 13)
    elif name == "fileplus":
        _poly(p, [(6, 3), (14, 3), (19, 8), (19, 21), (6, 21)], True)
        _poly(p, [(14, 3), (14, 8), (19, 8)])
        _line(p, 12.5, 12, 12.5, 18)
        _line(p, 9.5, 15, 15.5, 15)
    elif name == "grid":
        for x, y in ((4, 4), (13, 4), (4, 13), (13, 13)):
            p.drawRect(R(x, y, 7, 7))
    elif name == "list":
        for y in (6, 12, 18):
            _line(p, 8, y, 20, y)
            p.drawPoint(QPointF(4, y))
    elif name == "plus":
        _line(p, 12, 5, 12, 19)
        _line(p, 5, 12, 19, 12)
    elif name == "minus":
        _line(p, 5, 12, 19, 12)
    elif name == "expand":
        p.drawRect(R(5, 5, 14, 14))
    elif name == "back":
        _line(p, 19, 12, 5, 12)
        _poly(p, [(11, 6), (5, 12), (11, 18)])
    elif name == "stack":
        _poly(p, [(12, 3), (21, 8), (12, 13), (3, 8)], True)
        _poly(p, [(3, 13), (12, 18), (21, 13)])
    elif name == "user":
        p.drawEllipse(R(8, 4, 8, 8))
        p.drawArc(R(4, 14, 16, 14), 0, 180 * 16)
    elif name == "music":
        _line(p, 9, 18, 9, 5)
        _line(p, 9, 5, 20, 3)
        _line(p, 20, 3, 20, 16)
        p.drawEllipse(R(3, 15, 6, 6))
        p.drawEllipse(R(14, 13, 6, 6))
    elif name == "image":
        p.drawRoundedRect(R(3, 4, 18, 16), 2, 2)
        p.drawEllipse(R(7, 8, 4, 4))
        _poly(p, [(21, 16), (16, 11), (8, 19)])
    elif name == "gif":
        p.drawRoundedRect(R(3, 6, 18, 12), 2, 2)
        f = QFont("Segoe UI")
        f.setPixelSize(7)
        f.setBold(True)
        p.setFont(f)
        p.drawText(R(3, 6, 18, 12), Qt.AlignCenter, "GIF")
    elif name == "film":
        p.drawRoundedRect(R(3, 4, 18, 16), 2, 2)
        for x in (7, 17):
            _line(p, x, 4, x, 20)
        for y in (9, 15):
            _line(p, 3, y, 7, y)
            _line(p, 17, y, 21, y)
    elif name == "heart":
        path = QPainterPath()
        path.moveTo(12, 20)
        path.cubicTo(3, 13, 3, 5, 8, 5)
        path.cubicTo(10, 5, 11.5, 6.2, 12, 8)
        path.cubicTo(12.5, 6.2, 14, 5, 16, 5)
        path.cubicTo(21, 5, 21, 13, 12, 20)
        p.drawPath(path)
    elif name == "cube":
        _poly(p, [(12, 3), (20, 7.5), (20, 16.5), (12, 21), (4, 16.5), (4, 7.5)], True)
        _poly(p, [(4, 7.5), (12, 12), (20, 7.5)])
        _line(p, 12, 12, 12, 21)
    elif name == "clapper":
        p.drawRoundedRect(R(3, 9, 18, 11), 2, 2)
        _poly(p, [(3, 9), (4.5, 4), (21, 7), (19.5, 9)], True)
        _line(p, 9, 5.2, 7.5, 9)
        _line(p, 14.5, 6.2, 13, 9)
    elif name == "pen":
        _poly(p, [(4, 20), (5, 15), (16, 4), (20, 8), (9, 19)], True)
        _line(p, 14, 6, 18, 10)
    elif name == "doc":
        _poly(p, [(6, 3), (14, 3), (19, 8), (19, 21), (6, 21)], True)
        _poly(p, [(14, 3), (14, 8), (19, 8)])
        _line(p, 9, 13, 16, 13)
        _line(p, 9, 17, 16, 17)
    elif name == "folder":
        _poly(p, [(3, 7), (3, 5), (9, 5), (11, 7)])
        p.drawRoundedRect(R(3, 7, 18, 12), 2, 2)
    elif name == "star":
        pts = []
        for i in range(10):
            r = 9 if i % 2 == 0 else 4
            a = -math.pi / 2 + i * math.pi / 5
            pts.append((12 + r * math.cos(a), 12.5 + r * math.sin(a)))
        _poly(p, pts, True)
    elif name == "camera":
        p.drawRoundedRect(R(3, 7, 18, 13), 2, 2)
        p.drawEllipse(R(8.5, 10.5, 7, 7))
        _poly(p, [(8, 7), (9.5, 4), (14.5, 4), (16, 7)])
    elif name == "close":
        _line(p, 6, 6, 18, 18)
        _line(p, 18, 6, 6, 18)
    elif name == "chevdown":
        _poly(p, [(6, 9), (12, 15), (18, 9)])
    elif name == "play":
        _poly(p, [(8, 5), (19, 12), (8, 19)], True)
    elif name == "pause":
        _line(p, 9, 5, 9, 19)
        _line(p, 15, 5, 15, 19)
    elif name == "stop":
        p.drawRect(R(6, 6, 12, 12))
    elif name == "zoomin":
        p.drawEllipse(R(4, 4, 14, 14))
        _line(p, 16, 16, 21, 21)
        _line(p, 8, 11, 14, 11)
        _line(p, 11, 8, 11, 14)
    elif name == "zoomout":
        p.drawEllipse(R(4, 4, 14, 14))
        _line(p, 16, 16, 21, 21)
        _line(p, 8, 11, 14, 11)
    elif name == "fitw":
        _line(p, 3, 12, 21, 12)
        _poly(p, [(7, 8), (3, 12), (7, 16)])
        _poly(p, [(17, 8), (21, 12), (17, 16)])
    p.end()
    return QIcon(pm)


def image_pixmap(path, size):
    """Ảnh người dùng chọn làm biểu tượng: cắt vuông, bo góc."""
    src = QPixmap(path)
    if src.isNull():
        return None
    px = size * 2
    src = src.scaled(px, px, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
    x, y = (src.width() - px) // 2, (src.height() - px) // 2
    src = src.copy(x, y, px, px)
    out = QPixmap(px, px)
    out.fill(Qt.transparent)
    p = QPainter(out)
    p.setRenderHint(QPainter.Antialiasing)
    clip = QPainterPath()
    clip.addRoundedRect(QRectF(0, 0, px, px), px * 0.22, px * 0.22)
    p.setClipPath(clip)
    p.drawPixmap(0, 0, src)
    p.end()
    out.setDevicePixelRatio(2)
    return out


def category_icon(cat, size=20):
    img = cat.get("icon_image")
    if img and os.path.exists(img):
        pm = image_pixmap(img, size)
        if pm is not None:
            return QIcon(pm)
    return make_icon(cat.get("icon") or "folder", cat.get("color") or "#74c0fc", size)
