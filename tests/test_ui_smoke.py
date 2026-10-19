import os
import tempfile

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication  # noqa: E402

from app.db import Database  # noqa: E402
from app.main_window import MainWindow  # noqa: E402


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


def test_pagination_10_per_page(win):
    for i in range(25):
        mk(win, f"many/f{i:02d}.png")
    pick(win, "Ảnh")
    folder = os.path.join(win._tmp.name, "data", "many")
    win.add_roots([folder])
    win.navigate(folder)
    assert win.pages == 3 and win.list.count() == 10
    win.set_page(2)
    assert win.list.count() == 5 and win.pagebar.isVisible()
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
