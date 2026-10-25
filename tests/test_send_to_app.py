import os
import tempfile

import pytest

from app import send_to_app as s
from app.db import Database


class FakeDriver:
    """Giả lập Windows để kiểm tra thứ tự các bước mà không cần Moho thật."""

    def __init__(self, app=True, dialog=True, fill_ok=True, elevated=False, prompt_after=None, win=True):
        self.app, self.dialog, self.fill_ok, self.elevated = app, dialog, fill_ok, elevated
        self.prompt_after, self.win = prompt_after, win
        self.log = []
        self.sent_count = 0

    def available(self):
        return self.win

    def find_window(self, keywords):
        self.log.append(("find", tuple(keywords)))
        return {"hwnd": 1, "pid": 42, "title": "Moho - test"} if self.app else None

    def needs_admin_match(self, pid):
        return self.elevated

    def dialog_handles(self, pid):
        return set()

    def bring_front(self, hwnd):
        self.log.append(("front", hwnd))

    def send_hotkey(self, vks):
        self.log.append(("key", tuple(vks)))

    def wait_dialog(self, pid, before, timeout):
        return 7 if self.dialog else None

    def fill_and_accept(self, dlg, path):
        self.log.append(("fill", path))
        if self.fill_ok:
            self.sent_count += 1
        return self.fill_ok

    def close_dialog(self, dlg):
        self.log.append(("close", dlg))

    def wait_closed(self, dlg, t):
        return True

    def blocking_prompt(self, pid, before):
        return self.prompt_after is not None and self.sent_count >= self.prompt_after

    def dialog_title(self, dlg):
        return "Import"


def nosleep(_s):
    pass


@pytest.fixture()
def files(tmp_path):
    out = []
    for n in ("a.png", "b.wav", "c.moho"):
        p = tmp_path / n
        p.write_bytes(b"x")
        out.append(str(p))
    return out


MOHO = s.DEFAULT_PROFILES[0]


def test_parse_hotkey():
    assert s.parse_hotkey("ctrl+shift+y") == [0x11, 0x10, ord("Y")]
    assert s.parse_hotkey("Ctrl + O") == [0x11, ord("O")]
    assert s.parse_hotkey("f5") == [0x74]
    assert s.parse_hotkey("alt+1") == [0x12, ord("1")]
    for bad in ("", "ctrl+", "ctrl+shift", "ctrl+banana", "f13"):
        with pytest.raises(ValueError):
            s.parse_hotkey(bad)
    assert s.hotkey_ok("ctrl+i") and not s.hotkey_ok("ctrl+")


def test_send_all_files_in_order(files):
    d = FakeDriver()
    res = s.send_files(MOHO, files[:2], driver=d, sleep=nosleep)
    assert res.ok and res.sent == files[:2]
    keys = [e[1] for e in d.log if e[0] == "key"]
    assert keys == [tuple(s.parse_hotkey("ctrl+shift+y"))] * 2  # tệp ảnh và âm thanh dùng phím Nhập
    assert [e[1] for e in d.log if e[0] == "fill"] == files[:2]


def test_project_file_uses_open_hotkey(files):
    d = FakeDriver()
    s.send_files(MOHO, [files[2]], driver=d, sleep=nosleep)
    assert [e[1] for e in d.log if e[0] == "key"] == [tuple(s.parse_hotkey("ctrl+o"))]


def test_no_app_running(files):
    res = s.send_files(MOHO, files, driver=FakeDriver(app=False), sleep=nosleep)
    assert res.stop == "no_app" and res.remaining == [os.path.abspath(f) for f in files] and not res.sent
    assert "Chưa thấy Moho" in s.describe(res, MOHO)


def test_no_dialog_stops_whole_batch(files):
    d = FakeDriver(dialog=False)
    res = s.send_files(MOHO, files, driver=d, sleep=nosleep)
    assert res.stop == "no_dialog" and len(res.remaining) == 3
    assert len([e for e in d.log if e[0] == "key"]) == 1  # không bấm phím liên tục khi đã thất bại
    assert "mở dự án" in s.describe(res, MOHO)


def test_elevated_mismatch_reported(files):
    res = s.send_files(MOHO, files, driver=FakeDriver(elevated=True), sleep=nosleep)
    assert res.stop == "elevated" and "Administrator" in s.describe(res, MOHO)


def test_fill_failure_continues_with_next(files):
    d = FakeDriver(fill_ok=False)
    res = s.send_files(MOHO, files[:2], driver=d, sleep=nosleep)
    assert not res.sent and [f[1] for f in res.failed] == ["fill", "fill"]
    assert ("close", 7) in d.log


def test_missing_file_is_failed_not_fatal(files):
    d = FakeDriver()
    res = s.send_files(MOHO, [files[0] + ".nope", files[1]], driver=d, sleep=nosleep)
    assert res.sent == [files[1]] and res.failed[0][1] == "missing"


def test_pause_when_app_asks_a_question(files):
    d = FakeDriver(prompt_after=1)
    res = s.send_files(MOHO, files[:2], driver=d, sleep=nosleep)
    assert res.sent == [files[0]] and res.stop == "prompt" and res.remaining == [files[1]]
    assert "Trả lời" in s.describe(res, MOHO)


def test_not_windows():
    res = s.send_files(MOHO, ["x"], driver=FakeDriver(win=False), sleep=nosleep)
    assert res.stop == "platform"


def test_bad_hotkey_in_profile(files):
    prof = dict(MOHO, import_hotkey="ctrl+")
    res = s.send_files(prof, [files[0]], driver=FakeDriver(), sleep=nosleep)
    assert res.stop == "hotkey" and "Phím tắt" in s.describe(res, prof)


def test_paste_and_probe():
    d = FakeDriver()
    assert s.paste_clipboard(MOHO, driver=d, sleep=nosleep).ok
    assert ("key", tuple(s.parse_hotkey("ctrl+v"))) in d.log
    info = s.probe(MOHO, driver=FakeDriver(), sleep=nosleep)
    assert info["app"] and info["dialog"] and info["title"] == "Import"
    info2 = s.probe(MOHO, driver=FakeDriver(dialog=False), sleep=nosleep)
    assert info2["app"] and not info2["dialog"]
    assert s.probe(MOHO, driver=FakeDriver(app=False), sleep=nosleep)["app"] is None


def test_profiles_roundtrip_and_defaults():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        db = Database(os.path.join(tmp, "t.db"))
        profs = s.load_profiles(db)
        assert [p["id"] for p in profs][:4] == ["moho", "premiere", "aftereffects", "photoshop"]
        assert s.active_profile(db)["id"] == "moho"
        pid = s.new_profile_id(profs, "Krita Pro!")
        assert pid == "kritapro"
        profs.append({"id": pid, "name": "Krita Pro", "keywords": ["Krita"], "method": "dialog",
                      "import_hotkey": "Ctrl+O", "open_hotkey": "ctrl+o", "open_exts": ["kra"]})
        s.save_profiles(db, profs)
        s.set_active(db, pid)
        again = s.load_profiles(db)
        k = next(p for p in again if p["id"] == pid)
        assert k["keywords"] == ["krita"] and k["import_hotkey"] == "ctrl+o" and k["open_exts"] == [".kra"]
        assert s.active_profile(db)["id"] == pid
        # hồ sơ có sẵn bị xóa khỏi dữ liệu thì tự có lại
        s.save_profiles(db, [p for p in again if p["id"] != "moho"])
        assert "moho" in [p["id"] for p in s.load_profiles(db)]
        db.set_setting(s.SETTING_PROFILES, "không phải json")
        assert len(s.load_profiles(db)) == 4
        db.close()


@pytest.mark.skipif(os.name != "nt", reason="chỉ chạy trên Windows (kiểm tra tự động trên GitHub)")
def test_windows_driver_structures_and_lookup():
    """Trên Windows thật: cấu trúc SendInput đúng kích thước, tìm cửa sổ/hộp thoại không lỗi."""
    import ctypes
    d = s.WinDriver()
    d._init()
    assert ctypes.sizeof(d.INPUT) == (40 if ctypes.sizeof(ctypes.c_void_p) == 8 else 28)
    assert d.find_window(["khong-co-ung-dung-nay-xyz"]) is None
    assert d.dialog_handles(os.getpid()) == set()
    assert d._elevated(os.getpid()) in (True, False, None)
    assert d.needs_admin_match(os.getpid()) is False  # chính nó: cùng quyền với chính nó
