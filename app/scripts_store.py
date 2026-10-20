"""Kịch bản lưu thành các tệp .txt thật trong một thư mục của phần mềm."""
import os
import re
import shutil

from .fsbrowse import natural_key

_INVALID = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
ENC = "utf-8-sig"  # có BOM để Notepad hiển thị đúng tiếng Việt


def sanitize_name(name):
    n = _INVALID.sub("_", name or "").strip().strip(".")
    return n[:80]


class ScriptStore:
    def __init__(self, folder):
        self.folder = folder
        os.makedirs(folder, exist_ok=True)

    def path(self, name):
        return os.path.join(self.folder, name + ".txt")

    def list(self):
        names = [f[:-4] for f in os.listdir(self.folder) if f.lower().endswith(".txt")]
        return sorted(names, key=natural_key)

    def exists(self, name):
        return os.path.exists(self.path(name))

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
        with open(self.path(name), "r", encoding=ENC, errors="replace") as f:
            return f.read()

    def write(self, name, text):
        tmp = self.path(name) + ".tmp"
        with open(tmp, "w", encoding=ENC, newline="") as f:
            f.write(text)
        os.replace(tmp, self.path(name))

    def rename(self, old, new):
        new = sanitize_name(new)
        if not new:
            raise ValueError("Tên không được để trống")
        if new != old and self.exists(new):
            raise ValueError("Đã có kịch bản tên này")
        if new != old:
            os.rename(self.path(old), self.path(new))
        return new

    def duplicate(self, name):
        new = self._unique(f"{name} (bản sao)")
        shutil.copyfile(self.path(name), self.path(new))
        return new

    def delete(self, name):
        os.remove(self.path(name))

    def import_file(self, src):
        base = sanitize_name(os.path.splitext(os.path.basename(src))[0]) or "Kịch bản nhập"
        name = self._unique(base)
        with open(src, "r", encoding="utf-8-sig", errors="replace") as f:
            text = f.read()
        self.write(name, text)
        return name
