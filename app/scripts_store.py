"""Kịch bản lưu thành tệp thật trong một thư mục của phần mềm.

Mỗi kịch bản có: tệp .txt (chữ thuần, luôn có) và tệp .html (giữ màu chữ, căn dòng... nếu có định dạng).
"""
import os
import re
import shutil

from .fsbrowse import natural_key

_INVALID = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
ENC = "utf-8-sig"  # có BOM để Notepad hiển thị đúng tiếng Việt


def sanitize_name(name):
    n = _INVALID.sub("_", name or "").strip().strip(".")
    return n[:80]


def _atomic_write(path, text, enc):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding=enc, newline="") as f:
        f.write(text)
    os.replace(tmp, path)


class ScriptStore:
    def __init__(self, folder):
        self.folder = folder
        os.makedirs(folder, exist_ok=True)

    def path(self, name, ext=".txt"):
        return os.path.join(self.folder, name + ext)

    def list(self):
        names = set()
        for f in os.listdir(self.folder):
            base, ext = os.path.splitext(f)
            if ext.lower() in (".txt", ".html"):
                names.add(base)
        return sorted(names, key=natural_key)

    def exists(self, name):
        return os.path.exists(self.path(name)) or os.path.exists(self.path(name, ".html"))

    def _unique(self, base):
        if not self.exists(base):
            return base
        n = 2
        while self.exists(f"{base} {n}"):
            n += 1
        return f"{base} {n}"

    def create(self, base="Kịch bản"):
        n = 1
        while self.exists(f"{base} {n}"):
            n += 1
        name = f"{base} {n}"
        self.write(name, "")
        return name

    def read(self, name):
        """Chữ thuần."""
        p = self.path(name)
        if not os.path.exists(p):
            return ""
        with open(p, "r", encoding=ENC, errors="replace") as f:
            return f.read()

    def read_html(self, name):
        """Bản có định dạng, hoặc None nếu kịch bản chỉ có chữ thuần."""
        p = self.path(name, ".html")
        if not os.path.exists(p):
            return None
        with open(p, "r", encoding="utf-8", errors="replace") as f:
            return f.read()

    def write(self, name, text, html=None):
        _atomic_write(self.path(name), text, ENC)
        hp = self.path(name, ".html")
        if html is not None:
            _atomic_write(hp, html, "utf-8")
        elif os.path.exists(hp):
            os.remove(hp)

    def rename(self, old, new):
        new = sanitize_name(new)
        if not new:
            raise ValueError("Tên không được để trống")
        if new != old and self.exists(new):
            raise ValueError("Đã có kịch bản tên này")
        if new != old:
            for ext in (".txt", ".html"):
                if os.path.exists(self.path(old, ext)):
                    os.rename(self.path(old, ext), self.path(new, ext))
        return new

    def duplicate(self, name):
        new = self._unique(f"{name} (bản sao)")
        for ext in (".txt", ".html"):
            if os.path.exists(self.path(name, ext)):
                shutil.copyfile(self.path(name, ext), self.path(new, ext))
        return new

    def delete(self, name):
        for ext in (".txt", ".html"):
            if os.path.exists(self.path(name, ext)):
                os.remove(self.path(name, ext))

    def import_file(self, src):
        base = sanitize_name(os.path.splitext(os.path.basename(src))[0]) or "Kịch bản nhập"
        name = self._unique(base)
        with open(src, "r", encoding="utf-8-sig", errors="replace") as f:
            text = f.read()
        self.write(name, text)
        return name
