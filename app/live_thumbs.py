"""Thẻ chuyển động: GIF và video luôn chạy trên thẻ; âm thanh phát khi rê chuột vào."""
import time

from PySide6.QtCore import QObject, QUrl
from PySide6.QtGui import QIcon, QMovie, QPixmap

from .fsbrowse import media_kind
from .thumbs import frame_card


class LiveThumbs(QObject):
    MAX_GIF, MAX_VIDEO = 16, 4

    def __init__(self, listw):
        super().__init__(listw)
        self.list = listw
        self.enabled = True
        self.movies = {}
        self.videos = {}

    def stop_all(self):
        for m in self.movies.values():
            m.stop()
            m.deleteLater()
        self.movies = {}
        for player, sink in self.videos.values():
            player.stop()
            player.deleteLater()
            sink.deleteLater()
        self.videos = {}

    def start(self, pairs):
        """pairs: danh sách (hàng, entry) của trang đang hiển thị."""
        if not self.enabled:
            return
        gifs = videos = 0
        for row, e in pairs:
            if e["is_dir"]:
                continue
            kind = media_kind(e["ext"])
            if kind == "gif" and gifs < self.MAX_GIF and self._start_gif(row, e):
                gifs += 1
            elif kind == "video" and videos < self.MAX_VIDEO and self._start_video(row, e):
                videos += 1

    def _set_icon(self, row, pm):
        it = self.list.item(row)
        if it is not None and not pm.isNull():
            it.setIcon(QIcon(frame_card(pm)))

    def _start_gif(self, row, e):
        m = QMovie(e["path"])
        if not m.isValid():
            return False
        m.setParent(self)
        m.frameChanged.connect(lambda _n=0, r=row, mv=m: self._set_icon(r, mv.currentPixmap()))
        m.start()
        self.movies[row] = m
        return True

    def _start_video(self, row, e):
        try:
            from PySide6.QtMultimedia import QMediaPlayer, QVideoSink
            player = QMediaPlayer(self)
            sink = QVideoSink(self)
            player.setVideoSink(sink)  # không gắn đầu ra âm thanh nên video im lặng
            last = [0.0]

            def on_frame(frame, r=row):
                now = time.monotonic()
                if now - last[0] < 0.08:
                    return
                last[0] = now
                img = frame.toImage()
                if not img.isNull():
                    self._set_icon(r, QPixmap.fromImage(img))

            sink.videoFrameChanged.connect(on_frame)
            try:
                player.setLoops(-1)
            except Exception:
                pass
            player.setSource(QUrl.fromLocalFile(e["path"]))
            player.play()
            self.videos[row] = (player, sink)
            return True
        except Exception:
            return False


class HoverAudio(QObject):
    """Phát âm thanh khi rê chuột vào thẻ, dừng khi rời đi."""

    def __init__(self, parent):
        super().__init__(parent)
        self.player = self.out = None
        self.current = None

    def play(self, path):
        try:
            if self.player is None:
                from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
                self.player = QMediaPlayer(self)
                self.out = QAudioOutput(self)
                self.out.setVolume(0.8)
                self.player.setAudioOutput(self.out)
            if path != self.current:
                self.player.setSource(QUrl.fromLocalFile(path))
                self.current = path
            self.player.setPosition(0)
            self.player.play()
        except Exception:
            self.current = None

    def stop(self):
        if self.player is not None:
            self.player.stop()
        self.current = None
