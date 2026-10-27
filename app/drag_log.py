"""Nhật ký kéo thả sang ứng dụng khác (giống aa09-keo.log) và đưa Moho lên trước sau khi thả."""
import os
import time

from . import moho_bridge

MAX_BYTES = 200_000


def log_path(folder):
    return os.path.join(folder, "keo.log")


def format_line(ms, action, front, pinned, path, now=None, info=None):
    ts = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(now))
    extra = "".join(f" | {k}={v}" for k, v in (info or {}).items())
    return (f"{ts} | KEO | {int(ms)}ms | {action} | moho_len_truoc={'true' if front else 'false'} "
            f"| luon_noi={'true' if pinned else 'false'}{extra} | {path}")


def append(folder, line):
    try:
        os.makedirs(folder, exist_ok=True)
        p = log_path(folder)
        if os.path.exists(p) and os.path.getsize(p) > MAX_BYTES:
            with open(p, "r", encoding="utf-8", errors="replace") as f:
                keep = f.readlines()[-500:]
            with open(p, "w", encoding="utf-8") as f:
                f.writelines(keep)
        with open(p, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass


def after_drag(folder, paths, action, ms, pinned, info=None, keywords=("moho",)):
    """Gọi sau mỗi lần kéo. Nếu thả thành công thì đưa Moho lên trước. Trả về True nếu đã đưa Moho lên."""
    front = False
    if action != "Ignore":
        front = moho_bridge.bring_app_to_front(keywords)
    for p in paths[:5]:
        append(folder, format_line(ms, action, front, pinned, p, info=info))
    return front
