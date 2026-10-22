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


def _find_moho_hwnd():
    if sys.platform != "win32":
        return None
    import ctypes
    from ctypes import wintypes
    user32, kernel32 = ctypes.windll.user32, ctypes.windll.kernel32
    kernel32.OpenProcess.restype = wintypes.HANDLE
    found = []
    proc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def exe_of(pid):
        h = kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
        if not h:
            return ""
        try:
            buf = ctypes.create_unicode_buffer(1024)
            size = wintypes.DWORD(1024)
            if kernel32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size)):
                return buf.value
            return ""
        finally:
            kernel32.CloseHandle(h)

    def cb(hwnd, _lparam):
        try:
            if not user32.IsWindowVisible(hwnd) or user32.GetWindowTextLengthW(hwnd) == 0:
                return True
            pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if pid.value == os.getpid():
                return True
            if is_moho_exe(exe_of(pid.value)):
                found.append(hwnd)
                return False
        except Exception:
            pass
        return True

    user32.EnumWindows(proc(cb), 0)
    return found[0] if found else None


def bring_moho_to_front():
    """Đưa cửa sổ Moho lên trước. Trả về True nếu tìm thấy Moho đang chạy."""
    try:
        hwnd = _find_moho_hwnd()
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


def open_in_moho(path):
    """Mở tệp bằng chương trình mặc định (với .moho thường là Moho)."""
    try:
        os.startfile(path)  # type: ignore[attr-defined]
        return True
    except Exception:
        return False
