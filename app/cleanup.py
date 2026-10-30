"""Dọn các tệp âm thanh đã cắt (thư mục exports; chỉ tệp phần mềm tạo ra) để không chiếm ổ đĩa.

Lưu ý quan trọng: Moho chỉ GHI NHỚ ĐƯỜNG DẪN tới tệp âm thanh/ảnh đã nhập (không nhúng vào dự án). Xóa tệp thì lớp
âm thanh trong dự án sẽ báo thiếu tệp. Vì vậy mặc định là giữ lại; người dùng chọn tự dọn tệp cũ hoặc xóa ngay.
"""
import os
import re
import time

DEFAULT_POLICY = "30d"
POLICIES = (
    ("30d", "Tự xóa tệp cắt cũ hơn 30 ngày (mặc định)"),
    ("keep", "Giữ lại mãi (an toàn nhất cho dự án Moho)"),
    ("7d", "Tự xóa tệp cắt cũ hơn 7 ngày"),
    ("1d", "Tự xóa tệp cắt cũ hơn 1 ngày"),
    ("now", "Xóa ngay sau khi kéo vào Moho (Moho sẽ báo thiếu tệp khi mở lại dự án)"),
)
SETTING = "slice_cleanup"
DAYS = {"30d": 30, "7d": 7, "1d": 1}


def export_dir(db):
    return db.get_setting("export_dir") or os.path.join(os.path.dirname(db.path), "exports")


# Chỉ tệp do chính phần mềm tạo ra (tên dạng "tên_1.20-4.50s.mp3" hoặc ".wav") mới bị dọn, tệp khác của bạn thì không.
CUT_NAME = re.compile(r".+_\d+\.\d\d-\d+\.\d\ds(_\d+)?\.(wav|mp3)$", re.IGNORECASE)


def _wavs(folder):
    try:
        for name in os.listdir(folder):
            p = os.path.join(folder, name)
            if CUT_NAME.match(name) and os.path.isfile(p):
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
    pol = db.get_setting(SETTING, DEFAULT_POLICY)
    if pol in DAYS:
        return purge(export_dir(db), DAYS[pol])
    return 0, 0


def human(nbytes):
    for unit in ("B", "KB", "MB", "GB"):
        if nbytes < 1024 or unit == "GB":
            return f"{nbytes:.0f} {unit}" if unit == "B" else f"{nbytes:.1f} {unit}"
        nbytes /= 1024


# ---------------------------------------------------------------- rác sinh ra khi dùng (bộ nhớ đệm, tệp tạm, nhật ký)
CACHE_SUBDIRS = ("cache", "Default/Cache", "Default/Code Cache", "Default/GPUCache", "GrShaderCache", "ShaderCache",
                 "GraphiteDawnCache", "DawnGraphiteCache", "DawnWebGPUCache")
TEMP_NAMES = ("moho_queue.txt", "moho_result.txt", "animate_import.jsfl")


def _tree_size(path):
    total = 0
    for root, _dirs, files in os.walk(path):
        for f in files:
            try:
                total += os.path.getsize(os.path.join(root, f))
            except OSError:
                pass
    return total


def junk_items(data_dir, exchange_dir=None):
    """Danh sách (đường dẫn, là_thư_mục) rác có thể xóa an toàn: tệp thử kéo, tệp trao đổi tạm với Moho/Animate,
    bộ nhớ đệm trình duyệt của các tài khoản AI. KHÔNG gồm dữ liệu quan trọng (kịch bản, mục, cài đặt, đăng nhập)."""
    items = []
    t = os.path.join(data_dir, "testdrag")
    if os.path.isdir(t):
        items.append((t, True))
    if exchange_dir and os.path.isdir(exchange_dir):
        for n in TEMP_NAMES:
            p = os.path.join(exchange_dir, n)
            if os.path.isfile(p):
                items.append((p, False))
    prof = os.path.join(data_dir, "ai_profiles")
    if os.path.isdir(prof):
        for acc in os.listdir(prof):
            for sub in CACHE_SUBDIRS:
                d = os.path.join(prof, acc, *sub.split("/"))
                if os.path.isdir(d):
                    items.append((d, True))
    return items


def junk_usage(data_dir, exchange_dir=None):
    n = total = 0
    for path, is_dir in junk_items(data_dir, exchange_dir):
        n += 1
        try:
            total += _tree_size(path) if is_dir else os.path.getsize(path)
        except OSError:
            pass
    return n, total


def clear_junk(data_dir, exchange_dir=None):
    """Xóa rác. Trả về (số mục đã xóa, byte giải phóng). Lỗi (tệp đang dùng) thì bỏ qua."""
    import shutil
    n = freed = 0
    for path, is_dir in junk_items(data_dir, exchange_dir):
        try:
            size = _tree_size(path) if is_dir else os.path.getsize(path)
            if is_dir:
                shutil.rmtree(path, ignore_errors=True)
                if os.path.isdir(path):
                    continue
            else:
                os.remove(path)
            n, freed = n + 1, freed + size
        except OSError:
            pass
    return n, freed
