"""Xem trước model 3D ngay trong phần mềm: xoay bằng chuột, zoom bằng con lăn. Hỗ trợ OBJ và STL.

Tự vẽ bằng QPainter (không cần thư viện 3D nào khác nên nhẹ, chạy ở mọi máy). Các định dạng khác
(FBX, GLB, BLEND...) chưa xem được: hiện thông báo thay vì báo lỗi.
"""
import math
import os
import struct

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QBrush, QColor, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import QWidget

SUPPORTED = (".obj", ".stl")
MAX_FILE_MB = 30       # tệp lớn hơn thì không nạp để khỏi treo máy
MAX_FACES = 14000      # nhiều mặt hơn thì vẽ rút gọn (vẫn đúng hình dáng)


class ModelError(Exception):
    pass


class Model:
    def __init__(self, verts, faces, simplified=False):
        self.verts = verts      # list[(x, y, z)] đã đưa về tâm (0,0,0), bán kính ~1
        self.faces = faces      # list[(a, b, c)] tam giác
        self.simplified = simplified

    @property
    def face_count(self):
        return len(self.faces)


def _normalize(verts):
    xs, ys, zs = zip(*verts)
    cx, cy, cz = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, (min(zs) + max(zs)) / 2
    r = max(max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs)) / 2 or 1.0
    return [((x - cx) / r, (y - cy) / r, (z - cz) / r) for x, y, z in verts]


def _decimate(faces):
    if len(faces) <= MAX_FACES:
        return faces, False
    step = math.ceil(len(faces) / MAX_FACES)
    return faces[::step], True


def load_obj(path):
    verts, faces = [], []
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if line.startswith("v "):
                p = line.split()
                try:
                    verts.append((float(p[1]), float(p[2]), float(p[3])))
                except (IndexError, ValueError):
                    continue
            elif line.startswith("f "):
                idx = []
                for tok in line.split()[1:]:
                    try:
                        i = int(tok.split("/")[0])
                    except ValueError:
                        continue
                    idx.append(i - 1 if i > 0 else len(verts) + i)  # chỉ số âm tính từ cuối
                for k in range(1, len(idx) - 1):  # đa giác -> tam giác (quạt)
                    faces.append((idx[0], idx[k], idx[k + 1]))
    return verts, faces


def load_stl(path):
    with open(path, "rb") as f:
        data = f.read()
    verts, faces = [], []
    n = struct.unpack("<I", data[80:84])[0] if len(data) >= 84 else -1
    if len(data) >= 84 and 84 + n * 50 == len(data):  # STL nhị phân
        off = 84
        for _ in range(n):
            vals = struct.unpack("<12fH", data[off:off + 50])
            base = len(verts)
            verts += [tuple(vals[3:6]), tuple(vals[6:9]), tuple(vals[9:12])]
            faces.append((base, base + 1, base + 2))
            off += 50
        return verts, faces
    text = data.decode("utf-8", errors="replace")  # STL chữ
    cur = []
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("vertex"):
            p = line.split()
            try:
                cur.append((float(p[1]), float(p[2]), float(p[3])))
            except (IndexError, ValueError):
                continue
            if len(cur) == 3:
                base = len(verts)
                verts += cur
                faces.append((base, base + 1, base + 2))
                cur = []
    return verts, faces


def load_model(path):
    ext = os.path.splitext(path)[1].lower()
    if ext not in SUPPORTED:
        raise ModelError(f"Chưa xem được định dạng {ext or 'này'} (xem được: OBJ, STL).")
    if os.path.getsize(path) > MAX_FILE_MB * 1024 * 1024:
        raise ModelError(f"Tệp lớn hơn {MAX_FILE_MB} MB nên không nạp để xem trước.")
    verts, faces = load_obj(path) if ext == ".obj" else load_stl(path)
    n = len(verts)
    faces = [f for f in faces if all(0 <= i < n for i in f)]
    if not verts or not faces:
        raise ModelError("Không đọc được hình khối nào trong tệp này.")
    faces, simplified = _decimate(faces)
    return Model(_normalize(verts), faces, simplified)


class ModelView(QWidget):
    """Khung xem: kéo chuột trái để xoay, con lăn để zoom, kéo chuột phải (hoặc giữa) để dịch, nhấp đúp để về mặc định."""

    def __init__(self):
        super().__init__()
        self.model = None
        self.message = "Chưa chọn model"
        self.setMinimumSize(160, 160)
        self.setCursor(Qt.OpenHandCursor)
        self.reset_view()
        self._last = None
        self._btn = None

    def reset_view(self):
        self.yaw, self.pitch, self.zoom = 0.6, 0.35, 1.0
        self.pan = QPointF(0, 0)
        self.update()

    def set_model(self, model, message=""):
        self.model = model
        self.message = message
        self.reset_view()

    def clear(self, message="Chưa chọn model"):
        self.model, self.message = None, message
        self.update()

    # ---- điều khiển chuột
    def mousePressEvent(self, e):
        self._last, self._btn = e.position(), e.button()
        self.setCursor(Qt.ClosedHandCursor)

    def mouseMoveEvent(self, e):
        if self._last is None:
            return
        d = e.position() - self._last
        self._last = e.position()
        if self._btn == Qt.LeftButton:
            self.yaw += d.x() * 0.01
            self.pitch = max(-1.55, min(1.55, self.pitch + d.y() * 0.01))
        else:
            self.pan += d
        self.update()

    def mouseReleaseEvent(self, _e):
        self._last = None
        self.setCursor(Qt.OpenHandCursor)

    def mouseDoubleClickEvent(self, _e):
        self.reset_view()

    def wheelEvent(self, e):
        steps = e.angleDelta().y() / 120.0
        self.zoom = max(0.2, min(12.0, self.zoom * (1.15 ** steps)))
        self.update()
        e.accept()

    # ---- vẽ
    def projected(self):
        """Trả về danh sách (độ sâu, đa giác, độ sáng 0..1) đã sắp từ xa tới gần. Tách riêng để kiểm tra được."""
        m = self.model
        if not m:
            return []
        cy, sy, cp, sp = math.cos(self.yaw), math.sin(self.yaw), math.cos(self.pitch), math.sin(self.pitch)
        rot = []
        for x, y, z in m.verts:
            x1, z1 = x * cy + z * sy, -x * sy + z * cy      # quay quanh trục dọc
            y2, z2 = y * cp - z1 * sp, y * sp + z1 * cp     # nghiêng lên xuống
            rot.append((x1, y2, z2))
        scale = min(self.width(), self.height()) * 0.42 * self.zoom
        ox, oy = self.width() / 2 + self.pan.x(), self.height() / 2 + self.pan.y()
        pts = [QPointF(ox + x * scale, oy - y * scale) for x, y, _z in rot]
        light = (0.3, 0.5, 0.8)
        out = []
        for a, b, c in m.faces:
            pa, pb, pc = rot[a], rot[b], rot[c]
            ux, uy, uz = pb[0] - pa[0], pb[1] - pa[1], pb[2] - pa[2]
            vx, vy, vz = pc[0] - pa[0], pc[1] - pa[1], pc[2] - pa[2]
            nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
            ln = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
            shade = abs(nx * light[0] + ny * light[1] + nz * light[2]) / ln  # hai mặt đều sáng (không cắt mặt sau)
            out.append(((pa[2] + pb[2] + pc[2]) / 3, QPolygonF([pts[a], pts[b], pts[c]]), shade))
        out.sort(key=lambda t: t[0])
        return out

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), QColor("#15171c"))
        if not self.model:
            p.setPen(QColor("#9aa0aa"))
            p.drawText(self.rect().adjusted(12, 12, -12, -12), Qt.AlignCenter | Qt.TextWordWrap, self.message)
            return
        for _z, poly, shade in self.projected():
            g = int(70 + 170 * shade)
            col = QColor(g, int(g * 0.86), int(g * 0.55))
            p.setBrush(QBrush(col))
            p.setPen(QPen(col, 0.6))  # viền cùng màu để không lộ khe giữa các mặt
            p.drawPolygon(poly)
        p.setPen(QColor("#9aa0aa"))
        note = f"{self.model.face_count:,} mặt" + (" (vẽ rút gọn)" if self.model.simplified else "")
        p.drawText(8, self.height() - 8, note + "  ·  kéo: xoay · lăn: zoom · chuột phải: dịch · nhấp đúp: về mặc định")
