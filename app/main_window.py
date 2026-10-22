import os
import shutil
import time

from PySide6.QtCore import QMimeData, QSize, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QColor, QDesktopServices, QGuiApplication, QIcon, QKeySequence, QPainter, QShortcut
from PySide6.QtWidgets import (
    QAbstractItemView, QApplication, QFileDialog, QFrame, QGridLayout, QHBoxLayout, QInputDialog,
    QLabel, QLineEdit, QListView, QListWidget, QListWidgetItem, QMenu, QMessageBox, QPushButton,
    QSizePolicy, QSlider, QStackedWidget, QToolButton, QVBoxLayout, QWidget,
)

from . import drag_log, moho_bridge, native_drag
from .audio_slice import AudioSliceWindow
from .db import Database
from .dialogs import CategoryDialog, FilterDialog
from .fsbrowse import (
    AUDIO_EXTS, GROUPS_VERSION, breadcrumb, deep_search, exts_for, groups_from_json, groups_to_json,
    human_size, list_dir, make_entry, merge_default_groups, page_buttons, page_slice, pkey, root_of, sort_items,
)
from .icons import category_icon, make_icon
from .live_thumbs import HoverAudio, LiveThumbs
from .manage_dialog import ManageDialog
from .preview_panel import PreviewPanel
from .script_window import ScriptWindow
from .scripts_store import ScriptStore
from .theme import QSS
from .thumbs import compose
from . import widgets
from .widgets import ElidedLabel, start_file_drag


class FileList(QListWidget):
    """Lưới thẻ. Kéo thẻ ra ngoài sẽ mang theo đường dẫn tệp thật (để kéo sang Moho)."""

    hoverItem = Signal(object)          # thẻ đang rê chuột vào (hoặc None)
    dragStarted = Signal()
    dragFinished = Signal(object, str, int)  # đường dẫn, kiểu thả, số ms

    def __init__(self):
        super().__init__()
        self._grid = True
        self._hover_row = -1
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setDragEnabled(False)  # tự xử lý kéo (giống cắt âm thanh), không dùng cơ chế mặc định của Qt
        self._press_pos = None
        self._press_item = None
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.setWordWrap(True)
        self.setMouseTracking(True)
        self.setSelectionRectVisible(False)  # bỏ khung chọn trong suốt khi kéo chuột
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.set_grid_mode(True)

    def set_grid_mode(self, grid):
        self._grid = grid
        if grid:
            self.setViewMode(QListView.IconMode)
            self.setIconSize(QSize(112, 76))
            self.apply_grid()
        else:
            self.setViewMode(QListView.ListMode)
            self.setIconSize(QSize(56, 38))
            self.setGridSize(QSize())
        self.setResizeMode(QListView.Adjust)
        self.setMovement(QListView.Static)

    def apply_grid(self):
        """Luôn 2 tệp mỗi hàng."""
        if self._grid:
            self.setGridSize(QSize(max(110, (self.viewport().width() - 4) // 2), 118))

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.apply_grid()

    def item_at(self, pos):
        """Thẻ tại vị trí chuột. Tính theo cả ô lưới, nên nhấn vào phần trống quanh biểu tượng cũng tính."""
        it = self.itemAt(pos)
        if it is not None or not self._grid:
            return it
        gs = self.gridSize()
        if gs.width() <= 0 or gs.height() <= 0:
            return None
        cols = max(1, self.viewport().width() // gs.width())
        c = pos.x() // gs.width()
        r = (pos.y() + self.verticalScrollBar().value()) // gs.height()
        if c < 0 or c >= cols or r < 0:
            return None
        idx = r * cols + c
        return self.item(idx) if 0 <= idx < self.count() else None

    def mousePressEvent(self, e):
        if e.button() != Qt.LeftButton:
            super().mousePressEvent(e)
            return
        pos = e.position().toPoint()
        self._press_pos = pos
        self._press_item = self.item_at(pos)
        if self._press_item is not None and self.itemAt(pos) is None:
            # nhấn vào phần trống của ô: tự chọn thẻ, không để Qt bắt đầu khung chọn
            if not (QApplication.keyboardModifiers() & (Qt.ControlModifier | Qt.ShiftModifier)):
                self.clearSelection()
            self._press_item.setSelected(True)
            return
        super().mousePressEvent(e)

    def mouseReleaseEvent(self, e):
        pos = e.position().toPoint()
        if (self._press_pos is not None and self._press_item is not None and self.itemAt(pos) is None
                and self.item_at(pos) is self._press_item):
            item = self._press_item
            self._press_pos = self._press_item = None
            self.itemClicked.emit(item)
            return
        self._press_pos = None
        self._press_item = None
        super().mouseReleaseEvent(e)

    def mouseDoubleClickEvent(self, e):
        pos = e.position().toPoint()
        if self.itemAt(pos) is None and self.item_at(pos) is not None:
            self.itemDoubleClicked.emit(self.item_at(pos))
            return
        super().mouseDoubleClickEvent(e)

    def mouseMoveEvent(self, e):
        if e.buttons() & Qt.LeftButton:
            if (self._press_pos is not None and self._press_item is not None
                    and (e.position().toPoint() - self._press_pos).manhattanLength() >= QApplication.startDragDistance()):
                self._press_pos = None
                self._begin_drag()
            return  # đang giữ chuột: không cho Qt vẽ khung chọn (màng trong suốt)
        super().mouseMoveEvent(e)
        it = self.item_at(e.position().toPoint())
        row = self.row(it) if it is not None else -1
        if row != self._hover_row:
            self._hover_row = row
            self.hoverItem.emit(self.item(row) if row >= 0 else None)

    def _begin_drag(self):
        """Kéo các tệp đang chọn (hoặc thẻ vừa nhấn) ra ngoài như kéo từ thư mục máy tính."""
        if self._press_item is not None and not self._press_item.isSelected():
            self.clearSelection()
            self._press_item.setSelected(True)
        items = [i for i in self.selectedItems() if not i.data(Qt.UserRole)["is_dir"]]
        if not items:
            return  # thư mục không kéo vào Moho được: bấm đúp để mở rồi kéo tệp bên trong
        paths = [i.data(Qt.UserRole)["path"] for i in items]
        self.dragStarted.emit()
        action, ms = start_file_drag(self, paths, items[0].icon().pixmap(112, 76))
        self.dragFinished.emit(paths, action, ms)
        self._hover_row = -1
        self.hoverItem.emit(None)

    def leaveEvent(self, e):
        super().leaveEvent(e)
        if self._hover_row != -1:
            self._hover_row = -1
            self.hoverItem.emit(None)

    def mimeData(self, items):
        md = QMimeData()
        md.setUrls([QUrl.fromLocalFile(i.data(Qt.UserRole)["path"]) for i in items])
        return md


class MainWindow(QWidget):
    def __init__(self, db: Database):
        super().__init__()
        self.db = db
        self.setObjectName("root")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setWindowTitle("Manage Moho")
        self.setStyleSheet(QSS)
        self.setAcceptDrops(True)
        self.setMinimumSize(300, 100)

        self.collapsed = False
        self.expanded_size = None
        self.cats = []
        self.cat_buttons = []
        self.cats_grid = None
        self.current_cat = None
        self.view_path = None
        self.back_stack, self.fwd_stack = [], []
        self.page = 0
        self.pages = 1
        self.entries = []
        self.last_error = None
        self.groups = groups_from_json(db.get_setting("ext_groups"))
        if db.get_setting("groups_version") != GROUPS_VERSION:
            self.groups = merge_default_groups(self.groups)
            db.set_setting("ext_groups", groups_to_json(self.groups))
            db.set_setting("groups_version", GROUPS_VERSION)
        self.script_store = ScriptStore(os.path.join(os.path.dirname(db.path), "scripts"))
        self.script_win = None
        self._tools = []
        self.hover_enabled = db.get_setting("hover_audio", "1") == "1"
        widgets.USE_NATIVE = db.get_setting("native_drag", "1") == "1"
        self.upload_mode = db.get_setting("upload_mode", "folder")
        self.page_size = max(1, int(db.get_setting("page_size", "25")))
        self.sort_mode = db.get_setting("sort", "name")
        self.grid_mode = db.get_setting("grid", "1") == "1"
        self.deep = db.get_setting("deep_search", "0") == "1"
        self.fade_on = db.get_setting("fade_on", "0") == "1"
        self.rest_opacity = int(db.get_setting("opacity", "55"))

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_toolbar())
        root.addWidget(self._build_fadebar())
        self.body = QWidget()
        bl = QVBoxLayout(self.body)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.setSpacing(0)
        bl.addWidget(self._build_cats())
        bl.addWidget(self._build_header())
        bl.addWidget(self._build_content(), 1)
        bl.addWidget(self._build_info())
        bl.addWidget(self._build_pagebar())
        bl.addWidget(self._build_bottom())
        root.addWidget(self.body, 1)
        self.preview = PreviewPanel(self)
        self.live = LiveThumbs(self.list)
        self.live.enabled = db.get_setting("live_thumbs", "1") == "1"
        self.hover_audio = HoverAudio(self)
        self.hover_timer = QTimer(self)
        self.hover_timer.setSingleShot(True)
        self.hover_timer.timeout.connect(self._hover_fire)
        self._hover_item = None
        self.list.hoverItem.connect(self.on_hover)
        self.list.dragStarted.connect(self._drag_started)
        self.list.dragFinished.connect(self.on_drag_finished)

        self.toast_label = QLabel(self)
        self.toast_label.setObjectName("toast")
        self.toast_label.setWordWrap(True)
        self.toast_label.hide()
        self.toast_timer = QTimer(self)
        self.toast_timer.setSingleShot(True)
        self.toast_timer.timeout.connect(self.toast_label.hide)
        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.on_search)
        self.restore_timer = QTimer(self)
        self.restore_timer.setSingleShot(True)
        self.restore_timer.timeout.connect(self._restore_full_opacity)

        for seq, fn in (("Alt+Left", self.go_back), ("Alt+Right", self.go_forward), ("Alt+Up", self.go_up)):
            QShortcut(QKeySequence(seq), self).activated.connect(fn)

        self._restore_geometry()
        self.update_mode_ui()
        self.rebuild_cats(select=db.get_setting("last_category"))
        self.fade_btn.setChecked(self.fade_on)
        if db.get_setting("pinned", "0") == "1":
            self.pin_btn.setChecked(True)

    # ============================================================ dựng giao diện
    def _tool(self, icon, tip, checkable=False):
        b = QToolButton()
        b.setIcon(make_icon(icon))
        b.setIconSize(QSize(16, 16))
        b.setToolTip(tip)
        b.setAccessibleName(tip)
        b.setCheckable(checkable)
        b.setFixedSize(26, 26)
        b.setCursor(Qt.PointingHandCursor)
        return b

    def _build_toolbar(self):
        w = QWidget()
        w.setObjectName("toolbar")
        h = QHBoxLayout(w)
        h.setContentsMargins(6, 4, 6, 4)
        h.setSpacing(2)
        self.reload_btn = self._tool("reload", "Đọc lại mục này (tên hiển thị về như tên tệp gốc)")
        self.reload_btn.clicked.connect(self.reload_current)
        self.moho_btn = self._tool("moho", "Về Moho: đưa cửa sổ Moho lên trước")
        self.moho_btn.clicked.connect(self.go_moho)
        self.pin_btn = self._tool("pin", "Luôn nổi trên đầu", True)
        self.pin_btn.toggled.connect(self.set_topmost)
        self.fade_btn = self._tool("eyeoff", "Làm mờ khi chuột rời cửa sổ", True)
        self.fade_btn.toggled.connect(self.set_fade)
        self.collapse_btn = self._tool("shrink", "Thu gọn / mở rộng")
        self.collapse_btn.clicked.connect(self.toggle_collapse)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Tìm kiếm tài nguyên...")
        self.search.setClearButtonEnabled(True)
        self.search.setFixedHeight(26)
        self.search.setMinimumWidth(50)
        self.search.textChanged.connect(lambda _t: self.search_timer.start(250))
        self.filter_btn = self._tool("filter", "Bộ lọc định dạng")
        self.filter_btn.clicked.connect(lambda: self.edit_filter(self.current_cat))
        self.mode_btn = self._tool("folderplus", "")
        self.mode_btn.clicked.connect(self.toggle_mode)
        self.view_btn = self._tool("grid" if self.grid_mode else "list", "Đổi kiểu xem lưới / danh sách")
        self.view_btn.clicked.connect(self.toggle_view)
        for wd in (self.reload_btn, self.moho_btn, self.pin_btn, self.fade_btn, self.collapse_btn):
            h.addWidget(wd)
        h.addWidget(self.search, 1)
        for wd in (self.filter_btn, self.mode_btn, self.view_btn):
            h.addWidget(wd)
        self.toolbar = w
        return w

    def _build_fadebar(self):
        f = QFrame()
        f.setObjectName("fadebar")
        h = QHBoxLayout(f)
        h.setContentsMargins(12, 4, 12, 4)
        lab = QLabel("Độ mờ khi chuột rời cửa sổ")
        lab.setObjectName("muted")
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setRange(20, 100)
        self.opacity_slider.setValue(self.rest_opacity)
        self.opacity_slider.valueChanged.connect(self.on_opacity_changed)
        h.addWidget(lab)
        h.addWidget(self.opacity_slider, 1)
        f.hide()
        self.fadebar = f
        return f

    def _build_cats(self):
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(6, 6, 6, 0)
        v.setSpacing(4)
        holder = QWidget()
        self.cats_grid = QGridLayout(holder)
        self.cats_grid.setContentsMargins(0, 0, 0, 0)
        self.cats_grid.setSpacing(4)
        v.addWidget(holder)
        self.add_cat_btn = QPushButton("+")
        self.add_cat_btn.setObjectName("addCat")
        self.add_cat_btn.setFixedSize(40, 20)
        self.add_cat_btn.setToolTip("Thêm mục (chuột phải: khôi phục mục mặc định)")
        self.add_cat_btn.setAccessibleName("Thêm mục")
        self.add_cat_btn.setCursor(Qt.PointingHandCursor)
        self.add_cat_btn.clicked.connect(self.add_category)
        self.add_cat_btn.setContextMenuPolicy(Qt.CustomContextMenu)
        self.add_cat_btn.customContextMenuRequested.connect(self.add_btn_menu)
        v.addWidget(self.add_cat_btn, 0, Qt.AlignHCenter)
        self.catname = QLabel("")
        self.catname.setObjectName("muted")
        self.catname.setAlignment(Qt.AlignHCenter)
        v.addWidget(self.catname)
        return w

    def _build_header(self):
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(8, 0, 8, 2)
        self.back_btn = self._tool("back", "Thoát ra thư mục cha (Alt + ←)")
        self.back_btn.clicked.connect(self.go_up)
        self.title = ElidedLabel("")
        self.more_btn = QPushButton("+ Tải thêm")
        self.more_btn.clicked.connect(self.upload)
        h.addWidget(self.back_btn)
        h.addWidget(self.title, 1)
        h.addWidget(self.more_btn)
        self.header = w
        return w

    def _build_content(self):
        self.stack = QStackedWidget()
        hero = QWidget()
        hv = QVBoxLayout(hero)
        hv.setContentsMargins(20, 10, 20, 10)
        hv.setSpacing(10)
        hv.setAlignment(Qt.AlignCenter)
        self.hero_icon = QLabel()
        self.hero_icon.setFixedSize(56, 56)
        self.hero_icon.setAlignment(Qt.AlignCenter)
        self.hero_icon.setStyleSheet(
            "background: rgba(53,195,232,0.12); border: 1px solid rgba(53,195,232,0.25); border-radius: 16px;")
        self.hero_icon.setPixmap(make_icon("folderplus", "#35c3e8", 26).pixmap(26, 26))
        self.hero_title = QLabel("")
        self.hero_title.setObjectName("heroTitle")
        self.hero_title.setAlignment(Qt.AlignHCenter)
        self.hero_title.setWordWrap(True)
        self.hero_desc = QLabel("")
        self.hero_desc.setObjectName("heroDesc")
        self.hero_desc.setAlignment(Qt.AlignHCenter)
        self.hero_desc.setWordWrap(True)
        self.hero_desc.setMaximumWidth(320)
        self.hero_btn = QPushButton("")
        self.hero_btn.setObjectName("primary")
        self.hero_btn.setCursor(Qt.PointingHandCursor)
        self.hero_btn.clicked.connect(self.upload)
        hv.addWidget(self.hero_icon, 0, Qt.AlignHCenter)
        hv.addWidget(self.hero_title)
        hv.addWidget(self.hero_desc, 0, Qt.AlignHCenter)
        hv.addWidget(self.hero_btn, 0, Qt.AlignHCenter)
        hero.setContextMenuPolicy(Qt.CustomContextMenu)
        hero.customContextMenuRequested.connect(lambda pos: self.show_empty_menu(hero.mapToGlobal(pos)))
        self.hero = hero

        page = QWidget()
        pl = QVBoxLayout(page)
        pl.setContentsMargins(8, 0, 8, 4)
        self.list = FileList()
        self.list.itemClicked.connect(self.on_item_clicked)
        self.list.itemDoubleClicked.connect(self.on_item_double)
        self.list.itemSelectionChanged.connect(self.update_info)
        self.list.customContextMenuRequested.connect(self.on_list_menu)
        self.list.set_grid_mode(self.grid_mode)
        pl.addWidget(self.list)
        self.stack.addWidget(hero)
        self.stack.addWidget(page)
        return self.stack

    def _build_info(self):
        f = QFrame()
        f.setObjectName("info")
        h = QHBoxLayout(f)
        h.setContentsMargins(8, 4, 8, 4)
        col = QVBoxLayout()
        col.setSpacing(0)
        self.info_name = ElidedLabel("")
        self.info_meta = ElidedLabel("")
        self.info_meta.setObjectName("muted")
        self.info_path = ElidedLabel("")
        self.info_path.setObjectName("muted")
        for lb in (self.info_name, self.info_meta, self.info_path):
            lb.setFixedHeight(16)
            col.addWidget(lb)
        h.addLayout(col, 1)
        self.entry_fav_btn = self._tool("heart", "Yêu thích", True)
        self.entry_fav_btn.clicked.connect(self.toggle_sel_fav)
        self.entry_pin_btn = self._tool("pin", "Ghim lên đầu", True)
        self.entry_pin_btn.clicked.connect(self.toggle_sel_pin)
        h.addWidget(self.entry_fav_btn)
        h.addWidget(self.entry_pin_btn)
        f.hide()
        self.info = f
        return f

    def _build_pagebar(self):
        self.pagebar = QWidget()
        self.page_layout = QHBoxLayout(self.pagebar)
        self.page_layout.setContentsMargins(8, 4, 8, 4)
        self.page_layout.setSpacing(2)
        self.page_layout.setAlignment(Qt.AlignHCenter)
        self.pagebar.hide()
        return self.pagebar

    def _build_bottom(self):
        w = QWidget()
        w.setObjectName("bottombar")
        h = QHBoxLayout(w)
        h.setContentsMargins(8, 6, 8, 6)
        h.setSpacing(6)
        self.manage_btn = QPushButton("Quản lý")
        self.manage_btn.setMinimumHeight(30)
        self.manage_btn.clicked.connect(self.open_manage)
        self.script_btn = QPushButton("Kịch bản")
        self.script_btn.setObjectName("gold")
        self.script_btn.setMinimumHeight(30)
        self.script_btn.clicked.connect(self.open_script)
        h.addWidget(self.manage_btn, 1)
        h.addWidget(self.script_btn, 1)
        return w

    # ============================================================ mục (hàng biểu tượng)
    def current_category(self):
        return next((c for c in self.cats if c["id"] == self.current_cat), None)

    def rebuild_cats(self, select=None):
        for b in self.cat_buttons:
            b.deleteLater()
        self.cat_buttons = []
        self.cats = self.db.categories()
        ids = [c["id"] for c in self.cats]
        try:
            select = int(select) if select is not None else None
        except (TypeError, ValueError):
            select = None
        if select not in ids:
            select = ids[0] if ids else None
        for c in self.cats:
            b = QToolButton()
            b.setObjectName("catBtn")
            b.setCheckable(True)
            b.setFixedSize(30, 30)
            b.setIconSize(QSize(17, 17))
            b.setIcon(category_icon(c, 17))
            b.setToolTip(c["name"])
            b.setAccessibleName(c["name"])
            b.setCursor(Qt.PointingHandCursor)
            b.setProperty("cid", c["id"])
            b.setContextMenuPolicy(Qt.CustomContextMenu)
            b.customContextMenuRequested.connect(lambda _p, cid=c["id"], btn=b: self.cat_menu(cid, btn))
            b.clicked.connect(lambda _=False, cid=c["id"]: self.select_category(cid))
            self.cat_buttons.append(b)
        self.relayout_cats()
        self.select_category(select, remember=False)

    def relayout_cats(self):
        if self.cats_grid is None:
            return
        while self.cats_grid.count():
            self.cats_grid.takeAt(0)
        for c in range(64):
            self.cats_grid.setColumnStretch(c, 0)
        cols = max(1, min(60, (self.width() - 12 + 4) // 34))
        for i, b in enumerate(self.cat_buttons):
            self.cats_grid.addWidget(b, i // cols, i % cols + 1)
        self.cats_grid.setColumnStretch(0, 1)
        self.cats_grid.setColumnStretch(cols + 1, 1)

    def select_category(self, cid, remember=True):
        self.current_cat = cid
        self.reset_nav()
        for b in self.cat_buttons:
            b.setChecked(b.property("cid") == cid)
        if remember and cid is not None:
            self.db.set_setting("last_category", cid)
        self.refresh()

    def cat_menu(self, cid, btn):
        m = QMenu(self)
        act(m, "Sửa tên và biểu tượng...", lambda: self.edit_category(cid))
        act(m, "Bộ lọc định dạng của mục...", lambda: self.edit_filter(cid))
        m.addSeparator()
        act(m, "Dời sang trái", lambda: self.move_category(cid, -1))
        act(m, "Dời sang phải", lambda: self.move_category(cid, 1))
        m.addSeparator()
        act(m, "Xóa mục", lambda: self.delete_category(cid))
        m.exec(btn.mapToGlobal(btn.rect().bottomLeft()))

    def add_btn_menu(self, pos):
        m = QMenu(self)
        act(m, "Thêm mục...", self.add_category)
        act(m, "Khôi phục mục mặc định", self.restore_default_cats)
        m.exec(self.add_cat_btn.mapToGlobal(pos))

    def _icons_dir(self):
        folder = os.path.join(os.path.dirname(self.db.path), "icons")
        os.makedirs(folder, exist_ok=True)
        return folder

    def _keep_icon_image(self, src):
        """Sao chép ảnh biểu tượng vào thư mục dữ liệu của phần mềm (không đụng ảnh gốc)."""
        if not src:
            return None
        folder = self._icons_dir()
        if os.path.dirname(os.path.abspath(src)) == os.path.abspath(folder):
            return src
        ext = os.path.splitext(src)[1]
        dest = os.path.join(folder, f"{int(time.time() * 1000)}{ext}")
        shutil.copy2(src, dest)
        return dest

    def add_category(self):
        dlg = CategoryDialog(self, "Thêm mục")
        if not dlg.exec():
            return
        v = dlg.values()
        try:
            cid = self.db.add_category(v["name"], v["icon"], v["color"], self._keep_icon_image(v["image"]))
        except ValueError as e:
            QMessageBox.warning(self, "Không thêm được", str(e))
            return
        self.rebuild_cats(select=cid)

    def edit_category(self, cid):
        c = self.db.category(cid)
        if not c:
            return
        dlg = CategoryDialog(self, "Sửa mục", c["name"], c["icon"], c["color"], c["icon_image"])
        if not dlg.exec():
            return
        v = dlg.values()
        try:
            self.db.update_category(cid, name=v["name"], icon=v["icon"], color=v["color"],
                                    icon_image=self._keep_icon_image(v["image"]))
        except ValueError as e:
            QMessageBox.warning(self, "Không sửa được", str(e))
            return
        self.rebuild_cats(select=self.current_cat)

    def move_category(self, cid, delta):
        self.db.move_category(cid, delta)
        self.rebuild_cats(select=self.current_cat)

    def delete_category(self, cid):
        c = self.db.category(cid)
        if not c:
            return
        r = QMessageBox.question(
            self, "Xóa mục",
            f"Xóa mục “{c['name']}”?\nChỉ xóa danh sách trong phần mềm, tệp và thư mục thật trên máy KHÔNG bị xóa.")
        if r != QMessageBox.Yes:
            return
        self.db.delete_category(cid)
        self.rebuild_cats(select=None if cid == self.current_cat else self.current_cat)

    def restore_default_cats(self):
        n = self.db.restore_defaults()
        self.rebuild_cats(select=self.current_cat)
        self.toast(f"Đã khôi phục {n} mục mặc định" if n else "Không có mục mặc định nào bị thiếu")

    def edit_filter(self, cid):
        c = self.db.category(cid) if cid is not None else None
        if not c:
            self.toast("Hãy chọn một mục trước")
            return
        active = [k for k in c["filters"].split(",") if k]
        dlg = FilterDialog(self, self.groups, active)
        if not dlg.exec():
            return
        groups, keys = dlg.values()
        self.groups = groups
        self.db.set_setting("ext_groups", groups_to_json(groups))
        self.db.update_category(cid, filters=",".join(keys))
        self.rebuild_cats(select=self.current_cat)

    # ============================================================ điều hướng thư mục
    def reset_nav(self):
        self.view_path = None
        self.back_stack, self.fwd_stack = [], []
        self.page = 0

    def navigate(self, path):
        if self.view_path is not None and pkey(path) == pkey(self.view_path):
            return
        self.back_stack.append(self.view_path)
        self.fwd_stack = []
        self.view_path = os.path.normpath(path)
        self.page = 0
        self.refresh()

    def go_back(self):
        if not self.back_stack:
            return
        self.fwd_stack.append(self.view_path)
        self.view_path = self.back_stack.pop()
        self.page = 0
        self.refresh()

    def go_forward(self):
        if not self.fwd_stack:
            return
        self.back_stack.append(self.view_path)
        self.view_path = self.fwd_stack.pop()
        self.page = 0
        self.refresh()

    def go_up(self):
        if self.view_path is None:
            return
        cat = self.current_category()
        roots = self.view_roots(cat) if cat else []
        if any(pkey(r) == pkey(self.view_path) for r in roots):
            target = None
        else:
            target = os.path.dirname(self.view_path)
        self.back_stack.append(self.view_path)
        self.fwd_stack = []
        self.view_path = target
        self.page = 0
        self.refresh()

    def view_roots(self, cat):
        if cat["kind"] == "fav":
            return self.db.favorites()
        if cat["kind"] == "all":
            return [r["path"] for r in self.db.all_roots()]
        return [r["path"] for r in self.db.roots(cat["id"])]

    def active_exts(self, cat):
        return exts_for(self.groups, [k for k in cat["filters"].split(",") if k])

    # ============================================================ nạp và hiển thị danh sách
    def reload_entries(self):
        cat = self.current_category()
        self.last_error = None
        if cat is None:
            self.entries = []
            return
        exts = self.active_exts(cat)
        q = self.search.text().strip().lower()
        if self.view_path is None:
            starts = self.view_roots(cat)
            base = [e for e in (make_entry(p) for p in starts) if e]
        else:
            starts = [self.view_path]
            try:
                base = list_dir(self.view_path, exts)
            except OSError as ex:
                self.entries = []
                self.last_error = str(ex)
                return
        if q and self.deep:
            base, _cut = deep_search(starts, q, exts)
        meta = self.db.meta_map([e["path"] for e in base])
        for e in base:
            m = meta.get(pkey(e["path"]))
            e["label"] = (m and m["display_name"]) or e["name"]
            e["fav"] = bool(m and m["favorite"])
            e["pinned"] = bool(m and m["pinned"])
        if q:
            base = [e for e in base if q in e["label"].lower() or q in e["name"].lower()]
        self.entries = sort_items(base, self.sort_mode)

    def refresh(self, *_args, keep=None):
        self.reload_entries()
        self.render_page()
        self.update_chrome()
        if keep:
            self.select_paths(keep)

    def render_page(self):
        part, self.page, self.pages = page_slice(self.entries, self.page, self.page_size)
        self.live.stop_all()
        self.hover_audio.stop()
        self.list.clear()
        for e in part:
            it = QListWidgetItem(e["label"])
            it.setIcon(QIcon(compose(e, e["fav"], e["pinned"])))
            it.setData(Qt.UserRole, e)
            it.setToolTip(e["path"])
            self.list.addItem(it)
        self.live.start(list(enumerate(part)))
        self.update_pagebar()
        self.update_info()

    def update_chrome(self):
        cat = self.current_category()
        self.catname.setText(cat["name"] if cat else "")
        has = bool(self.entries)
        inside = self.view_path is not None
        n = len(self.entries)
        self.back_btn.setVisible(inside)
        self.more_btn.setVisible((not inside) and has and cat is not None and cat["kind"] != "fav")
        self.header.setVisible(inside or has)
        if inside:
            roots = self.view_roots(cat) if cat else []
            root = root_of(self.view_path, roots)
            text = " › ".join(nm for nm, _p in breadcrumb(self.view_path, root)) if root else os.path.basename(self.view_path)
            self.title.setFullText(f"{text}  ·  {n} mục")
        else:
            self.title.setFullText(f"{cat['name']}  ·  {n} mục" if cat else "")
        if has:
            self.stack.setCurrentIndex(1)
            return
        self.stack.setCurrentIndex(0)
        show_btn = False
        if cat is None:
            title, desc = "Chưa có mục nào", "Bấm dấu + ở trên để thêm mục."
        elif self.last_error:
            title, desc = "Không mở được thư mục", self.last_error
        elif inside:
            if self.search.text().strip():
                title, desc = "Không tìm thấy kết quả", "Thử từ khóa khác hoặc bật tìm cả trong thư mục con (chuột phải)."
            else:
                title, desc = "Thư mục trống", "Không có tệp phù hợp bộ lọc. Bấm biểu tượng bộ lọc để đổi loại tệp hiển thị."
        elif cat["kind"] == "fav":
            title, desc = "Chưa có tệp yêu thích", "Chuột phải vào tệp hoặc thư mục rồi chọn Yêu thích."
        else:
            title = "Chưa có tệp nào trong mục này"
            desc = "Kéo thả hoặc chọn thư mục/tệp từ máy tính. Phần mềm chỉ lưu liên kết, không sao chép hay xóa tệp gốc."
            show_btn = True
        self.hero_title.setText(title)
        self.hero_desc.setText(desc)
        self.hero_btn.setVisible(show_btn)

    def update_pagebar(self):
        while self.page_layout.count():
            w = self.page_layout.takeAt(0).widget()
            if w:
                w.deleteLater()
        if self.pages <= 1:
            self.pagebar.hide()
            return
        self.pagebar.show()
        self._page_btn("‹", self.page - 1, self.page > 0)
        for b in page_buttons(self.page, self.pages):
            if b == "…":
                lb = QLabel("…")
                lb.setObjectName("muted")
                self.page_layout.addWidget(lb)
            else:
                self._page_btn(str(b), b - 1, True, b - 1 == self.page)
        self._page_btn("Tiếp ›", self.page + 1, self.page < self.pages - 1)

    def _page_btn(self, text, target, enabled=True, current=False):
        b = QPushButton(text)
        b.setProperty("page", True)
        b.setProperty("current", current)
        b.setEnabled(enabled)
        b.setCursor(Qt.PointingHandCursor)
        b.clicked.connect(lambda _=False, t=target: self.set_page(t))
        self.page_layout.addWidget(b)

    def set_page(self, n):
        self.page = n
        self.render_page()

    def on_search(self):
        self.page = 0
        self.refresh()

    # ============================================================ chọn tệp / thông tin
    def selected_entries(self):
        return [i.data(Qt.UserRole) for i in self.list.selectedItems()]

    def select_paths(self, paths):
        keys = {pkey(p) for p in paths}
        for i in range(self.list.count()):
            it = self.list.item(i)
            if pkey(it.data(Qt.UserRole)["path"]) in keys:
                it.setSelected(True)

    def update_info(self):
        sel = self.selected_entries()
        if not sel:
            self.info.hide()
            return
        self.info.show()
        if len(sel) == 1:
            e = sel[0]
            name = e["label"] + (f"  (gốc: {e['name']})" if e["label"] != e["name"] else "")
            date = time.strftime("%d/%m/%Y %H:%M", time.localtime(e["mtime"])) if e["mtime"] else "—"
            kind = "Thư mục" if e["is_dir"] else f"{(e['ext'][1:].upper() or 'Tệp')} · {human_size(e['size'])}"
            self.info_name.setFullText(name)
            self.info_meta.setFullText(f"{kind} · sửa đổi (hệ thống) {date}")
            self.info_path.setFullText(e["path"])
        else:
            self.info_name.setFullText(f"{len(sel)} mục đã chọn")
            self.info_meta.setFullText("")
            self.info_path.setFullText("")
        self.entry_fav_btn.setChecked(all(e["fav"] for e in sel))
        self.entry_pin_btn.setChecked(all(e["pinned"] for e in sel))

    def toggle_sel_fav(self):
        sel = self.selected_entries()
        if sel:
            self.set_fav(sel, not all(e["fav"] for e in sel))

    def toggle_sel_pin(self):
        sel = self.selected_entries()
        if sel:
            self.set_pin(sel, not all(e["pinned"] for e in sel))

    def set_fav(self, entries, on):
        for e in entries:
            self.db.set_favorite(e["path"], on)
        self.refresh(keep=[e["path"] for e in entries])

    def set_pin(self, entries, on):
        for e in entries:
            self.db.set_pinned(e["path"], on)
        self.refresh(keep=[e["path"] for e in entries])

    def rename_entry(self, e):
        name, ok = QInputDialog.getText(
            self, "Đổi tên hiển thị", "Tên hiển thị (để trống = tên tệp gốc).\nTệp thật trên máy không bị đổi tên:",
            text=e["label"])
        if ok:
            self.db.set_display_name(e["path"], name)
            self.refresh(keep=[e["path"]])

    def reset_entry_name(self, e):
        self.db.set_display_name(e["path"], None)
        self.refresh(keep=[e["path"]])

    # ============================================================ thao tác chuột
    def on_item_clicked(self, item):
        e = item.data(Qt.UserRole)
        mods = QApplication.keyboardModifiers()
        if e["is_dir"] and not (mods & (Qt.ControlModifier | Qt.ShiftModifier)):
            QTimer.singleShot(0, lambda p=e["path"]: self.navigate(p))

    def on_item_double(self, item):
        e = item.data(Qt.UserRole)
        if not e["is_dir"]:
            self.preview.open_entry(e)

    def audio_hover_path(self, item):
        """Đường dẫn âm thanh cần phát khi rê chuột vào thẻ, hoặc None."""
        if item is None or not self.hover_enabled:
            return None
        e = item.data(Qt.UserRole)
        return e["path"] if (e and not e["is_dir"] and e["ext"] in AUDIO_EXTS) else None

    def on_hover(self, item):
        self._hover_item = item
        if item is None:
            self.hover_timer.stop()
            self.hover_audio.stop()
        else:
            self.hover_timer.start(160)

    def _hover_fire(self):
        path = self.audio_hover_path(self._hover_item)
        if path:
            self.hover_audio.play(path)
        else:
            self.hover_audio.stop()

    def _drag_started(self):
        self.hover_timer.stop()
        self.hover_audio.stop()

    def on_drag_finished(self, paths, action, ms):
        info = dict(native_drag.last_info)
        front = drag_log.after_drag(os.path.dirname(self.db.path), paths, action, ms, self.pin_btn.isChecked(), info)
        name = os.path.basename(paths[0]) + (f" và {len(paths) - 1} tệp khác" if len(paths) > 1 else "")
        target = info.get("tha_vao", "")
        ext = os.path.splitext(paths[0])[1].lower() or "này"
        if action == "Ignore":
            if info.get("huy"):
                self.toast("Đã hủy kéo.")
            elif target and not moho_bridge.is_moho_exe(target):
                self.toast(f"Bạn đang thả vào “{target}”, không phải Moho. Hãy thả vào cửa sổ Moho.", 4500)
            elif target:
                self.toast(f"Moho đã từ chối tệp {ext}. Thử thả vào vùng làm việc hoặc thử tệp PNG/WAV. "
                           "Gửi keo.log cho mình nếu tệp PNG cũng không được.", 6000)
            else:
                self.toast("Chưa có ứng dụng nào nhận tệp. Hãy thả vào cửa sổ Moho.", 4500)
        else:
            self.toast(f"Đã thả vào Moho: {name}" if front else f"Đã thả: {name}")

    def open_path(self, path):
        QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def copy_paths(self, paths):
        QGuiApplication.clipboard().setText("\n".join(paths))
        self.toast("Đã sao chép đường dẫn")

    def on_list_menu(self, pos):
        it = self.list.itemAt(pos)
        gpos = self.list.viewport().mapToGlobal(pos)
        if it is None:
            self.list.clearSelection()
            self.show_empty_menu(gpos)
            return
        if not it.isSelected():
            self.list.clearSelection()
            it.setSelected(True)
        sel = self.selected_entries()
        m = QMenu(self)
        if len(sel) == 1:
            self.fill_single_menu(m, sel[0])
        else:
            self.fill_multi_menu(m, sel)
        m.exec(gpos)

    def fill_single_menu(self, m, e):
        path = e["path"]
        if e["is_dir"]:
            act(m, "Mở", lambda: self.navigate(path))
            act(m, "Mở trong File Explorer", lambda: self.open_path(path))
        else:
            act(m, "Xem trước / thông tin", lambda: self.preview.open_entry(e))
            act(m, "Mở bằng ứng dụng mặc định", lambda: self.open_path(path))
            if e["ext"] in AUDIO_EXTS:
                act(m, "Cắt âm thanh...", lambda: self.open_audio_slice(path))
            act(m, "Mở thư mục chứa tệp", lambda: self.open_path(os.path.dirname(path)))
        m.addSeparator()
        act(m, "Bỏ yêu thích" if e["fav"] else "Yêu thích", lambda: self.set_fav([e], not e["fav"]))
        act(m, "Bỏ ghim" if e["pinned"] else "Ghim lên đầu", lambda: self.set_pin([e], not e["pinned"]))
        act(m, "Đổi tên hiển thị...", lambda: self.rename_entry(e))
        act(m, "Đặt lại tên hiển thị", lambda: self.reset_entry_name(e), e["label"] != e["name"])
        m.addSeparator()
        self.add_to_category_menu(m, [e])
        act(m, "Sao chép đường dẫn", lambda: self.copy_paths([path]))
        act(m, "Thông tin chi tiết", lambda: self.preview.open_entry(e))
        if self.can_remove([e]):
            m.addSeparator()
            act(m, "Bỏ khỏi mục (không xóa tệp thật)", lambda: self.remove_entries([e]))

    def fill_multi_menu(self, m, sel):
        files = [e["path"] for e in sel if not e["is_dir"]]
        allfav = all(e["fav"] for e in sel)
        allpin = all(e["pinned"] for e in sel)
        act(m, "Bỏ yêu thích tất cả" if allfav else "Yêu thích tất cả", lambda: self.set_fav(sel, not allfav))
        act(m, "Bỏ ghim tất cả" if allpin else "Ghim tất cả", lambda: self.set_pin(sel, not allpin))
        self.add_to_category_menu(m, sel)
        act(m, "Sao chép danh sách đường dẫn", lambda: self.copy_paths([e["path"] for e in sel]))
        if self.can_remove(sel):
            m.addSeparator()
            act(m, "Bỏ khỏi mục (không xóa tệp thật)", lambda: self.remove_entries(sel))

    def add_to_category_menu(self, m, entries):
        sub = m.addMenu("Thêm vào mục")
        targets = [c for c in self.cats if c["kind"] == "normal" and c["id"] != self.current_cat]
        if not targets:
            sub.setEnabled(False)
        for c in targets:
            act(sub, c["name"], lambda cid=c["id"]: self.add_entries_to(cid, entries))

    def add_entries_to(self, cid, entries):
        n = self.db.add_roots(cid, [e["path"] for e in entries])
        name = (self.db.category(cid) or {}).get("name", "")
        self.toast(f"Đã thêm {n} mục vào “{name}”" if n else f"Đã có sẵn trong “{name}”")

    def can_remove(self, entries):
        cat = self.current_category()
        return cat is not None and cat["kind"] in ("normal", "all") and self.view_path is None

    def remove_entries(self, entries):
        cat = self.current_category()
        for e in entries:
            if cat["kind"] == "all":
                self.db.remove_root_everywhere(e["path"])
            else:
                self.db.remove_root_path(cat["id"], e["path"])
        self.refresh()

    def show_empty_menu(self, gpos):
        cat = self.current_category()
        can_up = cat is not None and cat["kind"] != "fav"
        m = QMenu(self)
        act(m, "Quay lại", self.go_back, bool(self.back_stack))
        act(m, "Tiến tới", self.go_forward, bool(self.fwd_stack))
        act(m, "Lên thư mục cha", self.go_up, self.view_path is not None)
        m.addSeparator()
        act(m, "Đọc lại (tên hiển thị về như cũ)", self.reload_current, cat is not None)
        act(m, "Tải thư mục lên...", self.upload_folder, can_up)
        act(m, "Tải tệp lên...", self.upload_files, can_up)
        m.addSeparator()
        act(m, "Bộ lọc định dạng...", lambda: self.edit_filter(self.current_cat), cat is not None)
        act(m, "Chuyển lưới / danh sách", self.toggle_view)
        sm = m.addMenu("Sắp xếp theo")
        for key, label in (("name", "Tên"), ("date", "Ngày sửa đổi"), ("size", "Dung lượng"), ("type", "Loại tệp")):
            a = sm.addAction(label)
            a.setCheckable(True)
            a.setChecked(self.sort_mode == key)
            a.triggered.connect(lambda _c=False, k=key: self.set_sort(k))
        act(m, f"Số mục mỗi trang... ({self.page_size})", self.ask_page_size)
        a = m.addAction("Tìm cả trong thư mục con")
        a.setCheckable(True)
        a.setChecked(self.deep)
        a.triggered.connect(lambda _c=False: self.set_deep(not self.deep))
        m.exec(gpos)

    def set_sort(self, key):
        self.sort_mode = key
        self.db.set_setting("sort", key)
        self.refresh()

    def set_deep(self, on):
        self.deep = on
        self.db.set_setting("deep_search", "1" if on else "0")
        self.refresh()

    def ask_page_size(self):
        n, ok = QInputDialog.getInt(self, "Số mục mỗi trang", "Số mục hiển thị mỗi trang:", self.page_size, 1, 200)
        if ok:
            self.page_size = n
            self.db.set_setting("page_size", n)
            self.page = 0
            self.refresh()

    def toggle_view(self):
        self.grid_mode = not self.grid_mode
        self.db.set_setting("grid", "1" if self.grid_mode else "0")
        self.view_btn.setIcon(make_icon("grid" if self.grid_mode else "list"))
        self.list.set_grid_mode(self.grid_mode)

    # ============================================================ tải thư mục / tệp lên
    def upload_label(self):
        return "Tải thư mục lên" if self.upload_mode == "folder" else "Tải tệp lên"

    def update_mode_ui(self):
        folder = self.upload_mode == "folder"
        self.mode_btn.setIcon(make_icon("folderplus" if folder else "fileplus"))
        tip = ("Chế độ tải: THƯ MỤC (bấm để chuyển sang tải tệp)" if folder
               else "Chế độ tải: TỆP (bấm để chuyển sang tải thư mục)")
        self.mode_btn.setToolTip(tip)
        self.mode_btn.setAccessibleName(tip)
        self.hero_btn.setText(self.upload_label())
        self.hero_icon.setPixmap(make_icon("folderplus" if folder else "fileplus", "#35c3e8", 26).pixmap(26, 26))

    def toggle_mode(self):
        self.upload_mode = "file" if self.upload_mode == "folder" else "folder"
        self.db.set_setting("upload_mode", self.upload_mode)
        self.update_mode_ui()
        self.toast("Chế độ tải: " + ("thư mục" if self.upload_mode == "folder" else "tệp"))

    def can_upload(self):
        cat = self.current_category()
        if cat is None:
            self.toast("Hãy thêm một mục trước (dấu +)")
            return False
        if cat["kind"] == "fav":
            self.toast("Không tải trực tiếp vào Yêu thích, hãy chọn mục khác")
            return False
        return True

    def upload(self):
        if self.upload_mode == "folder":
            self.upload_folder()
        else:
            self.upload_files()

    def upload_folder(self):
        if not self.can_upload():
            return
        d = QFileDialog.getExistingDirectory(self, "Chọn thư mục để tải lên")
        if d:
            self.add_roots([d])

    def upload_files(self):
        if not self.can_upload():
            return
        files, _f = QFileDialog.getOpenFileNames(self, "Chọn tệp để tải lên")
        if files:
            self.add_roots(files)

    def add_roots(self, paths):
        if not self.can_upload():
            return 0
        cat = self.current_category()
        n = self.db.add_roots(cat["id"], paths)
        self.reset_nav()
        self.refresh()
        self.toast(f"Đã thêm {n} mục" if n else "Không có mục mới để thêm")
        return n

    def reload_current(self):
        cat = self.current_category()
        if cat is None:
            return
        paths = self.view_roots(cat)
        cleared = self.db.reset_names(paths)
        removed = 0
        if cat["kind"] == "all":
            removed = self.db.prune_missing_roots()
        elif cat["kind"] == "normal":
            removed = self.db.prune_missing_roots(cat["id"])
        if self.view_path is not None and not os.path.isdir(self.view_path):
            self.reset_nav()
        self.refresh()
        msg = "Đã đọc lại"
        if cleared:
            msg += f" · {cleared} tên về như cũ"
        if removed:
            msg += f" · bỏ {removed} mục không còn trên máy"
        self.toast(msg)

    def dragEnterEvent(self, e):
        if e.source() is None and e.mimeData().hasUrls():
            e.acceptProposedAction()
        else:
            e.ignore()

    def dropEvent(self, e):
        if e.source() is not None:
            return
        paths = [u.toLocalFile() for u in e.mimeData().urls() if u.isLocalFile()]
        if paths:
            self.add_roots(paths)
            e.acceptProposedAction()

    # ============================================================ Moho
    def go_moho(self):
        ok = moho_bridge.bring_moho_to_front()
        self.toast("Đã đưa Moho lên trước" if ok else "Chưa thấy Moho đang chạy")

    # ============================================================ luôn nổi, mờ, thu gọn
    def set_topmost(self, on):
        self.db.set_setting("pinned", "1" if on else "0")
        geo = self.geometry()
        visible = self.isVisible()
        self.setWindowFlag(Qt.WindowStaysOnTopHint, bool(on))
        if visible:
            self.show()
            self.setGeometry(geo)

    def set_fade(self, on):
        self.fade_on = bool(on)
        self.db.set_setting("fade_on", "1" if on else "0")
        self.fadebar.setVisible(bool(on))
        if not on:
            self.setWindowOpacity(1.0)

    def on_opacity_changed(self, v):
        self.rest_opacity = v
        self.db.set_setting("opacity", v)
        if self.fade_on:
            self.setWindowOpacity(v / 100.0)
            self.restore_timer.start(900)

    def _restore_full_opacity(self):
        if self.underMouse():
            self.setWindowOpacity(1.0)

    def enterEvent(self, e):
        self.setWindowOpacity(1.0)
        super().enterEvent(e)

    def leaveEvent(self, e):
        if self.fade_on:
            self.setWindowOpacity(self.rest_opacity / 100.0)
        super().leaveEvent(e)

    def toggle_collapse(self):
        if not self.collapsed:
            self.expanded_size = self.size()
            self.live.stop_all()
            self.hover_audio.stop()
            self.body.hide()
            self.collapse_btn.setIcon(make_icon("expand"))
            self.collapsed = True
            self.resize(self.width(), 10)
        else:
            self.body.show()
            self.collapse_btn.setIcon(make_icon("shrink"))
            self.collapsed = False
            if self.expanded_size:
                self.resize(self.expanded_size)
            self.render_page()

    # ============================================================ Quản lý / Kịch bản / Cắt âm thanh
    def open_manage(self):
        ManageDialog(self).exec()
        self.apply_settings()

    def open_script(self):
        if self.script_win is None:
            self.script_win = ScriptWindow(self.db, self.script_store, None)
        self.script_win.show()
        self.script_win.raise_()
        self.script_win.activateWindow()

    def refresh_script_window(self):
        if self.script_win is not None:
            self.script_win.refresh_list()
            self.script_win.ai.refresh()

    def open_audio_slice(self, path):
        w = AudioSliceWindow(self.db, path, None)
        self._tools.append(w)
        w.show()
        w.raise_()

    def apply_settings(self):
        """Đọc lại cài đặt từ cơ sở dữ liệu (sau khi sửa trong Quản lý hoặc khôi phục sao lưu)."""
        db = self.db
        self.page_size = max(1, int(db.get_setting("page_size", "25")))
        self.sort_mode = db.get_setting("sort", "name")
        self.deep = db.get_setting("deep_search", "0") == "1"
        self.upload_mode = db.get_setting("upload_mode", "folder")
        self.groups = groups_from_json(db.get_setting("ext_groups"))
        self.hover_enabled = db.get_setting("hover_audio", "1") == "1"
        widgets.USE_NATIVE = db.get_setting("native_drag", "1") == "1"
        self.live.enabled = db.get_setting("live_thumbs", "1") == "1"
        self.page = 0
        self.update_mode_ui()
        self.rebuild_cats(select=self.current_cat)

    # ============================================================ thông báo nhỏ, kích thước, lưu vị trí
    def toast(self, text, ms=2400):
        lb = self.toast_label
        lb.setText(text)
        lb.setFixedWidth(max(80, min(lb.sizeHint().width() + 4, self.width() - 24)))
        lb.adjustSize()
        self.place_toast()
        lb.show()
        lb.raise_()
        self.toast_timer.start(ms)

    def place_toast(self):
        lb = self.toast_label
        lb.move(max(0, (self.width() - lb.width()) // 2), max(0, self.height() - lb.height() - 70))

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.relayout_cats()
        self.place_toast()
        if hasattr(self, "preview"):
            self.preview.reposition()

    def mousePressEvent(self, e):
        if e.button() == Qt.BackButton:
            self.go_back()
            return
        if e.button() == Qt.ForwardButton:
            self.go_forward()
            return
        super().mousePressEvent(e)

    def _restore_geometry(self):
        g = self.db.get_setting("geometry2")
        try:
            x, y, w, h = [int(v) for v in g.split(",")]
            self.setGeometry(x, y, max(w, 300), max(h, 300))
        except Exception:
            self.resize(340, 580)

    def closeEvent(self, e):
        self.preview.hard_close()
        self.live.stop_all()
        self.hover_audio.stop()
        size = self.expanded_size if self.collapsed and self.expanded_size else self.size()
        pos = self.pos()
        self.db.set_setting("geometry2", f"{pos.x()},{pos.y()},{size.width()},{size.height()}")
        super().closeEvent(e)

