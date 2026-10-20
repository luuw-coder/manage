"""Hình thu nhỏ cho thẻ tệp / thư mục (chữ nhật bo góc)."""
import os

from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QColor, QFont, QImageReader, QPainter, QPainterPath, QPixmap

THUMB = QSize(88, 66)
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".jfif", ".webp", ".bmp", ".gif", ".svg", ".tif", ".tiff", ".tga", ".ico"}
KIND_COLORS = [
    ("#5b6bd6", {".wav", ".mp3", ".ogg", ".flac", ".m4a"}),
    ("#c2587a", {".mp4", ".mov", ".avi", ".mkv"}),
    ("#7a6bd6", {".obj", ".fbx", ".glb", ".gltf", ".stl", ".blend"}),
    ("#d98a3d", {".moho", ".fla"}),
    ("#3f9d8f", {".svg", ".ai", ".eps"}),
    ("#8a93a6", {".pdf", ".txt", ".md", ".docx"}),
]
_cache = {}


def _rounded(pm, radius=10):
    out = QPixmap(pm.size())
    out.fill(Qt.transparent)
    p = QPainter(out)
    p.setRenderHint(QPainter.Antialiasing)
    clip = QPainterPath()
    clip.addRoundedRect(QRectF(0, 0, pm.width(), pm.height()), radius, radius)
    p.setClipPath(clip)
    p.drawPixmap(0, 0, pm)
    p.end()
    return out


def _typed(ext):
    color = "#4a5560"
    for c, exts in KIND_COLORS:
        if ext in exts:
            color = c
    pm = QPixmap(THUMB)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setBrush(QColor(color))
    p.setPen(Qt.NoPen)
    p.drawRoundedRect(0, 0, THUMB.width(), THUMB.height(), 10, 10)
    p.setPen(QColor("white"))
    f = QFont("Segoe UI", 12)
    f.setBold(True)
    p.setFont(f)
    p.drawText(pm.rect(), Qt.AlignCenter, (ext[1:] or "?").upper()[:5])
    p.end()
    return pm


def _image(path):
    reader = QImageReader(path)
    reader.setAutoTransform(True)
    size = reader.size()
    if size.isValid() and (size.width() > THUMB.width() * 2 or size.height() > THUMB.height() * 2):
        reader.setScaledSize(size.scaled(THUMB.width() * 2, THUMB.height() * 2, Qt.KeepAspectRatio))
    img = reader.read()
    if img.isNull():
        return None
    fit = QPixmap.fromImage(img).scaled(THUMB, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    canvas = QPixmap(THUMB)
    canvas.fill(Qt.transparent)
    p = QPainter(canvas)
    p.setRenderHint(QPainter.Antialiasing)
    p.setBrush(QColor(255, 255, 255, 18))
    p.setPen(Qt.NoPen)
    p.drawRoundedRect(0, 0, THUMB.width(), THUMB.height(), 10, 10)
    p.drawPixmap((THUMB.width() - fit.width()) // 2, (THUMB.height() - fit.height()) // 2, fit)
    p.end()
    return _rounded(canvas)


def folder_pixmap():
    pm = QPixmap(THUMB)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor("#3d6bb3"))
    p.drawRoundedRect(QRectF(6, 8, 32, 16), 5, 5)
    p.setBrush(QColor("#5b8fd9"))
    p.drawRoundedRect(QRectF(6, 14, 76, 46), 9, 9)
    p.end()
    return pm


def base_pixmap(entry):
    if entry["is_dir"]:
        key = ("dir",)
    else:
        key = (entry["path"], entry["mtime"], entry["size"])
    pm = _cache.get(key)
    if pm is not None:
        return pm
    if entry["is_dir"]:
        pm = folder_pixmap()
    else:
        pm = _image(entry["path"]) if entry["ext"] in IMAGE_EXT and os.path.exists(entry["path"]) else None
        if pm is None:
            pm = _typed(entry["ext"])
    if len(_cache) > 300:
        _cache.clear()
    _cache[key] = pm
    return pm


def compose(entry, fav=False, pinned=False):
    pm = QPixmap(base_pixmap(entry))
    if fav or pinned:
        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing)
        f = QFont("Segoe UI", 8)
        f.setBold(True)
        p.setFont(f)
        x = pm.width() - 20
        if fav:
            p.setBrush(QColor("#ffd43b"))
            p.setPen(Qt.NoPen)
            p.drawEllipse(x, 3, 17, 17)
            p.setPen(QColor("#4a3500"))
            p.drawText(QRectF(x, 3, 17, 17), Qt.AlignCenter, "♥")
            x -= 19
        if pinned:
            p.setBrush(QColor("#35c3e8"))
            p.setPen(Qt.NoPen)
            p.drawEllipse(x, 3, 17, 17)
            p.setPen(QColor("#06222c"))
            p.drawText(QRectF(x, 3, 17, 17), Qt.AlignCenter, "P")
        p.end()
    return pm
