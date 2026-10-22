"""Kéo tệp kiểu Windows gốc, y hệt kéo từ File Explorer.

Dùng đối tượng dữ liệu của chính vỏ Windows (Shell) nên ứng dụng nhận (Moho...) thấy đúng
những gì Explorer gửi: danh sách tệp, hình mờ biểu tượng + tên tệp đi theo con trỏ chuột.
Nếu có lỗi, hàm ném OSError để phần mềm quay về cách kéo của Qt.
"""
import ctypes
import os
import sys
import time

DROPEFFECT_COPY, DROPEFFECT_MOVE, DROPEFFECT_LINK = 1, 2, 4
DRAGDROP_S_CANCEL = 0x00040101
NAMES = {DROPEFFECT_COPY: "Copy", DROPEFFECT_MOVE: "Move", DROPEFFECT_LINK: "Link"}
_api = None


def available():
    return sys.platform == "win32"


def _init():
    global _api
    if _api is not None:
        return _api
    from ctypes import wintypes

    class GUID(ctypes.Structure):
        _fields_ = [("Data1", wintypes.DWORD), ("Data2", wintypes.WORD),
                    ("Data3", wintypes.WORD), ("Data4", ctypes.c_ubyte * 8)]

    shell32, ole32 = ctypes.windll.shell32, ctypes.windll.ole32
    hres = ctypes.c_long
    vp = ctypes.c_void_p
    ole32.IIDFromString.argtypes = [wintypes.LPCWSTR, ctypes.POINTER(GUID)]
    ole32.IIDFromString.restype = hres
    ole32.CoTaskMemFree.argtypes = [vp]
    ole32.CoTaskMemFree.restype = None
    shell32.SHParseDisplayName.argtypes = [wintypes.LPCWSTR, vp, ctypes.POINTER(vp), wintypes.ULONG,
                                           ctypes.POINTER(wintypes.ULONG)]
    shell32.SHParseDisplayName.restype = hres
    shell32.SHCreateDataObject.argtypes = [vp, wintypes.UINT, ctypes.POINTER(vp), vp, ctypes.POINTER(GUID),
                                           ctypes.POINTER(vp)]
    shell32.SHCreateDataObject.restype = hres
    shell32.SHDoDragDrop.argtypes = [wintypes.HWND, vp, vp, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
    shell32.SHDoDragDrop.restype = hres
    iid = GUID()
    if ole32.IIDFromString("{0000010e-0000-0000-C000-000000000046}", ctypes.byref(iid)) != 0:
        raise OSError("Không tạo được IID_IDataObject")
    _api = (wintypes, shell32, ole32, iid)
    return _api


def _release(pdo):
    """Gọi IUnknown::Release (mục thứ 3 trong bảng hàm của đối tượng COM)."""
    vtbl = ctypes.cast(pdo, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p)))[0]
    fn = ctypes.WINFUNCTYPE(ctypes.c_ulong, ctypes.c_void_p)(vtbl[2])
    fn(pdo)


def drag_files(hwnd, paths):
    """Bắt đầu kéo tệp thật. Trả về (tên kiểu thả, số ms). Ném OSError nếu không làm được."""
    if not available():
        raise OSError("Chỉ có trên Windows")
    paths = [os.path.abspath(p) for p in paths if os.path.exists(p)]
    if not paths:
        raise OSError("Không có tệp để kéo")
    wintypes, shell32, ole32, iid = _init()
    pidls = []
    pdo = ctypes.c_void_p()
    try:
        for p in paths:
            pidl = ctypes.c_void_p()
            hr = shell32.SHParseDisplayName(p, None, ctypes.byref(pidl), 0, None)
            if hr != 0 or not pidl.value:
                raise OSError(f"SHParseDisplayName lỗi {hr & 0xFFFFFFFF:#x}")
            pidls.append(pidl)
        arr = (ctypes.c_void_p * len(pidls))(*[p.value for p in pidls])
        hr = shell32.SHCreateDataObject(None, len(pidls), arr, None, ctypes.byref(iid), ctypes.byref(pdo))
        if hr != 0 or not pdo.value:
            raise OSError(f"SHCreateDataObject lỗi {hr & 0xFFFFFFFF:#x}")
        effect = wintypes.DWORD(0)
        t0 = time.monotonic()
        hr = shell32.SHDoDragDrop(hwnd, pdo.value, None,
                                  DROPEFFECT_COPY | DROPEFFECT_MOVE | DROPEFFECT_LINK, ctypes.byref(effect))
        ms = int((time.monotonic() - t0) * 1000)
        try:
            ctypes.windll.user32.ReleaseCapture()
        except Exception:
            pass
        if hr < 0:
            raise OSError(f"SHDoDragDrop lỗi {hr & 0xFFFFFFFF:#x}")
        if (hr & 0xFFFFFFFF) == DRAGDROP_S_CANCEL:
            return "Ignore", ms
        return NAMES.get(effect.value, "Ignore"), ms
    finally:
        if pdo.value:
            try:
                _release(pdo.value)
            except Exception:
                pass
        for pidl in pidls:
            ole32.CoTaskMemFree(pidl.value)
