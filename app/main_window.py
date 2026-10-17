import os

from PySide6.QtCore import QMimeData, QSize, Qt, QTimer, QUrl
from PySide6.QtGui import QColor, QDesktopServices, QFont, QGuiApplication, QPainter, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView, QApplication, QButtonGroup, QFileDialog, QHBoxLayout, QInputDialog,
    QLabel, QLineEdit, QListView, QListWidget, QListWidgetItem, QMenu, QMessageBox,
    QPushButton, QScrollArea, QSlider, QStackedWidget, QToolButton, QVBoxLayout, QWidget,
)

from .db import Database
from .icons import make_icon
from .theme import QSS

IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"}
TYPE_COLORS = {
    "audio": ("#5b6bd6", {".wav", ".mp3", ".ogg", ".flac"}),
    "video": ("#c2587a", {".mp4", ".mov", ".avi", ".mkv"}),
    "3d": ("#7a6bd6", {".obj", ".fbx", ".glb", ".gltf"}),
    "moho": ("#d98a3d", {".moho"}),
}


def file_icon(path, size=QSize(88, 66)):
    ext = os.path.splitext(path)[1].lower()
    if ext in IMAGE_EXT and os.path.exists(path):
        pm = QPixmap(path)
        if not pm.isNull():
            return pm.scaled(size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    color = "#4a5560"
    for c, exts in TYPE_COLORS.values():
        if ext in exts:
            color = c
    pm = QPixmap(size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setBrush(QColor(color))
    p.setPen(Qt.NoPen)
    p.drawRoundedRect(0, 0, size.width(), size.height(), 10, 10)
    p.setPen(QColor("white"))
    f = QFont("Segoe UI", 12)
    f.setBold(True)
    p.setFont(f)
    p.drawText(pm.rect(), Qt.AlignCenter, (ext[1:] or "?").upper()[:5])
    p.end()
    return pm


class FileList(QListWidget):
    """Lưới thẻ tệp. Kéo thẻ ra ngoài sẽ mang theo đường dẫn tệp thật (để kéo sang Moho)."""

    def __init__(self):
        super().__init__()
        self.setViewMode(QListView.IconMode)
        self.setResizeMode(QListView.Adjust)
        self.setMovement(QListView.Static)
        self.setWordWrap(True)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setDragEnabled(True)
        self.setDragDropMode(QAbstractItemView.DragOnly)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.set_grid_mode(True)

    def set_grid_mode(self, grid):
        if grid:
            self.setViewMode(QListView.IconMode)
            self.setIconSize(QSize(88, 66))
            self.setGridSize(QSize(108, 112))
        else:
            self.setViewMode(QListView.ListMode)
            self.setIconSize(QSize(44, 33))
            self.setGridSize(QSize())
        self.setResizeMode(QListView.Adjust)
        self.setMovement(QListView.Static)

    def mimeData(self, items):
        md = QMimeData()
        md.setUrls([QUrl.fromLocalFile(i.data(Qt.UserRole)) for i in items])
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
        self.collapsed = False
        self.expanded_size = None
        self.current_cat = None
        self.grid_mode = self.db.get_setting("grid", "1") == "1"
        self.rest_opacity = int(self.db.get_setting("opacity", "85"))

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_toolbar())
        self.tabs_area = self._build_tabs()
        root.addWidget(self.tabs_area)
        self.content = self._build_content()
        root.addWidget(self.content, 1)
        self.bottom = self._build_bottom()
        root.addWidget(self.bottom)

        self._restore_geometry()
        self.restore_timer = QTimer(self)
        self.restore_timer.setSingleShot(True)
        self.restore_timer.timeout.connect(self._restore_full_opacity)
        self.info_timer = QTimer(self)
        self.info_timer.setSingleShot(True)
        self.info_timer.timeout.connect(self._update_header)

        self.rebuild_tabs(select=self.db.get_setting("last_category"))
        if self.db.get_setting("pinned", "0") == "1":
            self.pin_btn.setChecked(True)

    # ------------------------------------------------------------ dựng giao diện
    def _tool(self, icon, tip, checkable=False):
        b = QToolButton()
        b.setIcon(make_icon(icon))
        b.setIconSize(QSize(18, 18))
        b.setToolTip(tip)
        b.setAccessibleName(tip)
        b.setCheckable(checkable)
        b.setFixedSize(32, 32)
        b.setCursor(Qt.PointingHandCursor)
        return b

    def _build_toolbar(self):
        w = QWidget()
        w.setObjectName("toolbar")
        h = QHBoxLayout(w)
        h.setContentsMargins(8, 6, 8, 6)
        h.setSpacing(6)
        self.pin_btn = self._tool("pin", "Luôn nổi trên đầu", True)
        self.pin_btn.toggled.connect(self.set_pinned)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Tìm kiếm...")
        self.search.setClearButtonEnabled(True)
        self.search.setFixedHeight(32)
        self.search.textChanged.connect(self.refresh_items)
        self.reload_btn = self._tool("reload", "Đọc lại mục này")
        self.reload_btn.clicked.connect(self.reload_current)
        self.view_btn = self._tool("grid" if self.grid_mode else "list", "Đổi kiểu xem lưới/danh sách")
        self.view_btn.clicked.connect(self.toggle_view)
        self.opacity_icon = QLabel()
        self.opacity_icon.setPixmap(make_icon("opacity", "#9a9da6").pixmap(18, 18))
        self.opacity_icon.setToolTip("Độ mờ khi chuột rời cửa sổ")
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setRange(20, 100)
        self.opacity_slider.setValue(self.rest_opacity)
        self.opacity_slider.setFixedWidth(58)
        self.opacity_slider.setToolTip("Độ mờ khi chuột rời cửa sổ")
        self.opacity_slider.valueChanged.connect(self.on_opacity_changed)
        self.collapse_btn = self._tool("minus", "Thu gọn / mở rộng")
        self.collapse_btn.clicked.connect(self.toggle_collapse)
        for wd in (self.pin_btn,):
            h.addWidget(wd)
        h.addWidget(self.search, 1)
        for wd in (self.reload_btn, self.view_btn, self.opacity_icon, self.opacity_slider, self.collapse_btn):
            h.addWidget(wd)
        self.toolbar = w
        return w

    def _build_tabs(self):
        area = QScrollArea()
        area.setWidgetResizable(True)
        area.setFixedHeight(52)
        area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        holder = QWidget()
        holder.setObjectName("tabs")
        self.tabs_layout = QHBoxLayout(holder)
        self.tabs_layout.setContentsMargins(8, 8, 8, 8)
        self.tabs_layout.setSpacing(6)
        area.setWidget(holder)
        self.tab_group = QButtonGroup(self)
        self.tab_group.setExclusive(True)
        return area

    def _build_content(self):
        self.stack = QStackedWidget()
        # trang 0: chưa có tệp -> chỉ một ô "Tải tệp lên"
        empty = QWidget()
        el = QVBoxLayout(empty)
        el.setContentsMargins(12, 8, 12, 12)
        self.upload_box = QPushButton("＋\nTải tệp lên\nKéo thả hoặc bấm để chọn tệp / thư mục")
        self.upload_box.setObjectName("uploadBox")
        self.upload_box.setCursor(Qt.PointingHandCursor)
        self.upload_box.clicked.connect(self.show_upload_menu)
        el.addWidget(self.upload_box)
        # trang 1: có tệp
        full = QWidget()
        fl = QVBoxLayout(full)
        fl.setContentsMargins(10, 4, 10, 6)
        head = QHBoxLayout()
        self.header = QLabel("")
        self.header.setObjectName("heading")
        head.addWidget(self.header, 1)
        self.more_btn = QPushButton("+ Tải thêm")
        self.more_btn.clicked.connect(self.show_upload_menu)
        head.addWidget(self.more_btn)
        fl.addLayout(head)
        self.list = FileList()
        self.list.itemDoubleClicked.connect(self.open_item)
        self.list.customContextMenuRequested.connect(self.item_menu)
        self.list.set_grid_mode(self.grid_mode)
        fl.addWidget(self.list, 1)
        hint = QLabel("Kéo thẻ vào cửa sổ Moho để đưa tệp vào dự án")
        hint.setObjectName("muted")
        fl.addWidget(hint)
        self.stack.addWidget(empty)
        self.stack.addWidget(full)
        return self.stack

    def _build_bottom(self):
        w = QWidget()
        w.setObjectName("bottom")
        h = QHBoxLayout(w)
        h.setContentsMargins(8, 8, 8, 8)
        h.setSpacing(6)
        self.manage_btn = QPushButton("Quản lý")
        self.manage_btn.setMinimumHeight(36)
        self.manage_btn.clicked.connect(self.open_manage)
        self.script_btn = QPushButton("Kịch bản")
        self.script_btn.setProperty("gold", True)
        self.script_btn.setMinimumHeight(36)
        self.script_btn.clicked.connect(self.open_script)
        h.addWidget(self.manage_btn, 1)
        h.addWidget(self.script_btn, 1)
        return w

    # ------------------------------------------------------------ các mục (tab)
    def rebuild_tabs(self, select=None):
        for b in list(self.tab_group.buttons()):
            self.tab_group.removeButton(b)
        while self.tabs_layout.count():
            item = self.tabs_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        cats = self.db.categories()
        chosen = None
        for c in cats:
            b = QPushButton(c["name"])
            b.setCheckable(True)
            b.setProperty("tab", True)
            b.setCursor(Qt.PointingHandCursor)
            b.setContextMenuPolicy(Qt.CustomContextMenu)
            b.customContextMenuRequested.connect(lambda _pos, cid=c["id"], btn=b: self.tab_menu(cid, btn))
            b.clicked.connect(lambda _=False, cid=c["id"]: self.select_category(cid))
            self.tab_group.addButton(b)
            self.tabs_layout.addWidget(b)
            b.setProperty("cid", c["id"])
            if select is not None and str(c["id"]) == str(select):
                chosen = c["id"]
        add = QPushButton("+ Thêm mục")
        add.setProperty("ghost", True)
        add.setCursor(Qt.PointingHandCursor)
        add.clicked.connect(self.add_category)
        self.tabs_layout.addWidget(add)
        self.tabs_layout.addStretch(1)
        if chosen is None and cats:
            chosen = cats[0]["id"]
        if chosen is None:
            self.current_cat = None
            self.refresh_items()
        else:
            self.select_category(chosen)

    def select_category(self, cat_id):
        self.current_cat = cat_id
        for b in self.tab_group.buttons():
            b.setChecked(b.property("cid") == cat_id)
        self.db.set_setting("last_category", cat_id)
        self.refresh_items()

    def add_category(self):
        name, ok = QInputDialog.getText(self, "Thêm mục", "Tên mục mới:")
        if not ok:
            return
        try:
            cid = self.db.add_category(name)
        except ValueError as e:
            QMessageBox.warning(self, "Không thêm được", str(e))
            return
        self.rebuild_tabs(select=cid)

    def tab_menu(self, cat_id, btn):
        m = QMenu(self)
        a_ren = m.addAction("Đổi tên mục")
        a_del = m.addAction("Xóa mục (không xóa tệp thật)")
        act = m.exec(btn.mapToGlobal(btn.rect().bottomLeft()))
        if act == a_ren:
            name, ok = QInputDialog.getText(self, "Đổi tên mục", "Tên mới:", text=btn.text())
            if ok:
                try:
                    self.db.rename_category(cat_id, name)
                except ValueError as e:
                    QMessageBox.warning(self, "Không đổi được", str(e))
                    return
                self.rebuild_tabs(select=cat_id)
        elif act == a_del:
            r = QMessageBox.question(
                self, "Xóa mục",
                f"Xóa mục “{btn.text()}”?\nChỉ xóa danh sách trong phần mềm, tệp thật trên máy KHÔNG bị xóa.")
            if r == QMessageBox.Yes:
                self.db.delete_category(cat_id)
                self.rebuild_tabs()

    # ------------------------------------------------------------ tệp
    def refresh_items(self, *_):
        self.list.clear()
        if self.current_cat is None:
            self.stack.setCurrentIndex(0)
            return
        items = self.db.items(self.current_cat)
        self.total_in_cat = len(items)
        if not items:
            self.stack.setCurrentIndex(0)
            return
        q = self.search.text().strip().lower()
        for it in items:
            name = it["display_name"] or os.path.basename(it["path"])
            if q and q not in name.lower():
                continue
            li = QListWidgetItem(name)
            li.setIcon(file_icon(it["path"]))
            li.setData(Qt.UserRole, it["path"])
            li.setData(Qt.UserRole + 1, it["id"])
            li.setToolTip(it["path"])
            self.list.addItem(li)
        self.stack.setCurrentIndex(1)
        self._update_header()

    def _update_header(self):
        name = ""
        for b in self.tab_group.buttons():
            if b.property("cid") == self.current_cat:
                name = b.text()
        self.header.setText(f"{name}  ·  {self.list.count()}/{getattr(self, 'total_in_cat', 0)} tệp")

    def add_paths(self, paths):
        if self.current_cat is None:
            QMessageBox.information(self, "Chưa có mục", "Hãy bấm “+ Thêm mục” để tạo mục trước.")
            return 0
        n = self.db.add_items(self.current_cat, paths)
        self.refresh_items()
        return n

    def show_upload_menu(self):
        m = QMenu(self)
        a_files = m.addAction("Chọn tệp...")
        a_dir = m.addAction("Chọn thư mục...")
        pos = self.upload_box.mapToGlobal(self.upload_box.rect().center()) \
            if self.stack.currentIndex() == 0 else self.more_btn.mapToGlobal(self.more_btn.rect().bottomLeft())
        act = m.exec(pos)
        if act == a_files:
            files, _ = QFileDialog.getOpenFileNames(self, "Chọn tệp để thêm vào mục")
            if files:
                self.add_paths(files)
        elif act == a_dir:
            d = QFileDialog.getExistingDirectory(self, "Chọn thư mục để thêm vào mục")
            if d:
                self.add_paths([d])

    def reload_current(self):
        if self.current_cat is None:
            return
        removed = self.db.prune_missing(self.current_cat)
        self.refresh_items()
        if self.stack.currentIndex() == 1:
            self.header.setText(f"Đã đọc lại" + (f" · bỏ {removed} tệp không còn" if removed else " · không có thay đổi"))
            self.info_timer.start(2500)

    def open_item(self, li):
        QDesktopServices.openUrl(QUrl.fromLocalFile(li.data(Qt.UserRole)))

    def item_menu(self, pos):
        sel = self.list.selectedItems()
        if not sel:
            return
        m = QMenu(self)
        a_open = m.addAction("Mở tệp")
        a_dir = m.addAction("Mở thư mục chứa tệp")
        a_copy = m.addAction("Sao chép đường dẫn")
        m.addSeparator()
        a_rm = m.addAction("Bỏ khỏi mục (không xóa tệp thật)")
        act = m.exec(self.list.viewport().mapToGlobal(pos))
        if act == a_open:
            self.open_item(sel[0])
        elif act == a_dir:
            QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.dirname(sel[0].data(Qt.UserRole))))
        elif act == a_copy:
            QGuiApplication.clipboard().setText("\n".join(i.data(Qt.UserRole) for i in sel))
        elif act == a_rm:
            for i in sel:
                self.db.remove_item(i.data(Qt.UserRole + 1))
            self.refresh_items()

    def toggle_view(self):
        self.grid_mode = not self.grid_mode
        self.db.set_setting("grid", "1" if self.grid_mode else "0")
        self.view_btn.setIcon(make_icon("grid" if self.grid_mode else "list"))
        self.list.set_grid_mode(self.grid_mode)

    # ------------------------------------------------------------ kéo thả từ máy vào
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
            self.add_paths(paths)
            e.acceptProposedAction()

    # ------------------------------------------------------------ luôn nổi, mờ, thu gọn
    def set_pinned(self, on):
        self.db.set_setting("pinned", "1" if on else "0")
        geo = self.geometry()
        was_visible = self.isVisible()
        self.setWindowFlag(Qt.WindowStaysOnTopHint, bool(on))
        if was_visible:
            self.show()
            self.setGeometry(geo)

    def on_opacity_changed(self, v):
        self.rest_opacity = v
        self.db.set_setting("opacity", v)
        self.setWindowOpacity(v / 100.0)       # xem thử ngay
        self.restore_timer.start(900)          # rồi trả về rõ nếu chuột còn trong cửa sổ

    def _restore_full_opacity(self):
        if self.underMouse():
            self.setWindowOpacity(1.0)

    def enterEvent(self, e):
        self.setWindowOpacity(1.0)
        super().enterEvent(e)

    def leaveEvent(self, e):
        self.setWindowOpacity(self.rest_opacity / 100.0)
        super().leaveEvent(e)

    def toggle_collapse(self):
        if not self.collapsed:
            self.expanded_size = self.size()
            for w in (self.tabs_area, self.content, self.bottom):
                w.hide()
            self.collapse_btn.setIcon(make_icon("expand"))
            self.collapsed = True
            self.resize(self.width(), 10)
        else:
            for w in (self.tabs_area, self.content, self.bottom):
                w.show()
            self.collapse_btn.setIcon(make_icon("minus"))
            self.collapsed = False
            if self.expanded_size:
                self.resize(self.expanded_size)

    # ------------------------------------------------------------ Quản lý / Kịch bản (làm ở bước sau)
    def open_manage(self):
        QMessageBox.information(self, "Quản lý", "Cửa sổ Quản lý (thư mục nguồn, đổi tên mục, sao lưu) sẽ làm ở bước 6.")

    def open_script(self):
        QMessageBox.information(self, "Kịch bản", "Cửa sổ Kịch bản sẽ làm ở bước 4.")

    # ------------------------------------------------------------ lưu / khôi phục vị trí
    def _restore_geometry(self):
        g = self.db.get_setting("geometry")
        try:
            x, y, w, h = [int(v) for v in g.split(",")]
            self.setGeometry(x, y, max(w, 300), max(h, 300))
        except Exception:
            self.resize(380, 640)

    def closeEvent(self, e):
        size = self.expanded_size if self.collapsed and self.expanded_size else self.size()
        pos = self.pos()
        self.db.set_setting("geometry", f"{pos.x()},{pos.y()},{size.width()},{size.height()}")
        super().closeEvent(e)
