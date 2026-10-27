"""Kiểm tra: xem 3D, dọn tệp âm thanh cắt, khung AI nhúng, hướng dẫn trong phần mềm."""
import math
import os
import struct
import time

import pytest
from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtWidgets import QApplication

from app import cleanup, model_viewer as mv, webpanel

CUBE_OBJ = """v -1 -1 -1
v 1 -1 -1
v 1 1 -1
v -1 1 -1
v -1 -1 1
v 1 -1 1
v 1 1 1
v -1 1 1
f 1 2 3 4
f 5 8 7 6
f 1 5 6 2
f 2 6 7 3
f 3 7 8 4
f 4 8 5 1
"""


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def test_obj_quads_become_triangles_and_are_centered(tmp_path):
    p = tmp_path / "cube.obj"
    p.write_text(CUBE_OBJ)
    m = mv.load_model(str(p))
    assert m.face_count == 12 and len(m.verts) == 8 and not m.simplified
    assert max(abs(c) for v in m.verts for c in v) == pytest.approx(1.0)


def test_obj_negative_indices_and_slashes(tmp_path):
    p = tmp_path / "t.obj"
    p.write_text("v 0 0 0\nv 1 0 0\nv 0 1 0\nvt 0 0\nvn 0 0 1\nf 1/1/1 2/1/1 3/1/1\nf -3 -2 -1\n")
    m = mv.load_model(str(p))
    assert m.face_count == 2 and set(m.faces) == {(0, 1, 2)}


def test_stl_ascii_and_binary(tmp_path):
    a = tmp_path / "a.stl"
    a.write_text("solid x\nfacet normal 0 0 1\nouter loop\nvertex 0 0 0\nvertex 1 0 0\nvertex 0 1 0\nendloop\nendfacet\nendsolid\n")
    assert mv.load_model(str(a)).face_count == 1
    b = tmp_path / "b.stl"
    tri = struct.pack("<12fH", 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0)
    b.write_bytes(b"\0" * 80 + struct.pack("<I", 2) + tri + tri)
    assert mv.load_model(str(b)).face_count == 2


def test_unsupported_empty_and_huge_models_give_clear_errors(tmp_path):
    f = tmp_path / "x.fbx"
    f.write_bytes(b"x")
    with pytest.raises(mv.ModelError, match="OBJ, STL"):
        mv.load_model(str(f))
    e = tmp_path / "e.obj"
    e.write_text("# trống\n")
    with pytest.raises(mv.ModelError, match="Không đọc được"):
        mv.load_model(str(e))
    big = tmp_path / "big.obj"
    lines = ["v 0 0 0", "v 1 0 0", "v 0 1 0"] + ["f 1 2 3"] * (mv.MAX_FACES * 3)
    big.write_text("\n".join(lines))
    m = mv.load_model(str(big))
    assert m.simplified and m.face_count <= mv.MAX_FACES


def test_view_rotate_zoom_pan_reset(app, tmp_path):
    p = tmp_path / "cube.obj"
    p.write_text(CUBE_OBJ)
    v = mv.ModelView()
    v.resize(300, 300)
    v.set_model(mv.load_model(str(p)))
    yaw0, zoom0 = v.yaw, v.zoom
    from PySide6.QtGui import QMouseEvent, QWheelEvent
    from PySide6.QtCore import QEvent, QPointF as P
    press = QMouseEvent(QEvent.MouseButtonPress, P(10, 10), P(10, 10), Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)
    move = QMouseEvent(QEvent.MouseMove, P(60, 40), P(60, 40), Qt.NoButton, Qt.LeftButton, Qt.NoModifier)
    v.mousePressEvent(press)
    v.mouseMoveEvent(move)
    assert v.yaw == pytest.approx(yaw0 + 0.5) and v.pitch != 0.35
    wheel = QWheelEvent(P(100, 100), P(100, 100), QPoint(0, 0), QPoint(0, 120), Qt.NoButton, Qt.NoModifier,
                        Qt.NoScrollPhase, False)
    v.wheelEvent(wheel)
    assert v.zoom > zoom0
    rpress = QMouseEvent(QEvent.MouseButtonPress, P(10, 10), P(10, 10), Qt.RightButton, Qt.RightButton, Qt.NoModifier)
    rmove = QMouseEvent(QEvent.MouseMove, P(30, 25), P(30, 25), Qt.NoButton, Qt.RightButton, Qt.NoModifier)
    v.mousePressEvent(rpress)
    v.mouseMoveEvent(rmove)
    assert v.pan == QPointF(20, 15)
    v.mouseDoubleClickEvent(None)
    assert v.zoom == 1.0 and v.pan == QPointF(0, 0)
    polys = v.projected()
    assert len(polys) == 12 and all(0 <= s <= 1 for _z, _p, s in polys)
    assert [z for z, _p, _s in polys] == sorted(z for z, _p, _s in polys)  # vẽ từ xa tới gần
    v.grab()  # vẽ được không lỗi
    v.clear("hết")
    v.grab()


def test_cleanup_policies(tmp_path):
    d = tmp_path / "ex"
    d.mkdir()
    old, new, other = d / "old.wav", d / "new.wav", d / "note.txt"
    for f in (old, new, other):
        f.write_bytes(b"x" * 1000)
    past = time.time() - 10 * 86400
    os.utime(old, (past, past))
    assert cleanup.folder_usage(str(d)) == (2, 2000)  # chỉ đếm .wav
    assert cleanup.purge(str(d), 7) == (1, 1000)
    assert new.exists() and not old.exists() and other.exists()
    assert cleanup.purge(str(d), keep=[str(new)]) == (0, 0)
    assert cleanup.purge(str(d)) == (1, 1000) and other.exists()  # không bao giờ đụng tệp khác .wav
    assert cleanup.human(1536) == "1.5 KB" and cleanup.human(10) == "10 B"


def test_clean_user_agent_removes_qtwebengine_token():
    ua = "Mozilla/5.0 (Windows NT 10.0) AppleWebKit/537.36 (KHTML, like Gecko) QtWebEngine/6.8.1 Chrome/122.0.0.0 Safari/537.36"
    out = webpanel.clean_user_agent(ua)
    assert "QtWebEngine" not in out and "Chrome/122.0.0.0 Safari/537.36" in out


def test_guide_mentions_core_features():
    from app.guide import GUIDE_MD
    for word in ("Kéo thả", "Cắt âm thanh", "Model 3D", "Hỏi AI", "keo.log", "Gửi vào Moho"):
        assert word.lower() in GUIDE_MD.lower()
    assert "cài đặt phần mềm" not in GUIDE_MD.lower()  # hướng dẫn sử dụng, không phải hướng dẫn cài đặt
