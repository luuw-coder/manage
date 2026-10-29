"""Khung web nhúng trong phần mềm (dùng cho Hỏi AI), mỗi tài khoản một phiên đăng nhập riêng.

Dùng QtWebEngine (có sẵn trong PySide6). Nếu máy không có hoặc bị tắt thì available() = False và
phần mềm tự quay về mở cửa sổ Chrome/Edge riêng.
"""
import os
import re


def available():
    if os.environ.get("MM_NO_WEBENGINE"):
        return False
    try:
        from PySide6 import QtWebEngineCore, QtWebEngineWidgets  # noqa: F401
        return True
    except Exception:
        return False


def clean_user_agent(ua):
    """Bỏ phần 'QtWebEngine/x.y.z' khỏi chuỗi nhận diện để trang web coi đây là trình duyệt Chromium thường."""
    return re.sub(r"\s*QtWebEngine/[\d.]+", "", ua or "").strip()


class WebHost:
    """Giữ các trang web theo tài khoản; mỗi tài khoản có hồ sơ lưu đăng nhập riêng trong profiles_dir."""

    def __init__(self, profiles_dir, parent):
        from PySide6.QtWebEngineWidgets import QWebEngineView
        self.profiles_dir = profiles_dir
        self.parent = parent
        self.view = QWebEngineView(parent)
        self.pages = {}     # id tài khoản -> (profile, page)

    def show_account(self, acc):
        from PySide6.QtCore import QUrl
        from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile
        entry = self.pages.get(acc["id"])
        if entry is None:
            folder = os.path.join(self.profiles_dir, f"web{acc['id']}")
            os.makedirs(folder, exist_ok=True)
            prof = QWebEngineProfile(f"acc{acc['id']}", self.parent)
            prof.setPersistentStoragePath(folder)
            prof.setCachePath(os.path.join(folder, "cache"))
            prof.setPersistentCookiesPolicy(QWebEngineProfile.ForcePersistentCookies)
            prof.setHttpUserAgent(clean_user_agent(prof.httpUserAgent()))
            page = QWebEnginePage(prof, self.view)
            page.load(QUrl(acc["url"]))
            entry = self.pages[acc["id"]] = (prof, page)
        self.view.setPage(entry[1])

    def dispose(self):
        """Hủy trang trước hồ sơ (thứ tự Qt yêu cầu) khi đóng cửa sổ."""
        self.view.setPage(None)
        for prof, page in self.pages.values():
            page.deleteLater()   # hủy trang -> tiến trình trình duyệt phụ kết thúc, trả lại RAM
        self.pages.clear()
        self.view.deleteLater()


def chromium_flags():
    """Các cờ giúp trình duyệt nhúng ít tốn RAM hơn (mỗi trang một tiến trình, bỏ các tác vụ nền)."""
    return "--renderer-process-limit=1 --disable-background-networking --disable-sync --no-pings --disable-default-apps"


def apply_memory_flags():
    """Gọi trước khi tạo QApplication."""
    if not os.environ.get("QTWEBENGINE_CHROMIUM_FLAGS"):
        os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = chromium_flags()
