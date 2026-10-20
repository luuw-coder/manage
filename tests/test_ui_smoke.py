import os
import tempfile

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

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
    assert w.export_current() == out  # kéo nhiều lần không ghi lại tệp
    assert open(wav, "rb").read() == before
    w.wave.zoom(0.5)
    assert w.wave.view_len < w.wave.total()
    w.wave.grab()
    w.wave.fit()
    assert w.wave.view_len == w.wave.total()
    w.close()
