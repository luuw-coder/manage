"""Cắt âm thanh: hiện dạng sóng, phóng to/thu nhỏ, bôi đen đoạn cần dùng, nghe thử,
xuất thành tệp WAV MỚI hoặc kéo thẳng sang Moho. Tệp gốc không bao giờ bị thay đổi."""
import array
import ctypes
import math
import os

from PySide6.QtCore import QPointF, QRectF, QSize, QTimer, QUrl, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QApplication, QDoubleSpinBox, QHBoxLayout, QLabel, QPushButton, QScrollBar, QVBoxLayout, QWidget,
)

from . import audio_tools as at
from . import cleanup, drag_log, send_to_app
from .icons import make_icon
from .theme import QSS
from .widgets import ElidedLabel, start_file_drag

STEPS = [0.01, 0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10, 30, 60, 120, 300, 600]


def _buffer_bytes(buf):
    """Lấy byte từ QAudioBuffer, thử vài cách vì mỗi bản PySide6 trả về kiểu khác nhau."""
    n = buf.byteCount()
    ptr = buf.constData()
    attempts = (
        lambda: bytes(ptr),
        lambda: ctypes.string_at(int(ptr), n),
        lambda: bytes(memoryview(ptr)),
    )
    for fn in attempts:
        try:
            data = fn()
            if len(data) == n:
                return data
        except Exception:
            continue
    return None


class WaveformWidget(QWidget):
    selectionChanged = Signal()
    viewChanged = Signal()
    clickedFrame = Signal(int)
    fileDragged = Signal(object, str, int)  # đường dẫn, kiểu thả, số ms

    def __init__(self):
        super().__init__()
        self.drag_provider = None  # trả về đường dẫn tệp WAV của đoạn đang chọn
        self.setMinimumHeight(190)
        self.setMouseTracking(True)
        self.setCursor(Qt.IBeamCursor)
        self.pcm = self.mono = self.peaks = None
        self.view_start, self.view_len = 0, 1
        self.sel = None
        self.cursor_frame = None
        self._drag = None

    # ---- dữ liệu / khung nhìn
    def set_pcm(self, pcm):
        self.pcm, self.mono = pcm, pcm.mono()
        self.peaks = at.Peaks(self.mono)
        self.sel, self.cursor_frame = None, None
        self.fit()
        self.selectionChanged.emit()

    def total(self):
        return self.pcm.frames if self.pcm else 0

    def fit(self):
        self.view_start, self.view_len = 0, max(1, self.total())
        self._changed()

    def _changed(self):
        self.update()
        self.viewChanged.emit()

    def _clamp(self):
        total = self.total()
        self.view_len = min(max(1, self.view_len), max(1, total))
        self.view_start = max(0, min(self.view_start, max(0, total - self.view_len)))

    def zoom(self, factor, center=None):
        if not self.pcm:
            return
        total = self.total()
        c = center if center is not None else self.view_start + self.view_len / 2
        new_len = int(min(total, max(min(total, 64), self.view_len * factor)))
        ratio = (c - self.view_start) / max(1, self.view_len)
        self.view_start, self.view_len = int(c - ratio * new_len), max(1, new_len)
        self._clamp()
        self._changed()

    def pan_to(self, start):
        self.view_start = int(start)
        self._clamp()
        self._changed()

    def x_to_frame(self, x):
        return int(self.view_start + x * self.view_len / max(1, self.width()))

    def frame_to_x(self, f):
        return (f - self.view_start) * self.width() / max(1, self.view_len)

    def set_selection(self, a, b):
        total = self.total()
        a, b = sorted((max(0, min(int(a), total)), max(0, min(int(b), total))))
        self.sel = (a, b) if b - a >= 1 else None
        self.update()
        self.selectionChanged.emit()

    def selection_seconds(self):
        if not (self.sel and self.pcm):
            return None
        return self.sel[0] / self.pcm.rate, self.sel[1] / self.pcm.rate

    # ---- vẽ
    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = self.rect()
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#0e1424"))
        p.drawRoundedRect(r, 10, 10)
        if not self.pcm:
            p.setPen(QColor("#8fa0bf"))
            p.drawText(r, Qt.AlignCenter, "Đang đọc âm thanh...")
            p.end()
            return
        w, plot_h = r.width(), r.height() - 22
        mid = plot_h / 2
        cols = at.column_peaks(self.mono, self.peaks, self.view_start, self.view_start + self.view_len, w)
        p.setPen(QPen(QColor("#5fd0ee"), 1))
        for x, (lo, hi) in enumerate(cols):
            y1, y2 = mid - hi / 32768 * mid * 0.95, mid - lo / 32768 * mid * 0.95
            p.drawLine(QPointF(x + 0.5, y1), QPointF(x + 0.5, max(y2, y1 + 1)))
        if self.sel:
            xa, xb = self.frame_to_x(self.sel[0]), self.frame_to_x(self.sel[1])
            left, right = max(0.0, xa), min(float(w), xb)
            if right > left:
                p.fillRect(QRectF(left, 0, right - left, plot_h), QColor(224, 168, 74, 70))
            p.setPen(QPen(QColor("#e0a84a"), 2))
            for x in (xa, xb):
                if 0 <= x <= w:
                    p.drawLine(QPointF(x, 0), QPointF(x, plot_h))
        if self.cursor_frame is not None:
            x = self.frame_to_x(self.cursor_frame)
            if 0 <= x <= w:
                p.setPen(QPen(QColor("#ffffff"), 1))
                p.drawLine(QPointF(x, 0), QPointF(x, plot_h))
        self._ruler(p, w, r.height())
        p.end()

    def _ruler(self, p, w, h):
        rate = self.pcm.rate
        sec_per_view = self.view_len / rate
        px_per_sec = w / max(1e-9, sec_per_view)
        step = next((s for s in STEPS if s * px_per_sec >= 80), STEPS[-1])
        t = math.ceil((self.view_start / rate) / step) * step
        p.setPen(QColor("#8fa0bf"))
        end = (self.view_start + self.view_len) / rate
        while t <= end:
            x = (t - self.view_start / rate) * px_per_sec
            p.drawLine(QPointF(x, h - 22), QPointF(x, h - 17))
            label = f"{t:.2f}s" if step < 1 else (f"{t:.0f}s" if step < 60 else f"{int(t // 60)}:{int(t % 60):02d}")
            p.drawText(QPointF(x + 3, h - 4), label)
            t += step

    # ---- chuột
    def mousePressEvent(self, e):
        if not self.pcm or e.button() != Qt.LeftButton:
            return
        x = e.position().x()
        if self.sel:
            xa, xb = self.frame_to_x(self.sel[0]), self.frame_to_x(self.sel[1])
            if abs(x - xa) <= 7:
                self._drag = ("a",)
                return
            if abs(x - xb) <= 7:
                self._drag = ("b",)
                return
            if self.drag_provider and xa + 7 < x < xb - 7:
                self._drag = ("file", x)
                return
        self._drag = ("new", self.x_to_frame(x), x)

    def mouseMoveEvent(self, e):
        if not self.pcm:
            return
        x = max(0.0, min(e.position().x(), float(self.width())))
        f = self.x_to_frame(x)
        if self._drag is None:
            xa = self.frame_to_x(self.sel[0]) if self.sel else -99
            xb = self.frame_to_x(self.sel[1]) if self.sel else -99
            if self.sel and (abs(x - xa) <= 7 or abs(x - xb) <= 7):
                self.setCursor(Qt.SizeHorCursor)
            elif self.sel and self.drag_provider and xa + 7 < x < xb - 7:
                self.setCursor(Qt.OpenHandCursor)
            else:
                self.setCursor(Qt.IBeamCursor)
            return
        kind = self._drag[0]
        if kind == "file":
            if abs(x - self._drag[1]) >= QApplication.startDragDistance():
                self._drag = None
                path = self.drag_provider()
                if path:
                    action, ms = start_file_drag(self, [path], self._drag_pixmap())
                    self.fileDragged.emit(path, action, ms)
            return
        if kind == "new":
            if abs(x - self._drag[2]) > 3:
                self.set_selection(self._drag[1], f)
            return
        a, b = self.sel
        other = b if kind == "a" else a
        self.set_selection(f, other)
        if kind == "a" and f > other:
            self._drag = ("b",)
        elif kind == "b" and f < other:
            self._drag = ("a",)

    def _drag_pixmap(self):
        pm = QPixmap(170, 30)
        pm.fill(QColor("#e0a84a"))
        p = QPainter(pm)
        p.setPen(QColor("#2a1d05"))
        p.drawText(pm.rect(), Qt.AlignCenter, "♪ đoạn âm thanh đã chọn")
        p.end()
        return pm

    def mouseReleaseEvent(self, e):
        if self._drag and self._drag[0] == "file":
            self.cursor_frame = self.x_to_frame(e.position().x())
            self.clickedFrame.emit(self.cursor_frame)
            self.update()
        if self._drag and self._drag[0] == "new" and abs(e.position().x() - self._drag[2]) <= 3:
            self.sel = None
            self.cursor_frame = self.x_to_frame(e.position().x())
            self.selectionChanged.emit()
            self.clickedFrame.emit(self.cursor_frame)
            self.update()
        self._drag = None

    def wheelEvent(self, e):
        if self.pcm:
            self.zoom(0.8 if e.angleDelta().y() > 0 else 1.25, self.x_to_frame(e.position().x()))
        e.accept()


class AudioSliceWindow(QWidget):
    def __init__(self, db, path, parent=None):
        super().__init__(parent)
        self.setWindowFlag(Qt.Window, True)
        self.setObjectName("root")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet(QSS)
        self.setWindowTitle("Cắt âm thanh")
        self.resize(820, 520)
        self.db, self.path = db, path
        self.pcm = None
        self.player = self.audio_out = None
        self._stop_at = None
        self._last = (None, None)
        self._created = None
        self._decoder = None
        self._chunks = []
        self._fmt = None
        self._sync = False

        v = QVBoxLayout(self)
        v.setContentsMargins(14, 12, 14, 12)
        v.setSpacing(8)
        self.name_label = ElidedLabel(os.path.basename(path))
        self.status = QLabel("")
        self.status.setObjectName("muted")
        v.addWidget(self.name_label)
        v.addWidget(self.status)

        self.wave = WaveformWidget()
        self.wave.selectionChanged.connect(self._sel_changed)
        self.wave.viewChanged.connect(self._view_changed)
        self.wave.clickedFrame.connect(self._seek_to)
        v.addWidget(self.wave, 1)
        self.scroll = QScrollBar(Qt.Horizontal)
        self.scroll.valueChanged.connect(self._scrolled)
        v.addWidget(self.scroll)

        row = QHBoxLayout()
        for icon, tip, fn in (("zoomin", "Phóng to (hoặc lăn chuột lên)", lambda: self.wave.zoom(0.5)),
                              ("zoomout", "Thu nhỏ (hoặc lăn chuột xuống)", lambda: self.wave.zoom(2.0)),
                              ("fitw", "Vừa khung: xem cả bài", self.wave.fit)):
            b = QPushButton(" " + tip.split(" (")[0])
            b.setIcon(make_icon(icon, "#e6ecf7", 16))
            b.setIconSize(QSize(16, 16))
            b.setToolTip(tip)
            b.clicked.connect(lambda _=False, f=fn: f())
            row.addWidget(b)
        all_btn = QPushButton("Chọn cả bài")
        all_btn.clicked.connect(lambda: self.pcm and self.wave.set_selection(0, self.pcm.frames))
        row.addWidget(all_btn)
        row.addStretch(1)
        v.addLayout(row)

        sel = QHBoxLayout()
        self.start_spin, self.end_spin = QDoubleSpinBox(), QDoubleSpinBox()
        for sp in (self.start_spin, self.end_spin):
            sp.setDecimals(3)
            sp.setSingleStep(0.01)
            sp.setSuffix(" s")
            sp.setRange(0, 0)
            sp.valueChanged.connect(self._spin_changed)
        self.dur_label = QLabel("Chưa chọn đoạn nào: kéo chuột trên hình sóng để bôi đen")
        self.dur_label.setObjectName("muted")
        sel.addWidget(QLabel("Từ"))
        sel.addWidget(self.start_spin)
        sel.addWidget(QLabel("đến"))
        sel.addWidget(self.end_spin)
        sel.addWidget(self.dur_label, 1)
        v.addLayout(sel)

        play = QHBoxLayout()
        self.play_sel_btn = QPushButton("Nghe đoạn chọn")
        self.play_sel_btn.clicked.connect(self.play_selection)
        self.play_all_btn = QPushButton("Nghe cả bài")
        self.play_all_btn.clicked.connect(self.play_all)
        self.stop_btn = QPushButton("Dừng")
        self.stop_btn.clicked.connect(self.stop)
        for b in (self.play_sel_btn, self.play_all_btn, self.stop_btn):
            play.addWidget(b)
        play.addStretch(1)
        v.addLayout(play)

        self.wave.drag_provider = self.export_for_drag
        self.wave.fileDragged.connect(self._dragged)
        note = QLabel("Bôi đen đoạn cần dùng, rồi GIỮ CHUỘT KÉO THẲNG vùng bôi đen sang cửa sổ Moho. "
                      "Tool tự tạo tệp WAV mới cho đoạn đó, tệp gốc không bị thay đổi.")
        note.setWordWrap(True)
        note.setObjectName("muted")
        v.addWidget(note)
        self._load()

    # ---- đọc âm thanh
    def _load(self):
        self.status.setText("Đang đọc âm thanh...")
        pcm = at.load_pcm(self.path)
        if pcm is not None:
            self._set_pcm(pcm)
        else:
            self._start_qt_decode()

    def _set_pcm(self, pcm):
        if pcm.frames == 0:
            self.status.setText("Tệp âm thanh rỗng hoặc không đọc được.")
            return
        self.pcm = pcm
        self.wave.set_pcm(pcm)
        for sp in (self.start_spin, self.end_spin):
            sp.setRange(0, pcm.duration)
        self.status.setText(f"Sẵn sàng · {at.fmt_time(pcm.duration)} · {pcm.rate} Hz · "
                            f"{'stereo' if pcm.channels == 2 else str(pcm.channels) + ' kênh'}")

    def _fail(self, msg):
        self.status.setText(msg + " Hãy thử tệp WAV, MP3, OGG hoặc FLAC.")

    def _start_qt_decode(self):
        try:
            from PySide6.QtMultimedia import QAudioDecoder, QAudioFormat
            dec = QAudioDecoder(self)
            fmt = QAudioFormat()
            fmt.setSampleRate(44100)
            fmt.setChannelCount(2)
            fmt.setSampleFormat(QAudioFormat.SampleFormat.Int16)
            dec.setAudioFormat(fmt)
            dec.setSource(QUrl.fromLocalFile(self.path))
            self._decoder, self._chunks, self._fmt = dec, [], None
            dec.bufferReady.connect(self._on_buffer)
            dec.finished.connect(self._on_decoded)
            dec.error.connect(lambda *_a: self._fail("Không giải mã được âm thanh này."))
            dec.start()
        except Exception:
            self._fail("Máy này chưa có bộ giải mã âm thanh của Qt.")

    def _on_buffer(self):
        buf = self._decoder.read()
        if not buf.isValid():
            return
        from PySide6.QtMultimedia import QAudioFormat
        f = buf.format()
        if f.sampleFormat() != QAudioFormat.SampleFormat.Int16:
            self._decoder.stop()
            self._fail("Định dạng âm thanh chưa hỗ trợ.")
            return
        self._fmt = (f.sampleRate(), f.channelCount())
        data = _buffer_bytes(buf)
        if data is None:
            self._decoder.stop()
            self._fail("Không lấy được dữ liệu từ bộ giải mã.")
            return
        self._chunks.append(data)

    def _on_decoded(self):
        raw = b"".join(self._chunks)
        if not raw or not self._fmt:
            self._fail("Không đọc được âm thanh này.")
            return
        arr = array.array("h")
        arr.frombytes(raw[:len(raw) // 2 * 2])
        if not at.BYTEORDER_LITTLE:
            arr.byteswap()
        self._set_pcm(at.Pcm(arr, self._fmt[0], self._fmt[1]))

    # ---- đồng bộ giao diện
    def _view_changed(self):
        self._sync = True
        total, vl = self.wave.total(), self.wave.view_len
        self.scroll.setRange(0, max(0, total - vl))
        self.scroll.setPageStep(vl)
        self.scroll.setValue(self.wave.view_start)
        self._sync = False

    def _scrolled(self, v):
        if not self._sync:
            self.wave.pan_to(v)

    def _sel_changed(self):
        sel = self.wave.selection_seconds()
        self._sync = True
        if sel:
            self.start_spin.setValue(sel[0])
            self.end_spin.setValue(sel[1])
            self.dur_label.setText(f"Đoạn chọn dài {at.fmt_time(sel[1] - sel[0])}")
        else:
            self.dur_label.setText("Chưa chọn đoạn nào: kéo chuột trên hình sóng để bôi đen")
        self._sync = False

    def _spin_changed(self):
        if self._sync or not self.pcm:
            return
        self.wave.set_selection(self.pcm.frame_at(self.start_spin.value()), self.pcm.frame_at(self.end_spin.value()))

    # ---- nghe thử
    def _ensure_player(self):
        if self.player is None:
            from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
            self.player = QMediaPlayer(self)
            self.audio_out = QAudioOutput(self)
            self.audio_out.setVolume(0.9)
            self.player.setAudioOutput(self.audio_out)
            self.player.setSource(QUrl.fromLocalFile(self.path))
            self.player.positionChanged.connect(self._on_pos)
        return self.player

    def _play_from(self, start_s, stop_s):
        try:
            pl = self._ensure_player()
        except Exception:
            self.status.setText("Máy này chưa có thành phần phát âm thanh của Qt.")
            return
        self._stop_at = None if stop_s is None else int(stop_s * 1000)
        pl.setPosition(int(start_s * 1000))
        pl.play()

    def play_selection(self):
        sel = self.wave.selection_seconds()
        if not sel:
            self.status.setText("Hãy bôi đen một đoạn trước.")
            return
        self._play_from(*sel)

    def play_all(self):
        if self.pcm:
            self._play_from(0, None)

    def stop(self):
        if self.player is not None:
            self.player.stop()
        self._stop_at = None

    def _on_pos(self, ms):
        if self.pcm:
            self.wave.cursor_frame = int(ms / 1000 * self.pcm.rate)
            self.wave.update()
        if self._stop_at is not None and ms >= self._stop_at:
            self.player.pause()
            self._stop_at = None

    def _seek_to(self, frame):
        if self.player is not None and self.pcm:
            self.player.setPosition(int(frame / self.pcm.rate * 1000))

    # ---- xuất đoạn (không đụng tệp gốc)
    def _export_dir(self):
        d = self.db.get_setting("export_dir") or os.path.join(os.path.dirname(self.db.path), "exports")
        os.makedirs(d, exist_ok=True)
        return d

    def export_current(self):
        sel = self.wave.selection_seconds()
        if not (sel and self.pcm):
            self.status.setText("Hãy bôi đen một đoạn trước.")
            return None
        a, b = sorted(sel)
        if a <= 0.05 and b >= self.pcm.duration - 0.05:  # chọn cả bài: kéo luôn tệp gốc, không tạo tệp mới
            self._created = None
            return self.path
        key = (round(a, 3), round(b, 3))
        if self._last[0] == key and self._last[1] and os.path.exists(self._last[1]):
            return self._last[1]
        fmt = self.db.get_setting("slice_format", "mp3")
        folder = self._export_dir()
        planned = at.segment_path(self.pcm, a, b, folder, self.path, fmt)
        existed = os.path.exists(planned)
        out = at.export_segment(self.pcm, a, b, folder, self.path, fmt)
        self._created = None if existed else out   # chỉ tệp do lần kéo này tạo ra mới được tự xóa nếu kéo hụt
        self._last = (key, out)
        try:
            self.status.setText(f"Đoạn cắt: {cleanup.human(os.path.getsize(out))} ({os.path.splitext(out)[1][1:].upper()})")
        except OSError:
            pass
        return out

    def export_for_drag(self):
        try:
            return self.export_current()
        except (ValueError, OSError) as e:
            self.status.setText(f"Không xuất được: {e}")
            return None

    def _dragged(self, path, action, ms):
        if action == "Ignore" and self._created and os.path.abspath(path) == os.path.abspath(self._created):
            self._delete_cut(path)  # kéo hụt (Moho không nhận): xóa ngay tệp vừa tạo, không để rác
            self._created = None
        drag_log.after_drag(os.path.dirname(self.db.path), [path], action, ms, False, None,
                        send_to_app.active_profile(self.db)["keywords"])
        self.status.setText("Đã kéo đoạn âm thanh sang Moho." if action != "Ignore"
                            else "Moho chưa nhận. Hãy thả vào cửa sổ Moho (xem keo.log nếu vẫn không được).")
        if action != "Ignore" and self.db.get_setting(cleanup.SETTING, "keep") == "now":
            QTimer.singleShot(8000, lambda p=path: self._delete_cut(p))  # đợi Moho đọc xong rồi mới xóa

    def _delete_cut(self, path):
        try:
            os.remove(path)
            self._last = ((), None)
        except OSError:
            pass

    def closeEvent(self, e):
        self.stop()
        if self._decoder is not None:
            self._decoder.stop()
        super().closeEvent(e)
