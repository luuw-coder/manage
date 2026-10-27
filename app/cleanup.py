"""Dọn các tệp âm thanh đã cắt (thư mục exports) để không chiếm ổ đĩa.

Lưu ý quan trọng: Moho chỉ GHI NHỚ ĐƯỜNG DẪN tới tệp âm thanh/ảnh đã nhập (không nhúng vào dự án). Xóa tệp thì lớp
âm thanh trong dự án sẽ báo thiếu tệp. Vì vậy mặc định là giữ lại; người dùng chọn tự dọn tệp cũ hoặc xóa ngay.
"""
import os
import time

POLICIES = (
    ("keep", "Giữ lại (an toàn nhất cho dự án Moho)"),
    ("30d", "Tự xóa tệp cắt cũ hơn 30 ngày"),
    ("7d", "Tự xóa tệp cắt cũ hơn 7 ngày"),
    ("1d", "Tự xóa tệp cắt cũ hơn 1 ngày"),
    ("now", "Xóa ngay sau khi kéo vào Moho (Moho sẽ báo thiếu tệp khi mở lại dự án)"),
)
SETTING = "slice_cleanup"
DAYS = {"30d": 30, "7d": 7, "1d": 1}


def export_dir(db):
    return db.get_setting("export_dir") or os.path.join(os.path.dirname(db.path), "exports")


def _wavs(folder):
    try:
        for name in os.listdir(folder):
            p = os.path.join(folder, name)
            if name.lower().endswith(".wav") and os.path.isfile(p):
                yield p
    except OSError:
        return


def folder_usage(folder):
    """(số tệp, tổng byte) của các tệp .wav đã cắt."""
    n = total = 0
    for p in _wavs(folder):
        try:
            total += os.path.getsize(p)
            n += 1
        except OSError:
            pass
    return n, total


def purge(folder, older_than_days=None, keep=()):
    """Xóa tệp .wav trong folder (chỉ .wav). Trả về (số tệp đã xóa, byte giải phóng)."""
    cutoff = time.time() - older_than_days * 86400 if older_than_days is not None else None
    keep = {os.path.abspath(k) for k in keep}
    n = freed = 0
    for p in list(_wavs(folder)):
        if os.path.abspath(p) in keep:
            continue
        try:
            if cutoff is not None and os.path.getmtime(p) > cutoff:
                continue
            size = os.path.getsize(p)
            os.remove(p)
            n, freed = n + 1, freed + size
        except OSError:
            pass
    return n, freed


def apply_policy(db):
    """Chạy khi mở phần mềm: dọn tệp cũ theo lựa chọn của người dùng."""
    pol = db.get_setting(SETTING, "keep")
    if pol in DAYS:
        return purge(export_dir(db), DAYS[pol])
    return 0, 0


def human(nbytes):
    for unit in ("B", "KB", "MB", "GB"):
        if nbytes < 1024 or unit == "GB":
            return f"{nbytes:.0f} {unit}" if unit == "B" else f"{nbytes:.1f} {unit}"
        nbytes /= 1024
