"""Nhật ký kéo thả sang ứng dụng khác (giống aa09-keo.log) và đưa Moho lên trước sau khi thả."""
import os
import time

from . import moho_bridge

MAX_BYTES = 200_000


def log_path(folder):
    return os.path.join(folder, "keo.log")


def format_line(ms, action, front, pinned, path, now=None):
    ts = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(now))
    return (f"{ts} | KEO | {int(ms)}ms | {action} | moho_len_truoc={'true' if front else 'false'} "
            f"| luon_noi={'true' if pinned else 'false'} | {path}")


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


def after_drag(folder, paths, action, ms, pinned):
    """Gọi sau mỗi lần kéo. Nếu thả thành công thì đưa Moho lên trước. Trả về True nếu đã đưa Moho lên."""
    front = False
    if action != "Ignore":
        front = moho_bridge.bring_moho_to_front()
    for p in paths[:5]:
        append(folder, format_line(ms, action, front, pinned, p))
    return front
