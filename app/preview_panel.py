"""Bảng thông tin trượt lên từ dưới cửa sổ: xem trước ảnh / GIF / video / âm thanh / thư mục."""
import os
import time

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QRect, QSize, Qt, QUrl
from PySide6.QtGui import QImageReader, QMovie, QPainter, QPixmap
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QSlider, QStackedWidget, QToolButton, QVBoxLayout, QWidget,
)

from .fsbrowse import folder_summary, human_size, make_entry, media_kind
from .icons import make_icon
from .thumbs import base_pixmap, folder_pixmap
from .widgets import DragChip, ElidedLabel

PAGE_IMAGE, PAGE_VIDEO, PAGE_AUDIO, PAGE_FOLDER, PAGE_OTHER = range(5)


def fmt_ms(ms):
    s = max(0, int(ms // 1000))
    return f"{s // 60:02d}:{s % 60:02d}"


class PreviewPanel(QFrame):
    def __init__(self, main):
        super().__init__(main)
        self.main = main
        self.entry = None
        self.extra = []
        self.player = self.audio_out = self.video = self.movie = None
        self._QMediaPlayer = None
        self._closing = False
        self.setObjectName("previewPanel")
        self.setAttribute(Qt.WA_StyledBackground, True)

        v = QVBoxLayout(self)
        v.setContentsMargins(12, 10, 12, 10)
        v.setSpacing(8)
        top = QHBoxLayout()
        self.title = ElidedLabel("")
        self.chip = DragChip("Kéo vào Moho", self._drag_path)
        close = QToolButton()
        close.setIcon(make_icon("chevdown", "#e6ecf7", 18))
        close.setIconSize(QSize(18, 18))
        close.setToolTip("Đóng")
        close.setAccessibleName("Đóng bảng thông tin")
        close.clicked.connect(self.close_panel)
        top.addWidget(self.title, 1)
        top.addWidget(self.chip)
        top.addWidget(close)
        v.addLayout(top)

        self.stage = QStackedWidget()
        self.image_label = self._center_label()
        self.video_holder = QWidget()
        QVBoxLayout(self.video_holder).setContentsMargins(0, 0, 0, 0)
        self.audio_label = self._center_label()
        self.folder_label = self._center_label()
        self.other_label = self._center_label()
        for w in (self.image_label, self.video_holder, self.audio_label, self.folder_label, self.other_label):
            self.stage.addWidget(w)
        v.addWidget(self.stage, 1)

        self.controls = QWidget()
        cl = QHBoxLayout(self.controls)
        cl.setContentsMargins(0, 0, 0, 0)
        self.play_btn = QToolButton()
        self.play_btn.setIcon(make_icon("play", "#e6ecf7", 18))
        self.play_btn.setToolTip("Phát / tạm dừng")
        self.play_btn.setAccessibleName("Phát hoặc tạm dừng")
        self.play_btn.clicked.connect(self._toggle_play)
        self.seek = QSlider(Qt.Horizontal)
        self.seek.sliderMoved.connect(lambda ms: self.player and self.player.setPosition(ms))
        self.time_label = QLabel("00:00 / 00:00")
        self.time_label.setObjectName("muted")
        self.volume = QSlider(Qt.Horizontal)
        self.volume.setRange(0, 100)
        self.volume.setValue(80)
        self.volume.setFixedWidth(70)
        self.volume.setToolTip("Âm lượng")
        self.volume.valueChanged.connect(lambda x: self.audio_out and self.audio_out.setVolume(x / 100.0))
        for w in (self.play_btn, self.seek, self.time_label, self.volume):
            cl.addWidget(w, 1 if w is self.seek else 0)
        v.addWidget(self.controls)

        self.info = QLabel("")
        self.info.setObjectName("muted")
        self.info.setWordWrap(True)
        self.info.setTextInteractionFlags(Qt.TextSelectableByMouse)
        v.addWidget(self.info)

        row = QHBoxLayout()
        self.send_btn = QPushButton("Gửi sang Moho")
        self.send_btn.clicked.connect(lambda: self.entry and self.main.send_to_moho([self.entry["path"]]))
        self.folder_btn = QPushButton("Mở thư mục chứa")
        self.folder_btn.clicked.connect(self._open_folder)
        self.fav_btn = QPushButton("Yêu thích")
        self.fav_btn.setCheckable(True)
        self.fav_btn.clicked.connect(self._toggle_fav)
        self.pin_btn = QPushButton("Ghim")
        self.pin_btn.setCheckable(True)
        self.pin_btn.clicked.connect(self._toggle_pin)
        self.slice_btn = QPushButton("Cắt âm thanh")
        self.slice_btn.setObjectName("gold")
        self.slice_btn.clicked.connect(lambda: self.entry and self.main.open_audio_slice(self.entry["path"]))
        for b in (self.send_btn, self.folder_btn, self.fav_btn, self.pin_btn, self.slice_btn):
            row.addWidget(b)
        v.addLayout(row)

        self.anim = QPropertyAnimation(self, b"geometry")
        self.anim.setDuration(220)
        self.anim.setEasingCurve(QEasingCurve.OutCubic)
        self.anim.finished.connect(self._on_anim_done)
        self.hide()

    # ------------------------------------------------------------ tiện ích
    @staticmethod
    def _center_label():
        lb = QLabel()
        lb.setAlignment(Qt.AlignCenter)
        lb.setWordWrap(True)
        return lb

    def _drag_path(self):
        return self.entry["path"] if self.entry else None

    def is_open(self):
        return self.isVisible() and not self._closing

    def target_rect(self):
        h = min(self.main.height(), max(340, int(self.main.height() * 0.66)))
        return QRect(0, self.main.height() - h, self.main.width(), h)

    def stage_size(self):
        r = self.target_rect()
        return QSize(max(80, r.width() - 24), max(100, r.height() - 215))

    def reposition(self):
        if self.is_open():
            self.setGeometry(self.target_rect())

    # ------------------------------------------------------------ mở / đóng
    def open_entry(self, entry):
        self._stop_media()
        self.entry = entry
        self.extra = []
        self.title.setFullText(entry["label"])
        kind = "folder" if entry["is_dir"] else media_kind(entry["ext"])
        self.controls.setVisible(kind in ("video", "audio"))
        self.slice_btn.setVisible(kind == "audio")
        self.send_btn.setVisible(not entry["is_dir"])
        self.folder_btn.setText("Mở thư mục" if entry["is_dir"] else "Mở thư mục chứa")
        self.fav_btn.setChecked(bool(entry.get("fav")))
        self.pin_btn.setChecked(bool(entry.get("pinned")))
        {"folder": self._show_folder, "image": self._show_image, "gif": self._show_gif,
         "video": self._show_video, "audio": self._show_audio}.get(kind, self._show_other)(entry)
        self._set_info()
        self._slide_in()

    def _slide_in(self):
        rect = self.target_rect()
        self.anim.stop()
        if not self.is_open():
            self._closing = False
            self.setGeometry(QRect(0, self.main.height(), rect.width(), rect.height()))
            self.show()
            self.raise_()
            self.anim.setStartValue(self.geometry())
            self.anim.setEndValue(rect)
            self.anim.start()
        else:
            self.setGeometry(rect)

    def close_panel(self):
        if not self.isVisible():
            return
        self._stop_media()
        self._closing = True
        self.anim.stop()
        self.anim.setStartValue(self.geometry())
        self.anim.setEndValue(QRect(0, self.main.height(), self.width(), self.height()))
        self.anim.start()

    def _on_anim_done(self):
        if self._closing:
            self.hide()
            self._closing = False

    def hard_close(self):
        self._stop_media()
        self.anim.stop()
        self._closing = False
        self.hide()

    # ------------------------------------------------------------ nội dung theo loại
    def _base_info(self, e):
        date = time.strftime("%d/%m/%Y %H:%M", time.localtime(e["mtime"])) if e["mtime"] else "—"
        lines = [f"Tên gốc: {e['name']}"]
        if e["label"] != e["name"]:
            lines.append(f"Tên hiển thị: {e['label']}")
        if not e["is_dir"]:
            lines.append(f"Định dạng: {(e['ext'][1:].upper() or '—')} · Dung lượng: {human_size(e['size'])}")
        lines.append(f"Sửa đổi (theo hệ thống tệp): {date}")
        lines.append(f"Đường dẫn: {e['path']}")
        return lines

    def _set_info(self):
        self.info.setText("\n".join(self._base_info(self.entry) + self.extra))

    def _fallback(self, e, message):
        pm = base_pixmap(e).scaled(176, 132, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.other_label.setPixmap(pm)
        self.extra.append(message)
        self.stage.setCurrentIndex(PAGE_OTHER)

    def _show_other(self, e):
        self._fallback(e, "Chưa xem trước được định dạng này trong phần mềm.")

    def _show_image(self, e):
        reader = QImageReader(e["path"])
        reader.setAutoTransform(True)
        size = reader.size()
        if size.isValid():
            self.extra.append(f"Kích thước ảnh: {size.width()} × {size.height()}")
            fit = size.scaled(self.stage_size(), Qt.KeepAspectRatio)
            if fit.width() < size.width():
                reader.setScaledSize(fit)
        img = reader.read()
        if img.isNull():
            self._fallback(e, "Không đọc được ảnh này.")
            return
        self.image_label.setPixmap(QPixmap.fromImage(img))
        self.stage.setCurrentIndex(PAGE_IMAGE)

    def _show_gif(self, e):
        movie = QMovie(e["path"])
        if not movie.isValid():
            self._fallback(e, "Không đọc được GIF này.")
            return
        movie.jumpToFrame(0)
        size = movie.currentImage().size()
        if size.isValid():
            self.extra.append(f"Kích thước: {size.width()} × {size.height()} · {movie.frameCount()} khung hình")
            fit = size.scaled(self.stage_size(), Qt.KeepAspectRatio)
            if fit.width() < size.width():
                movie.setScaledSize(fit)
        self.movie = movie
        self.image_label.setMovie(movie)
        movie.start()  # GIF tự chạy
        self.stage.setCurrentIndex(PAGE_IMAGE)

    def _show_folder(self, e):
        s = folder_summary(e["path"])
        if s["error"]:
            self._fallback(e, "Không mở được thư mục này.")
            return
        more = "+" if s["truncated"] else ""
        self.extra.append(f"Bên trong: {s['files']}{more} tệp · {s['dirs']}{more} thư mục con · "
                          f"{human_size(s['size'])} (chỉ tính tệp ngay trong thư mục)")
        cw, ch = 128, 96
        if s["images"]:
            canvas = QPixmap(cw * 3 + 8, ch * 2 + 4)
            canvas.fill(Qt.transparent)
            p = QPainter(canvas)
            for i, path in enumerate(s["images"]):
                ent = make_entry(path)
                if not ent:
                    continue
                pm = base_pixmap(ent).scaled(cw, ch, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                x, y = (i % 3) * (cw + 4), (i // 3) * (ch + 4)
                p.drawPixmap(x + (cw - pm.width()) // 2, y + (ch - pm.height()) // 2, pm)
            p.end()
        else:
            canvas = folder_pixmap().scaled(176, 132, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.folder_label.setPixmap(canvas)
        self.stage.setCurrentIndex(PAGE_FOLDER)

    # ------------------------------------------------------------ video / âm thanh
    def _ensure_player(self):
        if self.player is not None:
            return True
        try:
            from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
        except ImportError:
            return False
        self._QMediaPlayer = QMediaPlayer
        self.player = QMediaPlayer(self)
        self.audio_out = QAudioOutput(self)
        self.audio_out.setVolume(self.volume.value() / 100.0)
        self.player.setAudioOutput(self.audio_out)
        self.player.positionChanged.connect(self._on_pos)
        self.player.durationChanged.connect(self._on_dur)
        self.player.playbackStateChanged.connect(self._on_state)
        self.player.mediaStatusChanged.connect(self._on_status)
        return True

    def _show_video(self, e):
        try:
            if not self._ensure_player():
                raise ImportError
            if self.video is None:
                from PySide6.QtMultimediaWidgets import QVideoWidget
                self.video = QVideoWidget()
                self.video_holder.layout().addWidget(self.video)
                self.player.setVideoOutput(self.video)
            self.player.setSource(QUrl.fromLocalFile(e["path"]))
            self.stage.setCurrentIndex(PAGE_VIDEO)
            self.player.play()  # video tự chạy
        except Exception:
            self.controls.hide()
            self._fallback(e, "Máy này chưa có thành phần phát video của Qt.")

    def _show_audio(self, e):
        self.audio_label.setPixmap(make_icon("music", "#ffa94d", 64).pixmap(64, 64))
        self.stage.setCurrentIndex(PAGE_AUDIO)
        try:
            if not self._ensure_player():
                raise ImportError
            self.player.setSource(QUrl.fromLocalFile(e["path"]))
        except Exception:
            self.controls.hide()
            self.extra.append("Máy này chưa có thành phần phát âm thanh của Qt.")

    def _toggle_play(self):
        if not self.player:
            return
        if self.player.playbackState() == self._QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
        else:
            self.player.play()

    def _on_pos(self, ms):
        if not self.seek.isSliderDown():
            self.seek.setValue(ms)
        self.time_label.setText(f"{fmt_ms(ms)} / {fmt_ms(self.seek.maximum())}")

    def _on_dur(self, ms):
        self.seek.setRange(0, max(0, ms))
        self.time_label.setText(f"{fmt_ms(self.seek.value())} / {fmt_ms(ms)}")

    def _on_state(self, state):
        playing = state == self._QMediaPlayer.PlaybackState.PlayingState
        self.play_btn.setIcon(make_icon("pause" if playing else "play", "#e6ecf7", 18))

    def _on_status(self, status):
        try:
            if status == self._QMediaPlayer.MediaStatus.LoadedMedia and self.entry:
                from PySide6.QtMultimedia import QMediaMetaData
                res = self.player.metaData().value(QMediaMetaData.Key.Resolution)
                dur = self.player.duration()
                self.extra = [x for x in self.extra if not x.startswith("Thời lượng") and not x.startswith("Độ phân giải")]
                if dur:
                    self.extra.append(f"Thời lượng: {fmt_ms(dur)}")
                if res is not None and hasattr(res, "width") and res.width() > 0:
                    self.extra.append(f"Độ phân giải: {res.width()} × {res.height()}")
                self._set_info()
        except Exception:
            pass

    def _stop_media(self):
        if self.player is not None:
            self.player.stop()
            self.player.setSource(QUrl())
        if self.movie is not None:
            self.movie.stop()
            self.movie = None
        self.image_label.clear()
        self.seek.setValue(0)
        self.time_label.setText("00:00 / 00:00")

    # ------------------------------------------------------------ nút hành động
    def _open_folder(self):
        if self.entry:
            p = self.entry["path"]
            self.main.open_path(p if self.entry["is_dir"] else os.path.dirname(p))

    def _toggle_fav(self):
        if self.entry:
            on = self.fav_btn.isChecked()
            self.main.set_fav([self.entry], on)
            self.entry["fav"] = on

    def _toggle_pin(self):
        if self.entry:
            on = self.pin_btn.isChecked()
            self.main.set_pin([self.entry], on)
            self.entry["pinned"] = on
