"""Kết nối với Moho (Windows): tìm cửa sổ Moho, đưa lên trước, mở dự án."""
import ntpath
import os
import sys


def is_moho_exe(path):
    name = ntpath.basename((path or "").replace("/", "\\")).lower()
    return name.startswith("moho") and name.endswith(".exe")


def window_exe_at_cursor():
    """Tên tệp .exe của ứng dụng đang nằm dưới con trỏ chuột (dùng để biết người dùng thả vào đâu)."""
    if sys.platform != "win32":
        return ""
    try:
        import ctypes
        from ctypes import wintypes
        user32, kernel32 = ctypes.windll.user32, ctypes.windll.kernel32
        user32.WindowFromPoint.argtypes = [wintypes.POINT]
        user32.WindowFromPoint.restype = wintypes.HWND
        user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
        user32.GetAncestor.restype = wintypes.HWND
        kernel32.OpenProcess.restype = wintypes.HANDLE
        pt = wintypes.POINT()
        user32.GetCursorPos(ctypes.byref(pt))
        hwnd = user32.WindowFromPoint(pt)
        root = user32.GetAncestor(hwnd, 2) if hwnd else None  # GA_ROOT
        if not root:
            return ""
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(root, ctypes.byref(pid))
        h = kernel32.OpenProcess(0x1000, False, pid.value)
        if not h:
            return ""
        try:
            buf = ctypes.create_unicode_buffer(1024)
            size = wintypes.DWORD(1024)
            if kernel32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size)):
                return ntpath.basename(buf.value)
            return ""
        finally:
            kernel32.CloseHandle(h)
    except Exception:
        return ""


def exe_matches(path, keywords):
    """Tên tệp .exe có chứa một trong các từ khóa không (không phân biệt hoa thường)."""
    name = ntpath.basename((path or "").replace("/", "\\")).lower()
    if not name.endswith(".exe") or name.startswith("managemoho"):
        return False
    return any(k.strip().lower() in name for k in keywords if k and k.strip())


def list_windows():
    """Danh sách cửa sổ ngoài cùng đang hiện (của ứng dụng khác): hwnd, pid, exe, tiêu đề, lớp."""
    if sys.platform != "win32":
        return []
    import ctypes
    from ctypes import wintypes
    user32, kernel32 = ctypes.windll.user32, ctypes.windll.kernel32
    kernel32.OpenProcess.restype = wintypes.HANDLE
    user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    out = []
    proc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    exe_cache = {}

    def exe_of(pid):
        if pid in exe_cache:
            return exe_cache[pid]
        h = kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
        res = ""
        if h:
            try:
                buf = ctypes.create_unicode_buffer(1024)
                size = wintypes.DWORD(1024)
                if kernel32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size)):
                    res = buf.value
            finally:
                kernel32.CloseHandle(h)
        exe_cache[pid] = res
        return res

    def cb(hwnd, _lparam):
        try:
            if not user32.IsWindowVisible(hwnd):
                return True
            n = user32.GetWindowTextLengthW(hwnd)
            if n == 0:
                return True
            pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if pid.value == os.getpid():
                return True
            title = ctypes.create_unicode_buffer(n + 1)
            user32.GetWindowTextW(hwnd, title, n + 1)
            cls = ctypes.create_unicode_buffer(256)
            user32.GetClassNameW(hwnd, cls, 256)
            out.append({"hwnd": hwnd, "pid": pid.value, "exe": exe_of(pid.value),
                        "title": title.value, "cls": cls.value})
        except Exception:
            pass
        return True

    user32.EnumWindows(proc(cb), 0)
    return out


def find_app_window(keywords):
    """Cửa sổ chính của ứng dụng có tên .exe chứa từ khóa; trả về dict hoặc None."""
    best = None
    for w in list_windows():
        if exe_matches(w["exe"], keywords):
            # ưu tiên cửa sổ có tiêu đề dài nhất (thường là cửa sổ chính có tên dự án)
            if best is None or len(w["title"]) > len(best["title"]):
                best = w
    return best


def _find_moho_hwnd():
    w = find_app_window(["moho"])
    return w["hwnd"] if (w and is_moho_exe(w["exe"])) else None


def bring_hwnd_to_front(hwnd):
    """Đưa một cửa sổ lên trước. Trả về True nếu không gặp lỗi."""
    try:
        if not hwnd:
            return False
        import ctypes
        user32, kernel32 = ctypes.windll.user32, ctypes.windll.kernel32
        if user32.IsIconic(hwnd):
            user32.ShowWindow(hwnd, 9)  # SW_RESTORE
        fg = user32.GetForegroundWindow()
        cur = kernel32.GetCurrentThreadId()
        fg_thread = user32.GetWindowThreadProcessId(fg, None) if fg else 0
        attached = False
        if fg_thread and fg_thread != cur:
            attached = bool(user32.AttachThreadInput(cur, fg_thread, True))
        try:
            user32.BringWindowToTop(hwnd)
            user32.SetForegroundWindow(hwnd)
        finally:
            if attached:
                user32.AttachThreadInput(cur, fg_thread, False)
        return True
    except Exception:
        return False


def bring_app_to_front(keywords=("moho",)):
    """Đưa ứng dụng đích (theo từ khóa tên .exe) lên trước. Trả về True nếu tìm thấy."""
    try:
        w = find_app_window(list(keywords))
        return bool(w) and bring_hwnd_to_front(w["hwnd"])
    except Exception:
        return False


def bring_moho_to_front():
    """Đưa cửa sổ Moho lên trước. Trả về True nếu tìm thấy Moho đang chạy."""
    return bring_app_to_front(("moho",))


def open_in_moho(path):
    """Mở tệp bằng chương trình mặc định (với .moho thường là Moho)."""
    try:
        os.startfile(path)  # type: ignore[attr-defined]
        return True
    except Exception:
        return False
