"""Cửa sổ Quản lý: thư mục nguồn, cài đặt, sao lưu / khôi phục."""
import os

import threading

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QFileDialog, QFormLayout, QHBoxLayout, QInputDialog, QLabel, QLineEdit, QMessageBox,
    QPushButton, QSpinBox, QTabWidget, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget,
)

from . import moho_script, native_drag, send_to_app
from .backup import load_backup_file, make_backup, restore_backup, save_backup_file
from .fsbrowse import default_groups, groups_to_json
from .widgets import DragChip

SORTS = (("name", "Tên"), ("date", "Ngày sửa đổi"), ("size", "Dung lượng"), ("type", "Loại tệp"))


class ManageDialog(QDialog):
    probeDone = Signal(str)

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
        self.tabs.addTab(self._tab_targets(), "Ứng dụng đích")
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
        self.native_check = QCheckBox("Kéo kiểu Windows gốc (thử nghiệm, chỉ bật nếu cách chuẩn không chạy)")
        self.native_check.setChecked(self.db.get_setting("native_drag2", "0") == "1")
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
        v.addWidget(self._drag_test_box())
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

    # ---- kiểm tra kéo thả
    def make_test_file(self):
        folder = os.path.join(os.path.dirname(self.db.path), "testdrag")
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, "kiem_tra_keo_tha.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write("Nếu bạn thấy tệp này ở Màn hình chính thì cách kéo của Manage Moho hoạt động.\n")
        return path

    def _drag_test_box(self):
        box = QWidget()
        v = QVBoxLayout(box)
        v.setContentsMargins(0, 6, 0, 6)
        title = QLabel("Kiểm tra kéo thả")
        title.setObjectName("heroTitle")
        info = QLabel("Giữ chuột vào ô vàng rồi kéo ra Màn hình chính (Desktop). Nếu tệp kiem_tra_keo_tha.txt hiện ra ở "
                      "Màn hình chính thì cách kéo của tool hoạt động; khi đó Moho nhận hay không là do Moho.")
        info.setWordWrap(True)
        info.setObjectName("muted")
        self.test_chip = DragChip("Kéo tôi ra Màn hình chính", self.make_test_file)
        self.test_chip.setMinimumHeight(34)
        self.test_chip.done.connect(self._test_done)
        self.test_status = QLabel("")
        self.test_status.setWordWrap(True)
        for w in (title, info, self.test_chip, self.test_status):
            v.addWidget(w)
        return box

    def _test_done(self, _path, action, ms):
        target = native_drag.last_info.get("tha_vao") or "không rõ"
        self.test_status.setText(f"Kết quả: {action} · thả vào: {target} · {ms} ms")

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
        self.db.set_setting("native_drag2", "1" if self.native_check.isChecked() else "0")
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

    # ---- ứng dụng đích (Moho và các phần mềm khác)
    def _tab_targets(self):
        w = QWidget()
        v = QVBoxLayout(w)
        info = QLabel("Chọn phần mềm bạn muốn đưa tệp vào. Kéo thả vẫn dùng được như cũ; ngoài ra chuột phải một tệp → "
                      "“Gửi vào …” sẽ tự mở hộp thoại Nhập của phần mềm đó và điền tệp giúp bạn. "
                      "Muốn dùng cho phần mềm khác thì bấm “Thêm ứng dụng”.")
        info.setWordWrap(True)
        v.addWidget(info)
        self.profiles = send_to_app.load_profiles(self.db)
        self.target_combo = QComboBox()
        self.target_combo.currentIndexChanged.connect(self._target_selected)
        form = QFormLayout()
        form.addRow("Ứng dụng đang dùng", self.target_combo)
        self.t_name = QLineEdit()
        self.t_keys = QLineEdit()
        self.t_keys.setToolTip("Một phần tên tệp .exe trong Task Manager, ví dụ: moho, premiere, photoshop. "
                               "Có thể nhiều từ, cách nhau bằng dấu phẩy.")
        self.t_import = QLineEdit()
        self.t_import.setToolTip("Phím tắt mở hộp thoại Nhập của phần mềm, ví dụ ctrl+shift+y")
        self.t_open = QLineEdit()
        self.t_open.setToolTip("Phím tắt mở hộp thoại Mở dự án, ví dụ ctrl+o")
        self.t_exts = QLineEdit()
        self.t_exts.setToolTip("Các đuôi tệp dùng phím Mở thay vì phím Nhập, ví dụ .moho, .anme")
        self.t_method = QComboBox()
        self.t_method.addItem("Script trong Moho (chắc nhất cho Moho)", send_to_app.METHOD_MOHO)
        self.t_method.addItem("Lệnh JSFL của Adobe Animate", send_to_app.METHOD_JSFL)
        self.t_method.addItem("Hộp thoại Nhập (phần mềm khác)", send_to_app.METHOD_DIALOG)
        self.t_method.addItem("Dán ảnh Ctrl+V (chỉ ảnh)", send_to_app.METHOD_PASTE)
        self.t_menu = QLineEdit()
        self.t_menu.setToolTip("Chữ có trong tên menu của script, để phần mềm tự bấm giúp (ví dụ: Manage Moho)")
        self.t_script_key = QLineEdit()
        self.t_script_key.setToolTip("Nếu bạn đã gán phím tắt cho script trong Moho (Edit → Keyboard Shortcuts), "
                                     "ghi vào đây để phần mềm tự bấm. Có thể để trống.")
        form.addRow("Tên hiển thị", self.t_name)
        form.addRow("Từ khóa tên .exe", self.t_keys)
        form.addRow("Phím tắt Nhập", self.t_import)
        form.addRow("Phím tắt Mở dự án", self.t_open)
        form.addRow("Đuôi tệp dùng phím Mở", self.t_exts)
        form.addRow("Cách gửi", self.t_method)
        form.addRow("Tên menu của script", self.t_menu)
        form.addRow("Phím tắt gọi script (nếu có)", self.t_script_key)
        v.addLayout(form)
        row = QHBoxLayout()
        b_add = QPushButton("Thêm ứng dụng")
        b_add.clicked.connect(self._target_add)
        self.t_del = QPushButton("Xóa")
        self.t_del.clicked.connect(self._target_delete)
        b_save = QPushButton("Lưu")
        b_save.setObjectName("gold")
        b_save.clicked.connect(self._target_save)
        b_test = QPushButton("Kiểm tra kết nối")
        b_test.setToolTip("Mở phần mềm đích, bấm phím Nhập, xem hộp thoại có hiện không rồi đóng lại")
        b_test.clicked.connect(self._target_probe)
        for b in (b_add, self.t_del, b_save, b_test):
            row.addWidget(b)
        v.addLayout(row)
        row2 = QHBoxLayout()
        b_inst = QPushButton("Cài script vào Moho...")
        b_inst.setObjectName("gold")
        b_inst.setToolTip("Chép script nhập tệp vào thư mục Custom Content của Moho")
        b_inst.clicked.connect(self._install_moho_script)
        row2.addWidget(b_inst)
        row2.addStretch(1)
        v.addLayout(row2)
        self.t_status = QLabel("")
        self.t_status.setWordWrap(True)
        self.t_status.setObjectName("muted")
        v.addWidget(self.t_status)
        v.addStretch(1)
        self.probeDone.connect(self.t_status.setText)
        self._target_fill_combo(send_to_app.active_id(self.db))
        return w

    def _target_fill_combo(self, select_id):
        self.target_combo.blockSignals(True)
        self.target_combo.clear()
        for p in self.profiles:
            self.target_combo.addItem(p["name"], p["id"])
        i = max(0, next((n for n, p in enumerate(self.profiles) if p["id"] == select_id), 0))
        self.target_combo.setCurrentIndex(i)
        self.target_combo.blockSignals(False)
        self._target_selected()

    def _cur_profile(self):
        i = self.target_combo.currentIndex()
        return self.profiles[i] if 0 <= i < len(self.profiles) else None

    def _target_selected(self, *_a):
        p = self._cur_profile()
        if not p:
            return
        self.t_name.setText(p["name"])
        self.t_keys.setText(", ".join(p["keywords"]))
        self.t_import.setText(p["import_hotkey"])
        self.t_open.setText(p["open_hotkey"])
        self.t_exts.setText(", ".join(p["open_exts"]))
        self.t_method.setCurrentIndex(max(0, self.t_method.findData(p["method"])))
        self.t_menu.setText(p.get("menu_text", ""))
        self.t_script_key.setText(p.get("script_hotkey", ""))
        self.t_del.setEnabled(not p.get("builtin"))

    def _target_read_form(self):
        """Đọc ô nhập vào hồ sơ hiện tại. Trả về thông báo lỗi hoặc ''. """
        p = self._cur_profile()
        if not p:
            return "Chưa chọn ứng dụng."
        keys = [k.strip() for k in self.t_keys.text().split(",") if k.strip()]
        if not keys:
            return "Cần ít nhất một từ khóa tên .exe (ví dụ: moho)."
        for label, edit in (("Phím tắt Nhập", self.t_import), ("Phím tắt Mở dự án", self.t_open)):
            try:
                send_to_app.parse_hotkey(edit.text())
            except ValueError as e:
                return f"{label}: {e}"
        if self.t_script_key.text().strip():
            try:
                send_to_app.parse_hotkey(self.t_script_key.text())
            except ValueError as e:
                return f"Phím tắt gọi script: {e}"
        p["name"] = self.t_name.text().strip() or p["name"]
        p["keywords"] = keys
        p["import_hotkey"] = self.t_import.text().strip().lower()
        p["open_hotkey"] = self.t_open.text().strip().lower()
        p["open_exts"] = [e.strip() for e in self.t_exts.text().split(",") if e.strip()]
        p["method"] = self.t_method.currentData()
        p["menu_text"] = self.t_menu.text().strip()
        p["script_hotkey"] = self.t_script_key.text().strip().lower()
        return ""

    def _target_save(self):
        err = self._target_read_form()
        if err:
            self.t_status.setText(err)
            return
        send_to_app.save_profiles(self.db, self.profiles)
        send_to_app.set_active(self.db, self._cur_profile()["id"])
        self.profiles = send_to_app.load_profiles(self.db)
        self._target_fill_combo(send_to_app.active_id(self.db))
        self.main.apply_settings()
        self.t_status.setText("Đã lưu. Từ giờ nút “Gửi vào …” và nút đưa ứng dụng lên trước dùng ứng dụng này.")

    def _target_add(self):
        name, ok = QInputDialog.getText(self, "Thêm ứng dụng", "Tên phần mềm (ví dụ: Krita):")
        if not ok or not name.strip():
            return
        pid = send_to_app.new_profile_id(self.profiles, name)
        self.profiles.append({"id": pid, "name": name.strip(), "keywords": [name.strip().split()[0].lower()],
                              "method": send_to_app.METHOD_DIALOG, "import_hotkey": "ctrl+o",
                              "open_hotkey": "ctrl+o", "open_exts": [], "builtin": False,
                              "script_hotkey": "", "menu_text": ""})
        self._target_fill_combo(pid)
        self.t_status.setText("Đã thêm. Kiểm tra từ khóa tên .exe và phím tắt Nhập của phần mềm đó rồi bấm Lưu.")

    def _target_delete(self):
        p = self._cur_profile()
        if not p or p.get("builtin"):
            return
        self.profiles = [x for x in self.profiles if x["id"] != p["id"]]
        send_to_app.save_profiles(self.db, self.profiles)
        if send_to_app.active_id(self.db) == p["id"]:
            send_to_app.set_active(self.db, "moho")
        self.profiles = send_to_app.load_profiles(self.db)
        self._target_fill_combo(send_to_app.active_id(self.db))
        self.main.apply_settings()
        self.t_status.setText("Đã xóa ứng dụng khỏi danh sách.")

    def _install_moho_script(self):
        """Chép script Lua vào Custom Content Folder của Moho (người dùng chọn thư mục đó)."""
        start = os.path.join(os.path.expanduser("~"), "Documents")
        d = QFileDialog.getExistingDirectory(
            self, "Chọn Custom Content Folder của Moho (Moho → Edit → Preferences → nút Custom Content Folder)", start)
        if not d:
            return
        try:
            path = moho_script.install_script(d)
        except OSError as e:
            self.t_status.setText(f"Không ghi được vào thư mục đó ({e}). Thử thư mục khác hoặc chạy phần mềm bằng quyền "
                                  "Administrator nếu là thư mục Program Files.")
            return
        self.t_status.setText(f"Đã cài script: {path}\nBây giờ KHỞI ĐỘNG LẠI Moho; menu Scripts sẽ có "
                              "“Manage Moho - Import”.")

    def _target_probe(self):
        err = self._target_read_form()
        if err:
            self.t_status.setText(err)
            return
        prof = dict(self._cur_profile())
        self.t_status.setText(f"Đang kiểm tra {prof['name']}... đừng chạm chuột/bàn phím trong vài giây.")

        def work():
            try:
                if prof["method"] == send_to_app.METHOD_MOHO:
                    info = send_to_app.probe_script(prof)
                    if not info["platform"]:
                        msg = "Chức năng này chỉ chạy trên Windows."
                    elif not info["app"]:
                        msg = f"Chưa thấy {prof['name']} đang chạy (từ khóa tên .exe: {', '.join(prof['keywords'])})."
                    elif info["elevated"]:
                        msg = send_to_app.MESSAGES["elevated"].format(app=prof["name"], detail="")
                    elif info["menu"]:
                        msg = (f"Đạt: thấy {prof['name']} (“{info['app']}”) và đã bấm được menu của script. "
                               f"Nếu {prof['name']} hiện thông báo “nothing to import” nghĩa là script đã cài và chạy tốt.")
                    else:
                        msg = (f"Thấy {prof['name']} nhưng không tự bấm được menu script (bình thường với Moho). "
                               "Vẫn dùng được: sau khi bấm “Gửi vào …”, bạn bấm Scripts → Manage Moho - Import một lần; "
                               "hoặc gán phím tắt cho script trong Moho rồi ghi vào ô “Phím tắt gọi script”.")
                    self.probeDone.emit(msg)
                    return
                if prof["method"] == send_to_app.METHOD_JSFL:
                    info = send_to_app.probe_script(prof)
                    self.probeDone.emit(
                        f"Đạt: thấy {prof['name']} (“{info['app']}”). Lệnh nhập chạy bằng tệp JSFL khi bạn gửi tệp."
                        if info["app"] else f"Chưa thấy {prof['name']} đang chạy (từ khóa: {', '.join(prof['keywords'])}).")
                    return
                info = send_to_app.probe(prof)
                if not info["platform"]:
                    msg = "Chức năng này chỉ chạy trên Windows."
                elif info.get("error"):
                    msg = f"Phím tắt chưa đúng: {info['error']}"
                elif not info["app"]:
                    msg = f"Chưa thấy {prof['name']} đang chạy (từ khóa tên .exe: {', '.join(prof['keywords'])})."
                elif info["elevated"]:
                    msg = send_to_app.MESSAGES["elevated"].format(app=prof["name"], detail="")
                elif info["dialog"]:
                    msg = (f"Đạt: thấy {prof['name']} (“{info['app']}”) và hộp thoại “{info['title']}” hiện ra khi bấm "
                           f"{prof['import_hotkey']}. Chức năng Gửi vào {prof['name']} dùng được.")
                else:
                    msg = send_to_app.MESSAGES["no_dialog"].format(app=prof["name"], detail="")
            except Exception as e:
                msg = f"Kiểm tra lỗi: {e}"
            self.probeDone.emit(msg)

        threading.Thread(target=work, daemon=True).start()
