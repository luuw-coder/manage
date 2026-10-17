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
    tmp = tempfile.TemporaryDirectory()
    w = MainWindow(Database(os.path.join(tmp.name, "t.db")))
    w.show()
    w._tmp = tmp
    yield w
    w.close()
    tmp.cleanup()


def make(win, name):
    p = os.path.join(win._tmp.name, name)
    with open(p, "w") as f:
        f.write("x")
    return p


def test_default_tabs_and_empty_state(win):
    assert [b.text() for b in win.tab_group.buttons()] == ["Âm thanh", "Nhân vật", "Ảnh", "GIF"]
    assert win.stack.currentIndex() == 0  # chỉ có ô "Tải tệp lên"


def test_add_files_shows_list_and_switch_category(win):
    first = win.db.categories()[0]["id"]
    second = win.db.categories()[1]["id"]
    win.select_category(first)
    assert win.add_paths([make(win, "a.wav"), make(win, "b.wav")]) == 2
    assert win.stack.currentIndex() == 1 and win.list.count() == 2
    win.select_category(second)
    assert win.stack.currentIndex() == 0  # mục khác chưa có tệp


def test_search_filters(win):
    win.add_paths([make(win, "ba.png"), make(win, "cat.png")])
    win.search.setText("cat")
    assert win.list.count() == 1


def test_reload_drops_missing_silently(win):
    a = make(win, "a.png")
    win.add_paths([a, make(win, "b.png")])
    os.remove(a)
    win.reload_current()
    assert win.list.count() == 1


def test_collapse_and_restore(win):
    win.toggle_collapse()
    assert win.collapsed and not win.content.isVisible()
    win.toggle_collapse()
    assert not win.collapsed and win.content.isVisible()


def test_pin_toggle_and_opacity(win):
    win.pin_btn.setChecked(True)
    assert win.db.get_setting("pinned") == "1"
    win.pin_btn.setChecked(False)
    win.opacity_slider.setValue(40)
    assert win.db.get_setting("opacity") == "40"


def test_view_toggle(win):
    before = win.grid_mode
    win.toggle_view()
    assert win.grid_mode != before
