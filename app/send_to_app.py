"""Gửi tệp vào ứng dụng đích (Moho, Premiere, Photoshop...) mà KHÔNG cần kéo thả.

Cách làm: đưa ứng dụng đích lên trước, bấm phím tắt "Nhập" (Import) hoặc "Mở" (Open) của chính ứng dụng đó,
đợi hộp thoại chọn tệp hiện ra, điền đường dẫn tệp rồi bấm Mở. Đây là đường nhập tệp mà mọi ứng dụng đều có,
nên dùng được khi kéo thả bị ứng dụng bỏ qua.

Mỗi ứng dụng là một "hồ sơ" (profile): tên, từ khóa tên .exe, phím tắt Nhập, phím tắt Mở, cách gửi.
Phần logic thuần (hồ sơ, phím tắt, thứ tự các bước) không phụ thuộc Windows nên kiểm tra tự động được;
phần gọi Windows nằm trong WinDriver.
"""
import copy
import json
import ntpath
import os
import sys
import time

SETTING_PROFILES = "target_profiles"
SETTING_ACTIVE = "target_active"

METHOD_DIALOG = "dialog"   # mở hộp thoại Nhập rồi điền đường dẫn (nhập được mọi loại tệp ứng dụng hỗ trợ)
METHOD_PASTE = "paste"     # đưa ảnh vào bộ nhớ tạm rồi bấm Ctrl+V trong ứng dụng (chỉ ảnh)

DEFAULT_PROFILES = [
    {"id": "moho", "name": "Moho", "keywords": ["moho"], "method": METHOD_DIALOG,
     "import_hotkey": "ctrl+shift+y", "open_hotkey": "ctrl+o",
     "open_exts": [".moho", ".anme", ".anime"], "builtin": True},
    {"id": "premiere", "name": "Premiere Pro", "keywords": ["premiere"], "method": METHOD_DIALOG,
     "import_hotkey": "ctrl+i", "open_hotkey": "ctrl+o", "open_exts": [".prproj"], "builtin": True},
    {"id": "aftereffects", "name": "After Effects", "keywords": ["afterfx"], "method": METHOD_DIALOG,
     "import_hotkey": "ctrl+i", "open_hotkey": "ctrl+o", "open_exts": [".aep"], "builtin": True},
    {"id": "photoshop", "name": "Photoshop", "keywords": ["photoshop"], "method": METHOD_DIALOG,
     "import_hotkey": "ctrl+o", "open_hotkey": "ctrl+o", "open_exts": [], "builtin": True},
]

# ---------------------------------------------------------------- phím tắt
_VK_NAMES = {"ctrl": 0x11, "control": 0x11, "shift": 0x10, "alt": 0x12, "enter": 0x0D, "return": 0x0D,
             "esc": 0x1B, "escape": 0x1B, "tab": 0x09, "space": 0x20, "delete": 0x2E, "del": 0x2E,
             "insert": 0x2D, "home": 0x24, "end": 0x23}
_MODIFIERS = (0x11, 0x10, 0x12)


def parse_hotkey(text):
    """'ctrl+shift+y' -> [0x11, 0x10, 0x59]. Ném ValueError nếu không hiểu. Phím thường phải ở cuối."""
    parts = [p.strip().lower() for p in (text or "").replace(" ", "").split("+") if p.strip()]
    if not parts:
        raise ValueError("Chưa nhập phím tắt")
    vks = []
    for p in parts:
        if p in _VK_NAMES:
            vks.append(_VK_NAMES[p])
        elif len(p) == 1 and p.isalpha() and p.isascii():
            vks.append(ord(p.upper()))
        elif len(p) == 1 and p.isdigit():
            vks.append(ord(p))
        elif p[0] == "f" and p[1:].isdigit() and 1 <= int(p[1:]) <= 12:
            vks.append(0x70 + int(p[1:]) - 1)
        else:
            raise ValueError(f"Không hiểu phím “{p}”")
    if vks[-1] in _MODIFIERS:
        raise ValueError("Cần thêm một phím thường (ví dụ Y, O, I) ở cuối, sau Ctrl/Shift/Alt")
    return vks


def hotkey_ok(text):
    try:
        parse_hotkey(text)
        return True
    except ValueError:
        return False


# ---------------------------------------------------------------- hồ sơ
def _clean(p):
    out = {
        "id": str(p.get("id") or "").strip() or "app",
        "name": str(p.get("name") or "").strip() or "Ứng dụng",
        "keywords": [k.strip().lower() for k in (p.get("keywords") or []) if str(k).strip()],
        "method": p.get("method") if p.get("method") in (METHOD_DIALOG, METHOD_PASTE) else METHOD_DIALOG,
        "import_hotkey": str(p.get("import_hotkey") or "ctrl+o").strip().lower(),
        "open_hotkey": str(p.get("open_hotkey") or "ctrl+o").strip().lower(),
        "open_exts": [e.strip().lower() if e.strip().startswith(".") else "." + e.strip().lower()
                      for e in (p.get("open_exts") or []) if str(e).strip()],
        "builtin": bool(p.get("builtin")),
    }
    return out


def load_profiles(db):
    """Hồ sơ đã lưu; luôn có đủ các hồ sơ có sẵn (người dùng sửa được nhưng không mất)."""
    saved = []
    raw = db.get_setting(SETTING_PROFILES)
    if raw:
        try:
            data = json.loads(raw)
            saved = [_clean(p) for p in data if isinstance(p, dict)]
        except (ValueError, TypeError):
            saved = []
    ids = {p["id"] for p in saved}
    for d in DEFAULT_PROFILES:
        if d["id"] not in ids:
            saved.append(copy.deepcopy(d))
    order = {d["id"]: i for i, d in enumerate(DEFAULT_PROFILES)}
    saved.sort(key=lambda p: (order.get(p["id"], 99), p["name"].lower()))
    return saved


def save_profiles(db, profiles):
    db.set_setting(SETTING_PROFILES, json.dumps([_clean(p) for p in profiles], ensure_ascii=False))


def active_id(db):
    return db.get_setting(SETTING_ACTIVE, "moho")


def set_active(db, pid):
    db.set_setting(SETTING_ACTIVE, pid)


def active_profile(db):
    profiles = load_profiles(db)
    want = active_id(db)
    return next((p for p in profiles if p["id"] == want), profiles[0])


def new_profile_id(profiles, name):
    base = "".join(ch for ch in name.lower() if ch.isalnum()) or "app"
    ids = {p["id"] for p in profiles}
    pid, n = base, 2
    while pid in ids:
        pid, n = f"{base}{n}", n + 1
    return pid


def hotkey_for(profile, path):
    ext = os.path.splitext(path)[1].lower()
    return profile["open_hotkey"] if ext in profile.get("open_exts", []) else profile["import_hotkey"]


# ---------------------------------------------------------------- kết quả
class SendResult:
    def __init__(self):
        self.sent = []        # đường dẫn đã gửi
        self.failed = []      # (đường dẫn, mã lý do)
        self.remaining = []   # chưa gửi vì phải dừng giữa chừng
        self.stop = ""        # mã lý do dừng: "", "no_app", "no_dialog", "prompt", "elevated", "platform"
        self.detail = ""

    @property
    def ok(self):
        return not self.failed and not self.stop


# ---------------------------------------------------------------- điều phối (không phụ thuộc Windows)
def send_files(profile, paths, driver=None, sleep=time.sleep, dialog_timeout=4.0, between=0.9):
    """Gửi lần lượt từng tệp vào ứng dụng đích. Dừng sớm khi gặp lỗi chặn cả mẻ."""
    res = SendResult()
    drv = driver or WinDriver()
    paths = [os.path.abspath(p) for p in paths]
    if not drv.available():
        res.stop, res.detail, res.remaining = "platform", "Chỉ có trên Windows", list(paths)
        return res
    win = drv.find_window(profile["keywords"])
    if not win:
        res.stop, res.remaining = "no_app", list(paths)
        return res
    if drv.needs_admin_match(win["pid"]):
        res.stop, res.remaining = "elevated", list(paths)
        return res
    for i, path in enumerate(paths):
        if not os.path.exists(path):
            res.failed.append((path, "missing"))
            continue
        try:
            keys = parse_hotkey(hotkey_for(profile, path))
        except ValueError as e:
            res.stop, res.detail, res.remaining = "hotkey", str(e), list(paths[i:])
            return res
        before = drv.dialog_handles(win["pid"])
        drv.bring_front(win["hwnd"])
        sleep(0.25)
        drv.send_hotkey(keys)
        dlg = drv.wait_dialog(win["pid"], before, dialog_timeout)
        if not dlg:
            res.stop, res.remaining = "no_dialog", list(paths[i:])
            return res
        if not drv.fill_and_accept(dlg, path):
            drv.close_dialog(dlg)
            res.failed.append((path, "fill"))
            continue
        drv.wait_closed(dlg, 3.0)
        res.sent.append(path)
        sleep(between)
        if i + 1 < len(paths) and drv.blocking_prompt(win["pid"], before):
            res.stop, res.remaining = "prompt", list(paths[i + 1:])
            return res
    return res


def paste_clipboard(profile, driver=None, sleep=time.sleep):
    """Bấm Ctrl+V trong ứng dụng đích (ảnh đã được đặt vào bộ nhớ tạm trước đó)."""
    res = SendResult()
    drv = driver or WinDriver()
    if not drv.available():
        res.stop, res.detail = "platform", "Chỉ có trên Windows"
        return res
    win = drv.find_window(profile["keywords"])
    if not win:
        res.stop = "no_app"
        return res
    if drv.needs_admin_match(win["pid"]):
        res.stop = "elevated"
        return res
    drv.bring_front(win["hwnd"])
    sleep(0.3)
    drv.send_hotkey(parse_hotkey("ctrl+v"))
    res.sent.append("clipboard")
    return res


def probe(profile, driver=None, sleep=time.sleep):
    """Kiểm tra kết nối: tìm ứng dụng, bấm phím Nhập, xem hộp thoại có hiện không rồi đóng nó lại."""
    drv = driver or WinDriver()
    info = {"platform": drv.available(), "app": None, "elevated": False, "dialog": False, "title": ""}
    if not info["platform"]:
        return info
    win = drv.find_window(profile["keywords"])
    if not win:
        return info
    info["app"] = win["title"]
    info["elevated"] = bool(drv.needs_admin_match(win["pid"]))
    if info["elevated"]:
        return info
    try:
        keys = parse_hotkey(profile["import_hotkey"])
    except ValueError as e:
        info["error"] = str(e)
        return info
    before = drv.dialog_handles(win["pid"])
    drv.bring_front(win["hwnd"])
    sleep(0.25)
    drv.send_hotkey(keys)
    dlg = drv.wait_dialog(win["pid"], before, 4.0)
    if dlg:
        info["dialog"] = True
        info["title"] = drv.dialog_title(dlg)
        drv.close_dialog(dlg)
    return info


MESSAGES = {
    "platform": "Chức năng này chỉ chạy trên Windows.",
    "no_app": "Chưa thấy {app} đang chạy. Hãy mở {app} (và mở một dự án) rồi thử lại.",
    "elevated": "{app} đang chạy bằng quyền Administrator còn Manage Moho thì không, nên Windows chặn gửi. "
                "Hãy mở cả hai cùng quyền (cùng chuột phải → Run as administrator, hoặc cùng bình thường).",
    "no_dialog": "Không thấy hộp thoại Nhập của {app}. Kiểm tra: đã mở dự án chưa, {app} có đang hiện hộp thoại "
                 "khác không, và phím tắt Nhập trong Quản lý → Cài đặt có đúng với {app} của bạn không.",
    "prompt": "{app} đang hỏi bạn một câu (ví dụ cách dùng ảnh). Trả lời trong {app} rồi gửi tiếp các tệp còn lại.",
    "hotkey": "Phím tắt chưa đúng: {detail}",
}


def describe(res, profile):
    """Câu thông báo ngắn cho người dùng."""
    app = profile["name"]
    if res.stop:
        msg = MESSAGES.get(res.stop, "Không gửi được.").format(app=app, detail=res.detail)
        if res.sent:
            msg = f"Đã gửi {len(res.sent)} tệp. " + msg
        return msg
    if res.failed and not res.sent:
        return f"Không gửi được tệp vào {app} (hộp thoại không nhận đường dẫn hoặc tệp không còn trên máy)."
    name = ntpath.basename(res.sent[0]) if res.sent and res.sent[0] != "clipboard" else "ảnh"
    more = f" và {len(res.sent) - 1} tệp khác" if len(res.sent) > 1 else ""
    tail = f" ({len(res.failed)} tệp lỗi)" if res.failed else ""
    return f"Đã gửi vào {app}: {name}{more}{tail}. Nếu {app} hỏi cách dùng, chọn trong {app}."


# ---------------------------------------------------------------- phần gọi Windows
class WinDriver:
    """Các thao tác Windows thật. Mọi hàm chịu lỗi: trả về giá trị 'không thành công' thay vì ném lỗi."""

    WM_SETTEXT, WM_CLOSE, BM_CLICK, WM_KEYDOWN, WM_KEYUP = 0x000C, 0x0010, 0x00F5, 0x0100, 0x0101
    KEYEVENTF_KEYUP = 0x0002

    def __init__(self):
        self._ready = False

    def available(self):
        return sys.platform == "win32"

    def _init(self):
        if self._ready:
            return
        import ctypes
        from ctypes import wintypes
        u = ctypes.windll.user32
        k = ctypes.windll.kernel32
        self.ctypes, self.wt, self.u, self.k = ctypes, wintypes, u, k
        ulp = ctypes.c_size_t

        class KEYBDINPUT(ctypes.Structure):
            _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD), ("dwFlags", wintypes.DWORD),
                        ("time", wintypes.DWORD), ("dwExtraInfo", ulp)]

        class MOUSEINPUT(ctypes.Structure):
            _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG), ("mouseData", wintypes.DWORD),
                        ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD), ("dwExtraInfo", ulp)]

        class HARDWAREINPUT(ctypes.Structure):
            _fields_ = [("uMsg", wintypes.DWORD), ("wParamL", wintypes.WORD), ("wParamH", wintypes.WORD)]

        class _U(ctypes.Union):
            _fields_ = [("ki", KEYBDINPUT), ("mi", MOUSEINPUT), ("hi", HARDWAREINPUT)]

        class INPUT(ctypes.Structure):
            _fields_ = [("type", wintypes.DWORD), ("u", _U)]

        self.INPUT, self.KEYBDINPUT = INPUT, KEYBDINPUT
        u.SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int]
        u.SendInput.restype = wintypes.UINT
        u.SendMessageW.argtypes = [wintypes.HWND, wintypes.UINT, ctypes.c_size_t, ctypes.c_void_p]
        u.SendMessageW.restype = ctypes.c_ssize_t
        u.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, ctypes.c_size_t, ctypes.c_ssize_t]
        u.PostMessageW.restype = wintypes.BOOL
        u.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        u.GetDlgItem.argtypes = [wintypes.HWND, ctypes.c_int]
        u.GetDlgItem.restype = wintypes.HWND
        u.FindWindowExW.argtypes = [wintypes.HWND, wintypes.HWND, wintypes.LPCWSTR, wintypes.LPCWSTR]
        u.FindWindowExW.restype = wintypes.HWND
        u.GetForegroundWindow.restype = wintypes.HWND
        u.IsWindow.argtypes = [wintypes.HWND]
        u.IsWindowVisible.argtypes = [wintypes.HWND]
        k.OpenProcess.restype = wintypes.HANDLE
        self._ready = True

    # ---- tìm cửa sổ
    def find_window(self, keywords):
        from .moho_bridge import find_app_window
        try:
            return find_app_window(keywords)
        except Exception:
            return None

    def _pid_of(self, hwnd):
        pid = self.wt.DWORD()
        self.u.GetWindowThreadProcessId(hwnd, self.ctypes.byref(pid))
        return pid.value

    def _class_of(self, hwnd):
        buf = self.ctypes.create_unicode_buffer(256)
        self.u.GetClassNameW(hwnd, buf, 256)
        return buf.value

    def _title_of(self, hwnd):
        n = self.u.GetWindowTextLengthW(hwnd)
        buf = self.ctypes.create_unicode_buffer(n + 1)
        self.u.GetWindowTextW(hwnd, buf, n + 1)
        return buf.value

    def _top_windows(self, pid):
        self._init()
        found = []
        proc = self.ctypes.WINFUNCTYPE(self.wt.BOOL, self.wt.HWND, self.wt.LPARAM)

        def cb(hwnd, _l):
            try:
                if self.u.IsWindowVisible(hwnd) and self._pid_of(hwnd) == pid:
                    found.append(hwnd)
            except Exception:
                pass
            return True

        self.u.EnumWindows(proc(cb), 0)
        return found

    def dialog_handles(self, pid):
        """Các hộp thoại kiểu Windows (#32770) đang hiện của tiến trình."""
        try:
            return {h for h in self._top_windows(pid) if self._class_of(h) == "#32770"}
        except Exception:
            return set()

    def blocking_prompt(self, pid, before):
        """Có hộp thoại mới (ngoài các hộp thoại đã có trước đó) đang chờ người dùng trả lời không."""
        try:
            return bool(self.dialog_handles(pid) - set(before))
        except Exception:
            return False

    def wait_dialog(self, pid, before, timeout):
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            new = self.dialog_handles(pid) - set(before)
            if new:
                time.sleep(0.25)  # đợi hộp thoại dựng xong các ô bên trong
                return sorted(new)[-1]
            time.sleep(0.1)
        return None

    def wait_closed(self, hwnd, timeout):
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            if not self.u.IsWindow(hwnd) or not self.u.IsWindowVisible(hwnd):
                return True
            time.sleep(0.1)
        return False

    def dialog_title(self, hwnd):
        try:
            return self._title_of(hwnd)
        except Exception:
            return ""

    def close_dialog(self, hwnd):
        try:
            self.u.PostMessageW(hwnd, self.WM_CLOSE, 0, 0)
        except Exception:
            pass

    # ---- quyền Administrator
    def _elevated(self, pid):
        """True/False nếu biết, None nếu không đọc được."""
        self._init()
        ct, wt = self.ctypes, self.wt
        h = self.k.OpenProcess(0x1000, False, pid)
        if not h:
            return None
        try:
            tok = wt.HANDLE()
            adv = ct.windll.advapi32
            adv.OpenProcessToken.argtypes = [wt.HANDLE, wt.DWORD, ct.POINTER(wt.HANDLE)]
            if not adv.OpenProcessToken(h, 0x0008, ct.byref(tok)):  # TOKEN_QUERY
                return None
            try:
                val, ret = wt.DWORD(0), wt.DWORD(0)
                adv.GetTokenInformation.argtypes = [wt.HANDLE, ct.c_int, ct.c_void_p, wt.DWORD, ct.POINTER(wt.DWORD)]
                if adv.GetTokenInformation(tok, 20, ct.byref(val), 4, ct.byref(ret)):  # TokenElevation
                    return bool(val.value)
                return None
            finally:
                self.k.CloseHandle(tok)
        finally:
            self.k.CloseHandle(h)

    def needs_admin_match(self, pid):
        """Ứng dụng đích chạy Administrator mà phần mềm này thì không -> Windows chặn phím và thả tệp."""
        try:
            target = self._elevated(pid)
            if not target:
                return False
            me = self._elevated(os.getpid())
            return me is False
        except Exception:
            return False

    # ---- phím và điền hộp thoại
    def bring_front(self, hwnd):
        from .moho_bridge import bring_hwnd_to_front
        ok = bring_hwnd_to_front(hwnd)
        end = time.monotonic() + 1.0
        while time.monotonic() < end:  # đợi đến khi cửa sổ thật sự có tiêu điểm
            fg = self.u.GetForegroundWindow()
            if fg and self._pid_of(fg) == self._pid_of(hwnd):
                break
            time.sleep(0.05)
        return ok

    def send_hotkey(self, vks):
        self._init()
        mods = [v for v in vks[:-1]]
        key = vks[-1]

        def ev(vk, up):
            i = self.INPUT()
            i.type = 1  # INPUT_KEYBOARD
            i.u.ki = self.KEYBDINPUT(vk, 0, self.KEYEVENTF_KEYUP if up else 0, 0, 0)
            return i

        seq = [ev(v, False) for v in mods] + [ev(key, False), ev(key, True)] + [ev(v, True) for v in reversed(mods)]
        for item in seq:
            self.u.SendInput(1, self.ctypes.byref(item), self.ctypes.sizeof(self.INPUT))
            time.sleep(0.02)

    def _children(self, hwnd):
        out = []
        proc = self.ctypes.WINFUNCTYPE(self.wt.BOOL, self.wt.HWND, self.wt.LPARAM)

        def cb(h, _l):
            out.append(h)
            return True

        self.u.EnumChildWindows(hwnd, proc(cb), 0)
        return out

    def _filename_edit(self, dlg):
        """Ô nhập tên tệp của hộp thoại Mở: ComboBoxEx32 > ComboBox > Edit (kiểu mới), hoặc ô Edit đầu tiên."""
        for h in self._children(dlg):
            if self._class_of(h) == "ComboBoxEx32":
                cb = self.u.FindWindowExW(h, None, "ComboBox", None)
                ed = self.u.FindWindowExW(cb, None, "Edit", None) if cb else None
                if ed:
                    return ed
        edits = [h for h in self._children(dlg) if self._class_of(h) == "Edit" and self.u.IsWindowVisible(h)]
        return edits[0] if edits else None

    def fill_and_accept(self, dlg, path):
        """Điền đường dẫn đầy đủ vào ô tên tệp rồi bấm nút Mở. Trả về True nếu gửi được lệnh."""
        try:
            self._init()
            ed = self._filename_edit(dlg)
            if not ed:
                return False
            buf = self.ctypes.create_unicode_buffer(path)
            self.u.SendMessageW(ed, self.WM_SETTEXT, 0, self.ctypes.cast(buf, self.ctypes.c_void_p))
            time.sleep(0.15)
            btn = self.u.GetDlgItem(dlg, 1)  # IDOK = nút Mở
            if btn:
                self.u.SendMessageW(btn, self.BM_CLICK, 0, None)
            else:  # không thấy nút: gửi phím Enter vào ô nhập
                self.u.PostMessageW(ed, self.WM_KEYDOWN, 0x0D, 0)
                self.u.PostMessageW(ed, self.WM_KEYUP, 0x0D, 0)
            return True
        except Exception:
            return False
