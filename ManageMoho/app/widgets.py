"""Thành phần giao diện dùng chung."""
import time

from PySide6.QtCore import QMimeData, QUrl, Qt
from PySide6.QtGui import QColor, QDrag, QPainter
from PySide6.QtWidgets import QApplication, QLabel, QSizePolicy


class ElidedLabel(QLabel):
    """Nhãn tự cắt chữ bằng dấu … khi hẹp."""

    def __init__(self, text=""):
        super().__init__("")
        self._full = text
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)

    def setFullText(self, text):
        self._full = text
        self.setToolTip(text)
        self.update()

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setPen(QColor("#8fa0bf") if self.objectName() == "muted" else QColor("#e6ecf7"))
        p.setFont(self.font())
        p.drawText(self.rect(), Qt.AlignVCenter | Qt.AlignLeft,
                   self.fontMetrics().elidedText(self._full, Qt.ElideMiddle, max(10, self.width())))
        p.end()


ACTION_NAMES = {Qt.CopyAction: "Copy", Qt.MoveAction: "Move", Qt.LinkAction: "Link", Qt.IgnoreAction: "Ignore"}


def start_file_drag(widget, paths, pixmap=None):
    """Kéo thả tệp THẬT ra ngoài (sang Moho, File Explorer...) như kéo từ thư mục máy tính.
    Cho phép Copy/Move/Link (mặc định Copy) để các ứng dụng chỉ nhận một kiểu thả vẫn nhận được.
    Phần mềm không bao giờ tự xóa hay di chuyển tệp gốc. Trả về (tên kiểu thả, số ms)."""
    md = QMimeData()
    md.setUrls([QUrl.fromLocalFile(p) for p in paths])
    drag = QDrag(widget)
    drag.setMimeData(md)
    if pixmap is not None and not pixmap.isNull():
        drag.setPixmap(pixmap)
    t0 = time.monotonic()
    result = drag.exec(Qt.CopyAction | Qt.MoveAction | Qt.LinkAction, Qt.CopyAction)
    return ACTION_NAMES.get(result, "Ignore"), int((time.monotonic() - t0) * 1000)


class DragChip(QLabel):
    """Ô để kéo một tệp (do provider() trả về) sang ứng dụng khác như Moho."""

    def __init__(self, text, provider):
        super().__init__(text)
        self.provider = provider
        self.setObjectName("dragChip")
        self.setAlignment(Qt.AlignCenter)
        self.setCursor(Qt.OpenHandCursor)
        self.setToolTip("Giữ chuột và kéo sang cửa sổ Moho")
        self._press = None

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._press = e.position().toPoint()

    def mouseMoveEvent(self, e):
        if self._press is None or not (e.buttons() & Qt.LeftButton):
            return
        if (e.position().toPoint() - self._press).manhattanLength() < QApplication.startDragDistance():
            return
        self._press = None
        path = self.provider()
        if path:
            start_file_drag(self, [path], self.grab())

    def mouseReleaseEvent(self, _e):
        self._press = None
