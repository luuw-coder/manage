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
        return {"hwnd": 1, "pid": 42, "title": "Moho - test", "exe": r"C:\Apps\Moho.exe"} if self.app else None

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

    # --- cách script / JSFL
    menu_ok = True
    moho_result = "RESULT\t{n}\t0\n"
    programs = None

    def invoke_menu(self, hwnd, text):
        self.log.append(("menu", text))
        if self.menu_ok and getattr(self, "folder", None):
            q = open(os.path.join(self.folder, "moho_queue.txt"), encoding="utf-8").read().split()
            if self.moho_result is not None:
                open(os.path.join(self.folder, "moho_result.txt"), "w", encoding="utf-8").write(
                    self.moho_result.format(n=len(q)))
        return self.menu_ok

    def run_program(self, args):
        self.log.append(("run", tuple(args)))
        return True


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


MOHO = dict(s.DEFAULT_PROFILES[0], method="dialog")  # các bài này kiểm tra cách hộp thoại Nhập


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
        assert [p["id"] for p in profs][:5] == ["moho", "animate", "premiere", "aftereffects", "photoshop"]
        assert profs[0]["method"] == "moho_script" and profs[1]["method"] == "animate_jsfl"
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
        assert len(s.load_profiles(db)) == 5
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


# ---------------------------------------------------------------- Moho script Lua và Animate JSFL
MOHO_SCRIPT = dict(s.DEFAULT_PROFILES[0])
ANIMATE = dict(s.DEFAULT_PROFILES[1])


def test_moho_script_success_reads_result_from_moho(files, tmp_path):
    d = FakeDriver()
    d.folder = str(tmp_path / "x")
    res = s.send_files(MOHO_SCRIPT, files[:2], driver=d, sleep=nosleep, folder=d.folder)
    assert res.ok and res.sent == files[:2]
    q = open(os.path.join(d.folder, "moho_queue.txt"), encoding="utf-8").read().split()
    assert q == files[:2]
    assert ("menu", "Manage Moho") in d.log
    assert "Đã gửi vào Moho" in s.describe(res, MOHO_SCRIPT)


def test_moho_script_manual_when_menu_cannot_be_clicked(files, tmp_path):
    d = FakeDriver(); d.folder = str(tmp_path); d.menu_ok = False
    res = s.send_files(MOHO_SCRIPT, files[:1], driver=d, sleep=nosleep, folder=d.folder)
    assert res.stop == "manual" and "Scripts → Manage Moho - Import" in s.describe(res, MOHO_SCRIPT)
    assert os.path.exists(os.path.join(d.folder, "moho_queue.txt"))  # hàng đợi vẫn sẵn để bấm tay


def test_moho_script_uses_hotkey_when_menu_fails(files, tmp_path):
    d = FakeDriver(); d.folder = str(tmp_path); d.menu_ok = False
    prof = dict(MOHO_SCRIPT, script_hotkey="ctrl+alt+m")
    res = s.send_files(prof, files[:1], driver=d, sleep=nosleep, folder=d.folder)
    assert ("key", tuple(s.parse_hotkey("ctrl+alt+m"))) in d.log
    assert res.stop == "no_response"  # bấm rồi mà Moho không ghi kết quả -> báo script có thể chưa cài


def test_moho_script_reports_failures_and_no_document(files, tmp_path):
    d = FakeDriver(); d.folder = str(tmp_path)
    d.moho_result = "RESULT\t0\t1\nFAIL\t" + files[0] + "\tunsupported_type\n"
    res = s.send_files(MOHO_SCRIPT, files[:1], driver=d, sleep=nosleep, folder=d.folder)
    assert not res.sent and res.failed == [(files[0], "unsupported_type")]
    d2 = FakeDriver(); d2.folder = str(tmp_path / "b"); d2.moho_result = "RESULT\t0\t0\nNOTE\tno_document\n"
    r2 = s.send_files(MOHO_SCRIPT, files[:1], driver=d2, sleep=nosleep, folder=d2.folder)
    assert r2.stop == "no_document" and "chưa mở dự án" in s.describe(r2, MOHO_SCRIPT)


def test_moho_script_skips_types_it_cannot_import(files, tmp_path):
    d = FakeDriver(); d.folder = str(tmp_path)
    res = s.send_files(MOHO_SCRIPT, [files[2]], driver=d, sleep=nosleep, folder=d.folder)  # .moho
    assert not res.sent and res.failed[0][1] == "unsupported" and not any(e[0] == "menu" for e in d.log)


def test_animate_runs_jsfl_with_found_exe(files, tmp_path):
    d = FakeDriver()
    res = s.send_files(ANIMATE, files[:2], driver=d, sleep=nosleep, folder=str(tmp_path))
    assert res.ok and res.sent == files[:2]
    run = next(e[1] for e in d.log if e[0] == "run")
    assert run[0].endswith("Moho.exe") and run[1].endswith("animate_import.jsfl") and run[2] == "-AlwaysRunJSFL"
    code = open(run[1], encoding="utf-8").read()
    assert "importFile" in code and "file:///" in code and "a.png" in code
    assert s.send_files(ANIMATE, files[:1], driver=FakeDriver(app=False), sleep=nosleep,
                        folder=str(tmp_path)).stop == "no_app"


def test_result_and_queue_helpers(tmp_path):
    from app import moho_script as ms
    f = str(tmp_path)
    assert ms.read_result(f) is None
    open(os.path.join(f, "moho_result.txt"), "w").write("RESULT\t2\t1\nFAIL\tC:\\a.png\tboom\nNOTE\tx\n")
    r = ms.read_result(f)
    assert r == {"ok": 2, "failed": [("C:\\a.png", "boom")], "note": "x"}
    ms.write_queue(["a.png"], f)  # ghi hàng đợi mới thì xóa kết quả cũ
    assert ms.read_result(f) is None
    assert ms.classify("x.PNG") == "image" and ms.classify("x.wav") == "audio" and ms.classify("x.psd") == ""


def test_install_script_paths(tmp_path):
    from app import moho_script as ms
    p = ms.install_script(str(tmp_path / "Custom Content"))
    assert p.endswith(os.path.join("Scripts", "Menu", "ManageMoho_Import.lua")) and os.path.exists(p)
    p2 = ms.install_script(str(tmp_path / "Scripts"))
    assert p2.endswith(os.path.join("Scripts", "Menu", "ManageMoho_Import.lua"))
    p3 = ms.install_script(str(tmp_path / "Menu"))
    assert os.path.dirname(p3).endswith("Menu") and "Menu" + os.sep + "Menu" not in p3


def test_old_saved_profiles_are_upgraded(tmp_path):
    import json
    db = Database(str(tmp_path / "t.db"))
    old = dict(s.DEFAULT_PROFILES[0], method="dialog")
    db.set_setting(s.SETTING_PROFILES, json.dumps([old]))
    assert s.load_profiles(db)[0]["method"] == "moho_script"
    db.close()


lupa = pytest.importorskip("lupa", reason="cần lupa để chạy thử script Lua")


def _run_lua(tmp_path, queue_lines, with_doc=True, fail_ext=None):
    """Chạy script Lua thật với đối tượng 'moho' giả để kiểm tra logic nhập."""
    from app import moho_script as ms
    from lupa import LuaRuntime
    pub = tmp_path / "pub"
    (pub / "ManageMoho").mkdir(parents=True)
    (pub / "ManageMoho" / "moho_queue.txt").write_text("\n".join(queue_lines) + "\n", encoding="utf-8")
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute('MOHO = {LT_IMAGE = 2, LT_AUDIO = 9}; LM = {GUI = {ALERT_INFO = 0, Alert = function() end}}')
    lua.globals().os.getenv = lambda k: str(pub) if k == "PUBLIC" else None
    lua.execute(ms.LUA_SOURCE.replace(r'pub .. "\\ManageMoho\\"', 'pub .. "/ManageMoho/"'))
    log = []
    lua.execute("""
    function make_moho(log, has_doc)
      local m = {}
      if has_doc then m.document = {PrepUndo = function() end, SetDirty = function() end} end
      local function layer() local l = {}
        function l:SetName(n) log(l.kind .. ":" .. n) end
        function l:SetSourceImage(p) log("img:" .. p) end
        function l:SetAudioFile(p) log("aud:" .. p) end
        return l end
      function m:CreateNewLayer(t) local l = layer(); l.kind = (t == 2) and "image" or "audio"; return l end
      function m:LayerAsImage(l) return l end
      function m:LayerAsAudio(l) return l end
      function m:ImportEPS(p) log("eps:" .. p) end
      function m:UpdateUI() end
      return m end
    """)
    return lua, log, pub


def test_lua_script_imports_with_fake_moho(tmp_path):
    lua, log, pub = _run_lua(tmp_path, ["C:\\a\\x.PNG", "C:\\a\\s.wav", "C:\\a\\v.ai", "C:\\a\\bad.psd"])
    moho = lua.eval("make_moho")(lambda msg: log.append(msg), True)
    lua.globals().ManageMoho_Import.Run(lua.globals().ManageMoho_Import, moho)
    assert "img:C:\\a\\x.PNG" in log and "aud:C:\\a\\s.wav" in log and "eps:C:\\a\\v.ai" in log
    assert "image:x.PNG" in log and "audio:s.wav" in log  # đặt tên lớp theo tên tệp
    res = (pub / "ManageMoho" / "moho_result.txt").read_text(encoding="utf-8")
    assert res.startswith("RESULT\t3\t1") and "FAIL\tC:\\a\\bad.psd\tunsupported_type" in res.replace("\\\\", "\\") or "bad.psd" in res
    assert not (pub / "ManageMoho" / "moho_queue.txt").exists()  # hàng đợi đã dùng xong


def test_lua_script_without_open_project(tmp_path):
    lua, log, pub = _run_lua(tmp_path, ["C:\\a\\x.png"])
    moho = lua.eval("make_moho")(lambda msg: log.append(msg), False)
    lua.globals().ManageMoho_Import.Run(lua.globals().ManageMoho_Import, moho)
    assert "NOTE\tno_document" in (pub / "ManageMoho" / "moho_result.txt").read_text(encoding="utf-8")
    assert not log
