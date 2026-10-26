import os
import tempfile

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from app.audio_slice import AudioSliceWindow  # noqa: E402
from app.db import Database  # noqa: E402
from app.fsbrowse import make_entry  # noqa: E402
from app.main_window import MainWindow  # noqa: E402
from app.manage_dialog import ManageDialog  # noqa: E402
from app.script_window import ScriptWindow, diff_html  # noqa: E402
from tests.test_audio_scripts import make_wav  # noqa: E402


@pytest.fixture()
def win():
    app = QApplication.instance() or QApplication([])
    tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
    db = Database(os.path.join(tmp.name, "t.db"))
    db.set_setting("live_thumbs", "0")  # test không bật thẻ chuyển động (video giả không phát được)
    w = MainWindow(db)
    w.show()
    w._tmp = tmp
    yield w
    w.close()
    db.close()
    app.processEvents()
    tmp.cleanup()


def mk(win, rel, text="x"):
    p = os.path.join(win._tmp.name, "data", rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w") as f:
        f.write(text)
    return p


def pick(win, name):
    cid = next(c["id"] for c in win.cats if c["name"] == name)
    win.select_category(cid)
    return cid


def test_default_categories_and_empty_state(win):
    names = [c["name"] for c in win.cats]
    assert names[0] == "Tất cả" and "Model 3D" in names and "Dự án" in names and names[-1] == "Yêu thích"
    assert win.stack.currentIndex() == 0
    assert win.hero_btn.text() == "Tải thư mục lên"


def test_upload_mode_changes_button_text(win):
    win.toggle_mode()
    assert win.hero_btn.text() == "Tải tệp lên"
    win.toggle_mode()
    assert win.hero_btn.text() == "Tải thư mục lên"


def test_add_folder_navigate_up_and_back(win):
    mk(win, "chars/a.png")
    mk(win, "chars/sub/b.png")
    pick(win, "Nhân vật")
    folder = os.path.join(win._tmp.name, "data", "chars")
    assert win.add_roots([folder]) == 1
    assert win.list.count() == 1 and win.entries[0]["is_dir"]
    win.navigate(folder)
    names = sorted(e["name"] for e in win.entries)
    assert names == ["a.png", "sub"]
    win.navigate(os.path.join(folder, "sub"))
    assert [e["name"] for e in win.entries] == ["b.png"]
    win.go_up()
    assert win.view_path == os.path.normpath(folder)
    win.go_up()
    assert win.view_path is None
    win.go_back()
    assert win.view_path == os.path.normpath(folder)
    win.go_forward()
    assert win.view_path is None


def test_category_filter_hides_other_types_but_keeps_folders(win):
    mk(win, "mix/a.wav")
    mk(win, "mix/b.png")
    mk(win, "mix/inner/c.txt")
    pick(win, "Âm thanh")
    cid = win.current_cat
    win.db.update_category(cid, filters="audio")  # bật bộ lọc "chỉ âm thanh" cho mục này
    win.rebuild_cats(select=cid)
    folder = os.path.join(win._tmp.name, "data", "mix")
    win.add_roots([folder])
    win.navigate(folder)
    assert sorted(e["name"] for e in win.entries) == ["a.wav", "inner"]


def test_pagination_25_per_page(win):
    for i in range(60):
        mk(win, f"many/f{i:02d}.png")
    pick(win, "Ảnh")
    folder = os.path.join(win._tmp.name, "data", "many")
    win.add_roots([folder])
    win.navigate(folder)
    assert win.page_size == 25 and win.pages == 3 and win.list.count() == 25
    win.set_page(2)
    assert win.list.count() == 10 and win.pagebar.isVisible()
    win.set_page(0)
    assert win.page == 0


def test_search_filters(win):
    mk(win, "s/cat.png")
    mk(win, "s/dog.png")
    pick(win, "Ảnh")
    folder = os.path.join(win._tmp.name, "data", "s")
    win.add_roots([folder])
    win.navigate(folder)
    win.search.setText("cat")
    win.on_search()
    assert [e["name"] for e in win.entries] == ["cat.png"]


def test_rename_reset_on_reload_keeps_favorite(win):
    a = mk(win, "r/a.png")
    pick(win, "Ảnh")
    folder = os.path.dirname(a)
    win.add_roots([folder])
    win.navigate(folder)
    win.db.set_display_name(a, "Nhân vật chính")
    win.db.set_favorite(a, True)
    win.refresh()
    assert win.entries[0]["label"] == "Nhân vật chính" and win.entries[0]["fav"]
    win.reload_current()
    assert win.entries[0]["label"] == "a.png" and win.entries[0]["fav"]
    assert os.path.exists(a)


def test_favorites_category_lists_favorites(win):
    a = mk(win, "f/a.png")
    win.db.set_favorite(a, True)
    pick(win, "Yêu thích")
    assert [e["name"] for e in win.entries] == ["a.png"]


def test_delete_builtin_category_and_restore(win):
    cid = next(c["id"] for c in win.cats if c["name"] == "Video")
    win.db.delete_category(cid)
    win.rebuild_cats(select=None)
    assert "Video" not in [c["name"] for c in win.cats]
    win.restore_default_cats()
    assert "Video" in [c["name"] for c in win.cats]


def test_add_category_with_icon(win):
    cid = win.db.add_category("Cảnh phim", icon="film", color="#ff0000")
    win.rebuild_cats(select=cid)
    assert win.current_category()["name"] == "Cảnh phim"
    assert win.cats_grid.count() == len(win.cat_buttons)


def test_missing_root_pruned_silently_on_reload(win):
    a = mk(win, "gone/a.wav")
    pick(win, "Âm thanh")
    folder = os.path.dirname(a)
    win.add_roots([folder])
    os.remove(a)
    os.rmdir(folder)
    win.reload_current()
    assert win.entries == [] and win.stack.currentIndex() == 0


def test_collapse_pin_fade_view(win):
    win.toggle_collapse()
    assert win.collapsed and not win.body.isVisible()
    win.toggle_collapse()
    assert not win.collapsed and win.body.isVisible()
    win.pin_btn.setChecked(True)
    assert win.db.get_setting("pinned") == "1"
    win.pin_btn.setChecked(False)
    win.fade_btn.setChecked(True)
    assert win.fadebar.isVisible() or win.db.get_setting("fade_on") == "1"
    win.opacity_slider.setValue(40)
    assert win.db.get_setting("opacity") == "40"
    before = win.grid_mode
    win.toggle_view()
    assert win.grid_mode != before


def entry_of(path):
    e = make_entry(path)
    e.update(label=e["name"], fav=False, pinned=False)
    return e


def test_default_filter_is_all_files(win):
    mk(win, "mix/a.wav")
    mk(win, "mix/b.png")
    mk(win, "mix/c.mp4")
    pick(win, "Âm thanh")
    folder = os.path.join(win._tmp.name, "data", "mix")
    win.add_roots([folder])
    win.navigate(folder)
    assert sorted(e["name"] for e in win.entries) == ["a.wav", "b.png", "c.mp4"]


def test_blender_and_3d_files_listed_and_draggable(win):
    paths = [mk(win, f"m3d/{n}") for n in ("scene.blend", "rig.fbx", "prop.obj", "x.glb")]
    pick(win, "Model 3D")
    folder = os.path.dirname(paths[0])
    win.add_roots([folder])
    win.navigate(folder)
    assert sorted(e["name"] for e in win.entries) == ["prop.obj", "rig.fbx", "scene.blend", "x.glb"]
    items = [win.list.item(i) for i in range(win.list.count())]
    md = win.list.mimeData(items)
    got = sorted(os.path.basename(u.toLocalFile()) for u in md.urls())
    assert got == ["prop.obj", "rig.fbx", "scene.blend", "x.glb"]
    assert all(os.path.exists(p) for p in paths)  # kéo ra chỉ sao chép, tệp gốc còn nguyên


def test_preview_panel_image_folder_and_3d(win):
    from PySide6.QtGui import QImage
    folder = os.path.join(win._tmp.name, "data", "pv")
    os.makedirs(folder)
    img = QImage(60, 40, QImage.Format_RGB32)
    img.fill(0xFF3366)
    png = os.path.join(folder, "a.png")
    assert img.save(png)
    blend = mk(win, "pv/scene.blend")
    win.preview.open_entry(entry_of(png))
    assert win.preview.is_open() and win.preview.stage.currentIndex() == 0
    assert "60 × 40" in win.preview.info.text()
    win.preview.open_entry(entry_of(folder))
    assert win.preview.stage.currentIndex() == 3 and "tệp" in win.preview.info.text()
    win.preview.open_entry(entry_of(blend))
    assert win.preview.stage.currentIndex() == 4 and "BLEND" in win.preview.info.text()
    win.preview.close_panel()
    win.preview.hard_close()
    assert not win.preview.isVisible()


def test_double_click_file_opens_panel(win):
    a = mk(win, "dc/a.png")
    pick(win, "Ảnh")
    folder = os.path.dirname(a)
    win.add_roots([folder])
    win.navigate(folder)
    win.on_item_double(win.list.item(0))
    assert win.preview.is_open()
    win.preview.hard_close()


def test_script_window_edit_autosave_versions_layout(win):
    sw = ScriptWindow(win.db, win.script_store, win)
    sw.new_script()
    name = sw.current
    sw.editor.setPlainText("CẢNH 1 – SÂN – NGÀY\n")
    sw.save_now()
    assert win.script_store.read(name).startswith("CẢNH 1")
    sw.insert_template("scene")
    assert "CẢNH 2" in sw.editor.toPlainText()
    sw.editor.setPlainText("bản đầu")
    vid = sw.save_version("v1")
    sw.editor.setPlainText("bản sửa")
    sw.save_now()
    sw.restore_version(vid)
    assert sw.editor.toPlainText() == "bản đầu"
    assert any(v["label"] == "Trước khi khôi phục" for v in win.db.versions(name))
    assert [a["provider"] for a in win.db.ai_accounts()][:3] == ["ChatGPT", "Gemini", "Claude"]
    assert sw.ai.list.count() >= 5
    sw.save_layout()
    assert win.db.get_setting("script_split_main")
    assert sw.split_main.count() == 2 and sw.split_left.count() == 2
    assert "Phiên bản" in diff_html("a\nb", "a\nc")
    sw.close()


def test_open_script_and_manage_from_main(win):
    win.open_script()
    assert win.script_win is not None and win.script_win.isVisible()
    dlg = ManageDialog(win)
    dlg.page_spin.setValue(40)
    dlg.apply()
    assert win.db.get_setting("page_size") == "40" and win.page_size == 40
    path = os.path.join(win._tmp.name, "bk.json")
    dlg.backup(path)
    assert os.path.exists(path)
    dlg.close()


def test_audio_slice_selects_exports_without_touching_original(win):
    wav = os.path.join(win._tmp.name, "voice.wav")
    make_wav(wav, 2.0, 8000, 2)
    before = open(wav, "rb").read()
    w = AudioSliceWindow(win.db, wav, win)
    w.show()
    assert w.pcm is not None and w.pcm.frames == 16000
    w.wave.grab()  # vẽ hình sóng
    w.wave.set_selection(1000, 4000)
    assert abs(w.start_spin.value() - 0.125) < 0.001 and abs(w.end_spin.value() - 0.5) < 0.001
    out = w.export_current()
    assert out and os.path.exists(out) and out != wav
    assert w.wave.drag_provider() == out  # kéo thẳng vùng bôi đen: tool tự tạo tệp
    assert w.export_current() == out  # kéo nhiều lần không ghi lại tệp
    assert open(wav, "rb").read() == before
    w.wave.zoom(0.5)
    assert w.wave.view_len < w.wave.total()
    w.wave.grab()
    w.wave.fit()
    assert w.wave.view_len == w.wave.total()
    w.close()


def test_two_files_per_row(win):
    for i in range(6):
        mk(win, f"grid/f{i}.png")
    pick(win, "Ảnh")
    folder = os.path.join(win._tmp.name, "data", "grid")
    win.add_roots([folder])
    win.navigate(folder)
    win.resize(340, 580)
    QApplication.processEvents()
    win.list.apply_grid()
    gw, vw = win.list.gridSize().width(), win.list.viewport().width()
    assert 2 * gw <= vw and 3 * gw > vw


def test_gif_card_is_live_and_stops(win):
    import base64
    gif = base64.b64decode("R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7")
    path = os.path.join(win._tmp.name, "data", "live", "a.gif")
    os.makedirs(os.path.dirname(path))
    with open(path, "wb") as f:
        f.write(gif)
    win.live.enabled = True
    pick(win, "GIF")
    win.add_roots([os.path.dirname(path)])
    win.navigate(os.path.dirname(path))
    assert len(win.live.movies) == 1
    win.live.stop_all()
    assert win.live.movies == {}


def test_audio_hover_path_only_for_audio(win):
    a = mk(win, "h/a.wav")
    mk(win, "h/b.png")
    pick(win, "Ảnh")
    folder = os.path.dirname(a)
    win.add_roots([folder])
    win.navigate(folder)
    items = {win.list.item(i).data(Qt.UserRole)["name"]: win.list.item(i) for i in range(win.list.count())}
    win.hover_enabled = True
    assert win.audio_hover_path(items["a.wav"]) == os.path.normpath(a)
    assert win.audio_hover_path(items["b.png"]) is None
    assert win.audio_hover_path(None) is None
    win.hover_enabled = False
    assert win.audio_hover_path(items["a.wav"]) is None


def test_closing_main_window_keeps_script_window_open(win):
    win.open_script()
    sw = win.script_win
    assert sw.parent() is None
    win.close()
    assert sw.isVisible()
    sw.close()


def test_script_rich_formatting_is_saved_and_reloaded(win):
    sw = ScriptWindow(win.db, win.script_store, None)
    sw.new_script()
    name = sw.current
    sw.editor.setHtml('<p align="center"><span style="color:#ff0000;">đỏ</span></p>')
    sw.save_now()
    assert "ff0000" in win.script_store.read_html(name).lower()
    assert win.script_store.read(name).strip() == "đỏ"
    sw.set_align(Qt.AlignRight)
    assert sw.editor.alignment() & Qt.AlignRight
    sw.editor.selectAll()
    sw.set_color("#00ff00")
    sw.set_background("#112233")
    sw.save_now()
    html = win.script_store.read_html(name).lower()
    assert "00ff00" in html and "112233" in html
    sw.open_script(name)
    assert "00ff00" in sw.editor.toHtml().lower()
    sw.close()


def test_native_drag_helpers_are_safe(win):
    from app import native_drag
    assert isinstance(native_drag.available(), bool)
    with pytest.raises(OSError):  # không có tệp thật: ném lỗi ngay, không gọi API Windows
        native_drag.drag_files(0, ["Z:\\khong\\co\\tep.png"])


def test_drag_finished_reports_result_and_logs(win):
    from app import native_drag
    native_drag.last_info.clear()
    a = mk(win, "d/a.png")
    win.on_drag_finished([a], "Ignore", 120)
    assert "Chưa có ứng dụng nào nhận" in win.toast_label.text()
    win.on_drag_finished([a], "Copy", 900)
    assert "Đã thả" in win.toast_label.text()
    log = open(os.path.join(os.path.dirname(win.db.path), "keo.log"), encoding="utf-8").read()
    assert "| Ignore |" in log and "| Copy |" in log


def test_drag_finished_says_where_you_dropped(win):
    from app import native_drag
    a = mk(win, "d/a.png")
    native_drag.last_info.clear()
    native_drag.last_info.update({"tha_vao": "chrome.exe"})
    win.on_drag_finished([a], "Ignore", 100)
    assert "không phải Moho" in win.toast_label.text() and "chrome.exe" in win.toast_label.text()
    native_drag.last_info.clear()
    native_drag.last_info.update({"tha_vao": "Moho.exe"})
    win.on_drag_finished([a], "Ignore", 100)
    assert "Moho từ chối" in win.toast_label.text() and "Gửi vào Moho" in win.toast_label.text()
    native_drag.last_info.clear()
    native_drag.last_info.update({"huy": True})
    win.on_drag_finished([a], "Ignore", 100)
    assert "Đã hủy" in win.toast_label.text()
    native_drag.last_info.clear()


def _grid_window(win, n=4):
    for i in range(n):
        mk(win, f"cell/f{i}.png")
    pick(win, "Ảnh")
    folder = os.path.join(win._tmp.name, "data", "cell")
    win.add_roots([folder])
    win.navigate(folder)
    win.resize(340, 580)
    QApplication.processEvents()
    win.list.apply_grid()
    win.list.doItemsLayout()  # ép Qt xếp lại lưới ngay (bình thường Qt xếp trễ một nhịp)
    QApplication.processEvents()


def _name(item):
    return item.data(Qt.UserRole)["name"]


def test_item_at_uses_grid_cells_and_selection_rect_is_off(win):
    from PySide6.QtCore import QPoint
    _grid_window(win)
    assert not win.list.isSelectionRectVisible()
    gs = win.list.gridSize()
    assert 2 * gs.width() <= win.list.viewport().width()
    # phần trống ở mép phải ô đầu vẫn là thẻ đầu; ô kế bên là thẻ thứ hai
    assert _name(win.list.item_at(QPoint(gs.width() - 3, 3))) == "f0.png"
    assert _name(win.list.item_at(QPoint(gs.width() + 3, 3))) == "f1.png"
    # hàng thứ hai
    assert _name(win.list.item_at(QPoint(3, gs.height() + 3))) == "f2.png"
    assert win.list.item_at(QPoint(3, gs.height() * 5)) is None


def test_click_in_empty_part_of_cell_selects_that_card(win):
    from PySide6.QtCore import QPoint
    from PySide6.QtTest import QTest
    _grid_window(win)
    gs = win.list.gridSize()
    vp = win.list.viewport()
    QTest.mouseClick(vp, Qt.LeftButton, Qt.NoModifier, QPoint(gs.width() - 3, 3))
    assert [_name(i) for i in win.list.selectedItems()] == ["f0.png"]
    QTest.mouseClick(vp, Qt.LeftButton, Qt.NoModifier, QPoint(gs.width() + 3, 3))
    assert [_name(i) for i in win.list.selectedItems()] == ["f1.png"]
    QTest.mouseClick(vp, Qt.LeftButton, Qt.ControlModifier, QPoint(3, gs.height() + 3))
    assert sorted(_name(i) for i in win.list.selectedItems()) == ["f1.png", "f2.png"]
    # quy tắc chọn sau khi Ctrl được kiểm tra riêng trong tests/test_drag_select.py (không phụ thuộc Qt)


def test_manage_toggles_native_drag_and_default_is_standard_qt(win):
    from app import widgets
    assert widgets.USE_NATIVE is False
    dlg = ManageDialog(win)
    assert not dlg.native_check.isChecked()
    dlg.native_check.setChecked(True)
    dlg.apply()
    assert win.db.get_setting("native_drag2") == "1" and widgets.USE_NATIVE is True
    dlg.native_check.setChecked(False)
    dlg.apply()
    assert widgets.USE_NATIVE is False
    dlg.close()


def test_drag_test_box_creates_real_test_file(win):
    dlg = ManageDialog(win)
    path = dlg.make_test_file()
    assert os.path.isfile(path) and path.endswith("kiem_tra_keo_tha.txt")
    assert dlg.test_chip.provider() == path
    dlg._test_done(path, "Copy", 800)
    assert "Copy" in dlg.test_status.text()
    dlg.close()


def test_start_file_drag_ignores_missing_files_without_dragging(win):
    from app import widgets
    assert widgets.start_file_drag(win, ["Z:\\khong\\co\\tep.png"]) == ("Ignore", 0)


# ---------------------------------------------------------------- menu chuột phải và Gửi vào ứng dụng đích
def E(path):
    e = make_entry(path)
    for k, v in (("fav", False), ("pinned", False)):
        e.setdefault(k, v)
    e.setdefault("label", e["name"])
    return e


def _menu_texts(menu):
    return [a.text() for a in menu.actions() if a.text()]


def test_file_context_menus_build_and_offer_send(win):
    from PySide6.QtWidgets import QMenu
    a = mk(win, "d/a.png")
    b = mk(win, "d/b.wav")
    ea, eb = E(a), E(b)
    m = QMenu()
    win.fill_single_menu(m, ea)  # trước đây báo lỗi NameError vì thiếu hàm act
    texts = _menu_texts(m)
    assert "Gửi vào Moho" in texts and "Gửi vào Moho bằng hộp thoại Nhập (dự phòng)" in texts and "Dán ảnh vào Moho (Ctrl+V)" in texts
    m2 = QMenu()
    win.fill_single_menu(m2, eb)
    t2 = _menu_texts(m2)
    assert "Gửi vào Moho" in t2 and "Dán ảnh vào Moho (Ctrl+V)" not in t2  # âm thanh không dán được
    assert "Cắt âm thanh..." in t2
    m3 = QMenu()
    win.fill_multi_menu(m3, [ea, eb])
    assert "Gửi vào Moho" in _menu_texts(m3)
    folder = E(os.path.dirname(a))
    m4 = QMenu()
    win.fill_single_menu(m4, folder)
    assert not any(t.startswith("Gửi vào") for t in _menu_texts(m4))  # thư mục không gửi được


def test_send_to_target_runs_in_background_and_reports(win, monkeypatch):
    import time as _t
    from app import send_to_app
    a = mk(win, "d/a.png")
    seen = {}

    def fake_send(profile, paths, **kw):
        seen["profile"], seen["paths"] = profile["id"], list(paths)
        r = send_to_app.SendResult()
        r.sent = list(paths)
        return r

    monkeypatch.setattr(send_to_app, "send_files", fake_send)
    win.send_to_target([a])
    end = _t.time() + 3
    while _t.time() < end and "Đã gửi vào Moho" not in win.toast_label.text():
        QApplication.processEvents()
        _t.sleep(0.01)
    assert seen == {"profile": "moho", "paths": [a]}
    assert "Đã gửi vào Moho: a.png" in win.toast_label.text() and win._sending is False


def test_preview_has_send_button_named_after_target(win):
    a = mk(win, "d/a.png")
    win.preview.open_entry(E(a))
    assert win.preview.send_btn.text() == "Gửi vào Moho" and not win.preview.send_btn.isHidden()
    win.preview.open_entry(E(os.path.dirname(a)))
    assert win.preview.send_btn.isHidden()


def test_targets_tab_add_save_delete(win, monkeypatch):
    from PySide6.QtWidgets import QInputDialog
    from app import send_to_app
    dlg = ManageDialog(win)
    assert dlg.target_combo.count() >= 4 and dlg.t_import.text() == "ctrl+shift+y"
    monkeypatch.setattr(QInputDialog, "getText", staticmethod(lambda *a, **k: ("Krita", True)))
    dlg._target_add()
    assert dlg.t_name.text() == "Krita" and dlg.t_keys.text() == "krita" and dlg.t_del.isEnabled()
    dlg.t_import.setText("ctrl+")  # phím tắt sai bị từ chối, không lưu
    dlg._target_save()
    assert "Cần thêm một phím thường" in dlg.t_status.text()
    dlg.t_import.setText("ctrl+i")
    dlg._target_save()
    assert send_to_app.active_profile(win.db)["id"] == "krita" and win.preview.send_btn.text().endswith("Moho")
    m = __import__("PySide6.QtWidgets", fromlist=["QMenu"]).QMenu()
    win.fill_single_menu(m, E(mk(win, "d/z.png")))
    assert "Gửi vào Krita (hộp thoại Nhập)" in _menu_texts(m)
    dlg._target_delete()
    assert send_to_app.active_profile(win.db)["id"] == "moho"
    dlg.t_del.isEnabled() is False
    dlg.close()


def test_targets_tab_install_script_and_methods(win, tmp_path, monkeypatch):
    from PySide6.QtWidgets import QFileDialog
    dlg = ManageDialog(win)
    assert dlg.t_method.currentData() == "moho_script" and dlg.t_menu.text() == "Manage Moho"
    monkeypatch.setattr(QFileDialog, "getExistingDirectory", staticmethod(lambda *a, **k: str(tmp_path / "CC")))
    dlg._install_moho_script()
    assert os.path.exists(tmp_path / "CC" / "Scripts" / "Menu" / "ManageMoho_Import.lua")
    assert "KHỞI ĐỘNG LẠI Moho" in dlg.t_status.text()
    dlg.t_script_key.setText("ctrl+")  # phím gọi script sai bị từ chối
    dlg._target_save()
    assert "Phím tắt gọi script" in dlg.t_status.text()
    dlg.t_script_key.setText("ctrl+alt+m")
    dlg._target_save()
    from app import send_to_app
    assert send_to_app.active_profile(win.db)["script_hotkey"] == "ctrl+alt+m"
    dlg.close()


def test_drag_modes_setting_and_lab_chips(win):
    from app import widgets
    dlg = ManageDialog(win)
    assert dlg.mode_combo.count() == 1 + len(widgets.DRAG_MODES)
    dlg.mode_combo.setCurrentIndex(dlg.mode_combo.findData("win_copylink"))
    dlg.apply()
    assert win.db.get_setting("drag_mode") == "win_copylink" and widgets.DRAG_MODE == "win_copylink"
    p = dlg.make_test_png()
    assert os.path.exists(p) and p.endswith("kiem_tra_moho.png")
    chips = [c for c in dlg.findChildren(widgets.DragChip) if c.mode]
    assert [c.mode for c in chips] == [k for k, _l in widgets.DRAG_MODES]
    dlg.mode_combo.setCurrentIndex(0)
    dlg.apply()
    assert widgets.DRAG_MODE == ""
    dlg.close()
