"""Thành phần giao diện dùng chung."""
import os
import time

from . import native_drag
from PySide6.QtCore import QMimeData, QPoint, QUrl, Qt, Signal
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
USE_NATIVE = False  # thử nghiệm: kéo kiểu Windows gốc. Mặc định dùng cách chuẩn của Qt.


def start_file_drag(widget, paths, pixmap=None):
    """Kéo tệp THẬT ra ngoài (Màn hình chính, File Explorer, Moho...) bằng cách chuẩn:
    đưa cho hệ điều hành danh sách đường dẫn tệp thật (QUrl.fromLocalFile).
    CHỈ cho phép SAO CHÉP: tài liệu Qt nói hành động mặc định được đề xuất theo thứ tự Di chuyển,
    Sao chép, Liên kết, nên nếu cho phép Di chuyển thì Explorer có thể chuyển mất tệp gốc.
    Trả về (tên kiểu thả, số ms)."""
    paths = [p for p in paths if os.path.exists(p)]
    if not paths:
        return "Ignore", 0
    if USE_NATIVE and native_drag.available():
        try:
            return native_drag.drag_files(int(widget.window().winId()), paths)
        except OSError:
            pass
    native_drag.last_info.clear()
    native_drag.last_info["kieu"] = "qt"
    result = _qt_drag(widget, paths, pixmap)
    from .moho_bridge import window_exe_at_cursor
    native_drag.last_info["tha_vao"] = window_exe_at_cursor()
    return result


def _qt_drag(widget, paths, pixmap=None):
    md = QMimeData()
    md.setUrls([QUrl.fromLocalFile(os.path.abspath(p)) for p in paths])
    drag = QDrag(widget)
    drag.setMimeData(md)
    if pixmap is not None and not pixmap.isNull():
        drag.setPixmap(pixmap)
        drag.setHotSpot(QPoint(pixmap.width() // 2, pixmap.height() // 2))
    t0 = time.monotonic()
    result = drag.exec(Qt.CopyAction, Qt.CopyAction)
    return ACTION_NAMES.get(result, "Ignore"), int((time.monotonic() - t0) * 1000)


class DragChip(QLabel):
    """Ô để kéo một tệp (do provider() trả về) sang ứng dụng khác như Moho."""

    done = Signal(object, str, int)  # đường dẫn, kiểu thả, số ms

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
            action, ms = start_file_drag(self, [path], self.grab())
            self.done.emit(path, action, ms)

    def mouseReleaseEvent(self, _e):
        self._press = None
