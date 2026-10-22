import time

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (
    QButtonGroup, QCheckBox, QDialog, QDialogButtonBox, QFileDialog, QGridLayout, QHBoxLayout,
    QInputDialog, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMessageBox, QPushButton,
    QToolButton, QVBoxLayout,
)

from .fsbrowse import parse_exts
from .icons import CATEGORY_COLORS, CATEGORY_ICONS, image_pixmap, make_icon


class CategoryDialog(QDialog):
    """Thêm / sửa mục: tên, biểu tượng có sẵn hoặc ảnh từ máy, màu."""

    def __init__(self, parent, title, name="", icon="folder", color=None, image=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.icon = icon if icon in CATEGORY_ICONS else "folder"
        self.color = color or CATEGORY_COLORS[6]
        self.image = image
        v = QVBoxLayout(self)
        v.addWidget(QLabel("Tên mục"))
        self.name_edit = QLineEdit(name)
        self.name_edit.setPlaceholderText("Ví dụ: Cảnh phim")
        v.addWidget(self.name_edit)
        v.addWidget(QLabel("Biểu tượng"))
        grid = QGridLayout()
        self.icon_btns = {}
        group = QButtonGroup(self)
        for i, n in enumerate(CATEGORY_ICONS):
            b = QToolButton()
            b.setCheckable(True)
            b.setFixedSize(38, 38)
            b.setIconSize(QSize(20, 20))
            b.setToolTip(n)
            group.addButton(b)
            b.clicked.connect(lambda _=False, n=n: self._pick_icon(n))
            self.icon_btns[n] = b
            grid.addWidget(b, i // 7, i % 7)
        v.addLayout(grid)
        v.addWidget(QLabel("Màu"))
        row = QHBoxLayout()
        for c in CATEGORY_COLORS:
            b = QPushButton()
            b.setFixedSize(24, 24)
            b.setStyleSheet(f"background:{c};border-radius:12px;padding:0;")
            b.clicked.connect(lambda _=False, c=c: self._pick_color(c))
            row.addWidget(b)
        row.addStretch(1)
        v.addLayout(row)
        img_row = QHBoxLayout()
        self.preview = QLabel()
        self.preview.setFixedSize(44, 44)
        img_btn = QPushButton("Chọn ảnh từ máy...")
        img_btn.clicked.connect(self._pick_image)
        clear_btn = QPushButton("Bỏ ảnh")
        clear_btn.clicked.connect(self._clear_image)
        img_row.addWidget(self.preview)
        img_row.addWidget(img_btn)
        img_row.addWidget(clear_btn)
        img_row.addStretch(1)
        v.addLayout(img_row)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        v.addWidget(buttons)
        self._refresh()

    def _pick_icon(self, name):
        self.icon = name
        self.image = None
        self._refresh()

    def _pick_color(self, color):
        self.color = color
        self._refresh()

    def _pick_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Chọn ảnh làm biểu tượng", "", "Ảnh (*.png *.jpg *.jpeg *.webp *.bmp *.gif)")
        if path:
            self.image = path
            self._refresh()

    def _clear_image(self):
        self.image = None
        self._refresh()

    def _refresh(self):
        for n, b in self.icon_btns.items():
            b.setIcon(make_icon(n, self.color if not self.image else "#9fb0cf", 20))
            b.setChecked(n == self.icon and not self.image)
        pm = image_pixmap(self.image, 44) if self.image else None
        if pm is None:
            pm = make_icon(self.icon, self.color, 36).pixmap(36, 36)
        self.preview.setPixmap(pm)

    def _accept(self):
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "Thiếu tên", "Hãy nhập tên mục.")
            return
        self.accept()

    def values(self):
        return {"name": self.name_edit.text().strip(), "icon": self.icon,
                "color": self.color, "image": self.image}


class FilterDialog(QDialog):
    """Chọn nhóm đuôi tệp được hiển thị; sửa đuôi tệp trong nhóm; thêm/xóa nhóm."""

    def __init__(self, parent, groups, active):
        super().__init__(parent)
        self.setWindowTitle("Bộ lọc định dạng")
        self.setModal(True)
        self.resize(420, 420)
        self.groups = {k: [v[0], list(v[1])] for k, v in groups.items()}
        v = QVBoxLayout(self)
        self.all_box = QCheckBox("Hiện tất cả loại tệp (không lọc)")
        self.all_box.setChecked(not active)
        self.all_box.toggled.connect(lambda on: self.list.setEnabled(not on))
        v.addWidget(self.all_box)
        self.list = QListWidget()
        for k in self.groups:
            it = QListWidgetItem(self._label(k))
            it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
            it.setCheckState(Qt.Checked if k in active else Qt.Unchecked)
            it.setData(Qt.UserRole, k)
            self.list.addItem(it)
        self.list.setEnabled(bool(active))
        self.list.currentItemChanged.connect(self._on_current)
        v.addWidget(self.list, 1)
        v.addWidget(QLabel("Đuôi tệp của nhóm đang chọn (cách nhau bằng dấu cách):"))
        self.exts_edit = QLineEdit()
        self.exts_edit.setPlaceholderText(".png .jpg")
        self.exts_edit.editingFinished.connect(self._on_exts)
        v.addWidget(self.exts_edit)
        row = QHBoxLayout()
        add = QPushButton("Thêm nhóm")
        add.clicked.connect(self._add_group)
        rem = QPushButton("Xóa nhóm")
        rem.clicked.connect(self._remove_group)
        row.addWidget(add)
        row.addWidget(rem)
        row.addStretch(1)
        v.addLayout(row)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        v.addWidget(buttons)

    def _label(self, k):
        name, exts = self.groups[k]
        return f"{name}   ({' '.join(exts)})"

    def _current_key(self):
        it = self.list.currentItem()
        return it.data(Qt.UserRole) if it else None

    def _on_current(self, cur, _prev):
        k = cur.data(Qt.UserRole) if cur else None
        self.exts_edit.setText(" ".join(self.groups[k][1]) if k else "")

    def _on_exts(self):
        k = self._current_key()
        if not k:
            return
        self.groups[k][1] = parse_exts(self.exts_edit.text())
        self.list.currentItem().setText(self._label(k))

    def _add_group(self):
        name, ok = QInputDialog.getText(self, "Thêm nhóm", "Tên nhóm:")
        if not ok or not name.strip():
            return
        k = f"g{int(time.time() * 1000)}"
        self.groups[k] = [name.strip(), []]
        it = QListWidgetItem(self._label(k))
        it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
        it.setCheckState(Qt.Checked)
        it.setData(Qt.UserRole, k)
        self.list.addItem(it)
        self.list.setCurrentItem(it)
        self.exts_edit.setFocus()

    def _remove_group(self):
        k = self._current_key()
        if not k:
            return
        del self.groups[k]
        self.list.takeItem(self.list.currentRow())

    def values(self):
        active = []
        if not self.all_box.isChecked():
            for i in range(self.list.count()):
                it = self.list.item(i)
                if it.checkState() == Qt.Checked:
                    active.append(it.data(Qt.UserRole))
        return self.groups, active
