"""Cửa sổ Quản lý: thư mục nguồn, cài đặt, sao lưu / khôi phục."""
import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QFileDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
    QPushButton, QSpinBox, QTabWidget, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget,
)

from .backup import load_backup_file, make_backup, restore_backup, save_backup_file
from .fsbrowse import default_groups, groups_to_json

SORTS = (("name", "Tên"), ("date", "Ngày sửa đổi"), ("size", "Dung lượng"), ("type", "Loại tệp"))


class ManageDialog(QDialog):
    def __init__(self, main):
        super().__init__(main)
        self.main, self.db = main, main.db
        self.setWindowTitle("Quản lý")
        self.setModal(True)
        self.resize(600, 540)
        v = QVBoxLayout(self)
        self.tabs = QTabWidget()
        self.tabs.addTab(self._tab_sources(), "Thư mục nguồn")
        self.tabs.addTab(self._tab_settings(), "Cài đặt")
        self.tabs.addTab(self._tab_backup(), "Sao lưu")
        v.addWidget(self.tabs)
        row = QHBoxLayout()
        row.addStretch(1)
        close = QPushButton("Đóng")
        close.clicked.connect(self.accept)
        row.addWidget(close)
        v.addLayout(row)

    # ---- thư mục nguồn
    def _tab_sources(self):
        w = QWidget()
        v = QVBoxLayout(w)
        v.addWidget(QLabel("Các thư mục và tệp đã thêm vào từng mục. Bỏ khỏi mục chỉ xóa danh sách, không xóa tệp thật."))
        self.tree = QTreeWidget()
        self.tree.setHeaderLabel("Mục / đường dẫn")
        v.addWidget(self.tree, 1)
        row = QHBoxLayout()
        add = QPushButton("Thêm thư mục vào mục đã chọn...")
        add.clicked.connect(self.add_folder)
        rem = QPushButton("Bỏ khỏi mục")
        rem.clicked.connect(self.remove_selected)
        prune = QPushButton("Dọn mục không còn trên máy")
        prune.clicked.connect(self.prune)
        for b in (add, rem, prune):
            row.addWidget(b)
        v.addLayout(row)
        self.src_status = QLabel("")
        self.src_status.setObjectName("muted")
        v.addWidget(self.src_status)
        self.reload_tree()
        return w

    def reload_tree(self):
        self.tree.clear()
        for c in self.db.categories():
            if c["kind"] == "fav":
                continue
            top = QTreeWidgetItem([c["name"]])
            top.setData(0, Qt.UserRole, ("cat", c["id"]))
            for r in self.db.roots(c["id"]):
                child = QTreeWidgetItem([r["path"] + ("" if os.path.exists(r["path"]) else "   (không còn trên máy)")])
                child.setData(0, Qt.UserRole, ("root", r["id"]))
                top.addChild(child)
            self.tree.addTopLevelItem(top)
            top.setExpanded(top.childCount() > 0)

    def add_folder(self):
        it = self.tree.currentItem()
        if it is None:
            self.src_status.setText("Hãy chọn một mục trong danh sách trước.")
            return
        kind, ident = it.data(0, Qt.UserRole)
        if kind == "root":
            it = it.parent()
            ident = it.data(0, Qt.UserRole)[1]
        d = QFileDialog.getExistingDirectory(self, "Chọn thư mục để thêm")
        if d:
            n = self.db.add_roots(ident, [d])
            self.reload_tree()
            self.src_status.setText(f"Đã thêm {n} thư mục.")
            self.main.refresh()

    def remove_selected(self):
        it = self.tree.currentItem()
        if it is None or it.data(0, Qt.UserRole)[0] != "root":
            self.src_status.setText("Hãy chọn một đường dẫn (dòng con) để bỏ.")
            return
        self.db.remove_root(it.data(0, Qt.UserRole)[1])
        self.reload_tree()
        self.main.refresh()

    def prune(self):
        n = self.db.prune_missing_roots()
        self.reload_tree()
        self.src_status.setText(f"Đã bỏ {n} mục không còn trên máy.")
        self.main.refresh()

    # ---- cài đặt
    def _tab_settings(self):
        w = QWidget()
        v = QVBoxLayout(w)
        form = QFormLayout()
        self.page_spin = QSpinBox()
        self.page_spin.setRange(1, 200)
        self.page_spin.setValue(self.main.page_size)
        self.sort_combo = QComboBox()
        for key, label in SORTS:
            self.sort_combo.addItem(label, key)
        self.sort_combo.setCurrentIndex(max(0, [k for k, _l in SORTS].index(self.main.sort_mode)
                                            if self.main.sort_mode in [k for k, _l in SORTS] else 0))
        self.deep_check = QCheckBox("Tìm cả trong thư mục con")
        self.deep_check.setChecked(self.main.deep)
        self.hover_check = QCheckBox("Phát âm thanh khi rê chuột vào thẻ")
        self.hover_check.setChecked(self.main.hover_enabled)
        self.live_check = QCheckBox("GIF và video chạy ngay trên thẻ")
        self.live_check.setChecked(self.main.live.enabled)
        self.native_check = QCheckBox("Kéo tệp kiểu Windows gốc (giống kéo từ File Explorer)")
        self.native_check.setChecked(self.db.get_setting("native_drag", "1") == "1")
        self.export_edit = QLineEdit(self.db.get_setting("export_dir") or "")
        self.export_edit.setPlaceholderText("Mặc định: thư mục exports trong dữ liệu của phần mềm")
        pick = QPushButton("Chọn...")
        pick.clicked.connect(self._pick_export)
        er = QHBoxLayout()
        er.addWidget(self.export_edit, 1)
        er.addWidget(pick)
        form.addRow("Số mục mỗi trang", self.page_spin)
        form.addRow("Sắp xếp mặc định", self.sort_combo)
        form.addRow("", self.deep_check)
        form.addRow("", self.hover_check)
        form.addRow("", self.live_check)
        form.addRow("", self.native_check)
        form.addRow("Thư mục tool tự lưu đoạn âm thanh đã cắt (khi kéo vào Moho)", er)
        v.addLayout(form)
        row = QHBoxLayout()
        restore = QPushButton("Khôi phục mục mặc định")
        restore.clicked.connect(self._restore_cats)
        groups = QPushButton("Đặt lại nhóm đuôi tệp về mặc định")
        groups.clicked.connect(self._reset_groups)
        row.addWidget(restore)
        row.addWidget(groups)
        v.addLayout(row)
        v.addStretch(1)
        save = QPushButton("Lưu cài đặt")
        save.setObjectName("primary")
        save.clicked.connect(self.apply)
        v.addWidget(save, 0, Qt.AlignRight)
        self.set_status = QLabel("")
        self.set_status.setObjectName("muted")
        v.addWidget(self.set_status)
        return w

    def _pick_export(self):
        d = QFileDialog.getExistingDirectory(self, "Chọn thư mục lưu đoạn âm thanh")
        if d:
            self.export_edit.setText(d)

    def apply(self):
        self.db.set_setting("page_size", self.page_spin.value())
        self.db.set_setting("sort", self.sort_combo.currentData())
        self.db.set_setting("deep_search", "1" if self.deep_check.isChecked() else "0")
        self.db.set_setting("hover_audio", "1" if self.hover_check.isChecked() else "0")
        self.db.set_setting("live_thumbs", "1" if self.live_check.isChecked() else "0")
        self.db.set_setting("native_drag", "1" if self.native_check.isChecked() else "0")
        self.db.set_setting("export_dir", self.export_edit.text().strip())
        self.main.apply_settings()
        self.set_status.setText("Đã lưu cài đặt.")

    def _restore_cats(self):
        n = self.db.restore_defaults()
        self.main.apply_settings()
        self.reload_tree()
        self.set_status.setText(f"Đã khôi phục {n} mục mặc định." if n else "Không có mục mặc định nào bị thiếu.")

    def _reset_groups(self):
        if QMessageBox.question(self, "Đặt lại", "Đưa tất cả nhóm đuôi tệp về mặc định? Nhóm bạn tự thêm sẽ bị xóa.") != QMessageBox.Yes:
            return
        self.db.set_setting("ext_groups", groups_to_json(default_groups()))
        self.main.apply_settings()
        self.set_status.setText("Đã đặt lại nhóm đuôi tệp.")

    # ---- sao lưu
    def _tab_backup(self):
        w = QWidget()
        v = QVBoxLayout(w)
        info = QLabel("Sao lưu gồm: các mục, thư mục nguồn, tên hiển thị, yêu thích, ghim, cài đặt, tài khoản AI, "
                      "kịch bản và phiên bản kịch bản. Không gồm các tệp tài nguyên thật trên máy. "
                      "Không lưu mật khẩu: đăng nhập AI nằm trong Chrome/Edge.")
        info.setWordWrap(True)
        v.addWidget(info)
        row = QHBoxLayout()
        b1 = QPushButton("Sao lưu cài đặt...")
        b1.setObjectName("gold")
        b1.clicked.connect(self.backup)
        b2 = QPushButton("Khôi phục từ tệp sao lưu...")
        b2.clicked.connect(self.restore)
        row.addWidget(b1)
        row.addWidget(b2)
        v.addLayout(row)
        v.addStretch(1)
        self.bk_status = QLabel("")
        self.bk_status.setObjectName("muted")
        self.bk_status.setWordWrap(True)
        v.addWidget(self.bk_status)
        return w

    def backup(self, path=None):
        if not path:
            path, _f = QFileDialog.getSaveFileName(self, "Sao lưu cài đặt", "manage_moho_backup.json", "Sao lưu (*.json)")
        if path:
            save_backup_file(path, make_backup(self.db, self.main.script_store))
            self.bk_status.setText(f"Đã sao lưu: {path}")

    def restore(self, path=None):
        if not path:
            path, _f = QFileDialog.getOpenFileName(self, "Chọn tệp sao lưu", "", "Sao lưu (*.json)")
        if not path:
            return
        try:
            state = load_backup_file(path)
        except (ValueError, OSError) as e:
            QMessageBox.warning(self, "Không khôi phục được", str(e))
            return
        if QMessageBox.question(self, "Khôi phục", "Thay các mục, tên hiển thị, cài đặt và tài khoản AI hiện tại bằng bản sao lưu?") != QMessageBox.Yes:
            return
        restore_backup(self.db, self.main.script_store, state)
        self.main.apply_settings()
        self.main.refresh_script_window()
        self.reload_tree()
        self.bk_status.setText("Đã khôi phục từ bản sao lưu.")
