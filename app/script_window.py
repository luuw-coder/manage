"""Cửa sổ Kịch bản: 3 vùng kéo chỉnh kích thước (hỏi AI | danh sách kịch bản | soạn thảo)."""
import difflib
import html
import os
import re
import time

from PySide6.QtCore import QByteArray, QTimer, Qt, QUrl
from PySide6.QtGui import QBrush, QColor, QDesktopServices, QFont, QGuiApplication, QTextCharFormat, QTextCursor, QTextDocument
from PySide6.QtWidgets import (
    QColorDialog, QComboBox, QDialog, QFileDialog, QHBoxLayout, QInputDialog, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QMessageBox, QPushButton, QSpinBox, QSplitter, QStackedWidget, QTextEdit, QToolButton, QVBoxLayout, QWidget,
)

from . import ai_launcher, webpanel
from .ai_presets import PRESETS
from .icons import make_icon
from .scripts_store import ENC
from .theme import QSS


def diff_html(old, new):
    """So sánh hai bản: dòng xanh là thêm vào, dòng đỏ là bị bỏ so với bản hiện tại."""
    out = []
    for line in difflib.unified_diff(old.splitlines(), new.splitlines(), "Phiên bản", "Hiện tại", lineterm="", n=2):
        esc = html.escape(line) or "&nbsp;"
        if line.startswith("+") and not line.startswith("+++"):
            out.append(f'<div style="color:#6fe3a0">{esc}</div>')
        elif line.startswith("-") and not line.startswith("---"):
            out.append(f'<div style="color:#ff8787">{esc}</div>')
        else:
            out.append(f'<div style="color:#8fa0bf">{esc}</div>')
    return "".join(out) or '<div style="color:#8fa0bf">Hai bản giống nhau.</div>'


def looks_like_html(content):
    c = (content or "").lstrip()[:200].lower()
    return c.startswith("<!doctype") or c.startswith("<html")


def plain_of(content):
    """Chữ thuần của một phiên bản (phiên bản có định dạng được lưu dưới dạng HTML)."""
    if looks_like_html(content):
        d = QTextDocument()
        d.setHtml(content)
        return d.toPlainText()
    return content


def template_text(kind, text):
    if kind == "scene":
        n = len(re.findall(r"^CẢNH\s+\d+", text, re.M)) + 1
        return f"\nCẢNH {n} – ĐỊA ĐIỂM – NGÀY\n"
    return {"context": "\n[BỐI CẢNH: ]\n", "action": "(Hành động) ",
            "dialog": "\nNHÂN VẬT\nLời thoại...\n", "note": "[Ghi chú: ]"}[kind]


class AiAccountDialog(QDialog):
    def __init__(self, parent, provider="", label="", url=""):
        super().__init__(parent)
        self.setWindowTitle("Tài khoản AI")
        self.setModal(True)
        self.resize(400, 220)
        v = QVBoxLayout(self)
        v.addWidget(QLabel("Chọn AI có sẵn hoặc tự nhập địa chỉ trang web"))
        self.combo = QComboBox()
        for name, _u in PRESETS:
            self.combo.addItem(name)
        self.combo.addItem("Khác (tự nhập)")
        v.addWidget(self.combo)
        self.provider = QLineEdit(provider)
        self.provider.setPlaceholderText("Tên AI, ví dụ Grok")
        self.label = QLineEdit(label)
        self.label.setPlaceholderText("Tên tài khoản, ví dụ Tài khoản 2")
        self.url = QLineEdit(url)
        self.url.setPlaceholderText("https://...")
        for w in (self.provider, self.label, self.url):
            v.addWidget(w)
        self.combo.currentIndexChanged.connect(self._preset)
        idx = next((i for i, (n, _u) in enumerate(PRESETS) if n == provider), len(PRESETS))
        self.combo.setCurrentIndex(idx)
        if provider:
            self.provider.setText(provider)
            self.url.setText(url)
        else:
            self._preset(idx)
        row = QHBoxLayout()
        ok, cancel = QPushButton("Lưu"), QPushButton("Hủy")
        ok.setObjectName("primary")
        ok.clicked.connect(self._ok)
        cancel.clicked.connect(self.reject)
        row.addStretch(1)
        row.addWidget(cancel)
        row.addWidget(ok)
        v.addLayout(row)

    def _preset(self, i):
        if i < len(PRESETS):
            self.provider.setText(PRESETS[i][0])
            self.url.setText(PRESETS[i][1])
        else:
            self.provider.clear()
            self.url.clear()

    def _ok(self):
        if not self.provider.text().strip() or not self.url.text().strip():
            QMessageBox.warning(self, "Thiếu thông tin", "Cần tên AI và địa chỉ trang web.")
            return
        self.accept()

    def values(self):
        return self.provider.text().strip(), self.label.text().strip() or "Tài khoản", self.url.text().strip()


class VersionsDialog(QDialog):
    def __init__(self, parent, db, script, current_text):
        super().__init__(parent)
        self.db, self.script, self.current_text = db, script, current_text
        self.chosen = None
        self.setWindowTitle(f"Phiên bản của “{script}”")
        self.setModal(True)
        self.resize(720, 460)
        v = QVBoxLayout(self)
        body = QHBoxLayout()
        self.list = QListWidget()
        self.list.setMaximumWidth(250)
        self.list.currentItemChanged.connect(self._show)
        self.view = QTextEdit()
        self.view.setReadOnly(True)
        body.addWidget(self.list)
        body.addWidget(self.view, 1)
        v.addLayout(body, 1)
        row = QHBoxLayout()
        self.restore_btn = QPushButton("Khôi phục bản này")
        self.restore_btn.setObjectName("gold")
        self.restore_btn.clicked.connect(self._restore)
        self.diff_btn = QPushButton("So sánh với bản hiện tại")
        self.diff_btn.clicked.connect(self._diff)
        self.del_btn = QPushButton("Xóa phiên bản")
        self.del_btn.clicked.connect(self._delete)
        close = QPushButton("Đóng")
        close.clicked.connect(self.reject)
        for b in (self.restore_btn, self.diff_btn, self.del_btn):
            row.addWidget(b)
        row.addStretch(1)
        row.addWidget(close)
        v.addLayout(row)
        note = QLabel("Khôi phục không làm mất bản hiện tại: bản hiện tại được lưu thành một phiên bản mới trước.")
        note.setObjectName("muted")
        v.addWidget(note)
        self.reload()

    def reload(self):
        self.list.clear()
        for ver in self.db.versions(self.script):
            when = time.strftime("%d/%m %H:%M", time.localtime(ver["created_at"]))
            it = QListWidgetItem(f"{ver['label']}  ·  {when}")
            it.setData(Qt.UserRole, ver["id"])
            self.list.addItem(it)
        has = self.list.count() > 0
        for b in (self.restore_btn, self.diff_btn, self.del_btn):
            b.setEnabled(has)
        if has:
            self.list.setCurrentRow(0)
        else:
            self.view.setPlainText("Chưa có phiên bản nào. Bấm “Lưu phiên bản” ở cửa sổ Kịch bản để tạo.")

    def _current_id(self):
        it = self.list.currentItem()
        return it.data(Qt.UserRole) if it else None

    def _show(self, *_a):
        vid = self._current_id()
        if vid is not None:
            content = self.db.get_version(vid)["content"]
            if looks_like_html(content):
                self.view.setHtml(content)
            else:
                self.view.setPlainText(content)

    def _diff(self):
        vid = self._current_id()
        if vid is not None:
            self.view.setHtml(diff_html(plain_of(self.db.get_version(vid)["content"]), self.current_text))

    def _restore(self):
        self.chosen = self._current_id()
        if self.chosen is not None:
            self.accept()

    def _delete(self):
        vid = self._current_id()
        if vid is not None:
            self.db.delete_version(vid)
            self.reload()


class AiPanel(QWidget):
    """Hỏi AI. Trang 1: chọn tài khoản AI. Trang 2: khung chat lớn (AI hiện ngay trong phần mềm)."""

    def __init__(self, win):
        super().__init__()
        self.win = win
        self.web_host = None
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        self.stack = QStackedWidget()
        outer.addWidget(self.stack)

        # --- trang chọn AI
        pick = QWidget()
        v = QVBoxLayout(pick)
        v.setContentsMargins(8, 8, 8, 8)
        head = QLabel("Hỏi AI")
        head.setObjectName("heroTitle")
        v.addWidget(head)
        self.list = QListWidget()
        self.list.itemDoubleClicked.connect(lambda _i: self.open_selected())
        v.addWidget(self.list, 1)
        r1 = QHBoxLayout()
        for text, fn in (("Mở", self.open_selected), ("+ Thêm", self.add), ("Sửa", self.edit), ("Xóa", self.remove)):
            b = QPushButton(text)
            if text == "Mở":
                b.setObjectName("primary")
                b.setStyleSheet("padding: 6px 14px;")
            b.clicked.connect(fn)
            r1.addWidget(b)
        v.addLayout(r1)
        self.status = QLabel("Mỗi tài khoản có đăng nhập riêng. Bấm đúp một AI để mở ngay trong khung.")
        self.status.setObjectName("muted")
        self.status.setWordWrap(True)
        v.addWidget(self.status)
        self.stack.addWidget(pick)

        # --- trang chat: thanh nhỏ phía trên, còn lại là khung web
        self.chat_page = QWidget()
        self.web_layout = QVBoxLayout(self.chat_page)
        self.web_layout.setContentsMargins(4, 4, 4, 4)
        self.web_layout.setSpacing(4)
        bar = QHBoxLayout()
        back = QPushButton("‹ Chọn AI")
        back.setMaximumHeight(26)
        back.clicked.connect(self.close_web)
        self.web_title = QLabel("")
        self.web_title.setObjectName("muted")
        ext = QPushButton("Cửa sổ riêng")
        ext.setMaximumHeight(26)
        ext.setToolTip("Mở AI bằng cửa sổ Chrome/Edge riêng (dùng khi trang không cho đăng nhập trong khung)")
        ext.clicked.connect(self.open_external)
        bar.addWidget(back)
        bar.addWidget(self.web_title, 1)
        bar.addWidget(ext)
        self.web_layout.addLayout(bar)
        self.stack.addWidget(self.chat_page)
        self.refresh()

    def refresh(self, select=None):
        self.list.clear()
        for a in self.win.db.ai_accounts():
            it = QListWidgetItem(f"{a['provider']}  ·  {a['label']}")
            it.setData(Qt.UserRole, a["id"])
            it.setToolTip(a["url"])
            self.list.addItem(it)
            if a["id"] == select:
                self.list.setCurrentItem(it)
        if self.list.currentRow() < 0 and self.list.count():
            self.list.setCurrentRow(0)

    def _selected(self):
        it = self.list.currentItem()
        if not it:
            return None
        return next((a for a in self.win.db.ai_accounts() if a["id"] == it.data(Qt.UserRole)), None)

    def open_selected(self):
        acc = self.win.db.ai_accounts() and self._selected()
        if not acc:
            self.status.setText("Hãy chọn một tài khoản AI trong danh sách.")
            return
        if webpanel.available() and self.win.db.get_setting("ai_embedded", "1") == "1":
            try:
                self._open_embedded(acc)
                return
            except Exception as e:  # nhúng không được thì quay về cửa sổ riêng
                self.status.setText(f"Không nhúng được khung web ({e}). Mở cửa sổ riêng.")
        self.open_external()

    def _open_embedded(self, acc):
        if self.web_host is None:
            self.web_host = webpanel.WebHost(self.win.profiles_dir(), self)
            self.web_layout.addWidget(self.web_host.view, 1)
        self.web_host.show_account(acc)
        self.web_title.setText(f"{acc['provider']} · {acc['label']}")
        self.stack.setCurrentWidget(self.chat_page)
        self.win.make_room_for_ai()

    def close_web(self):
        self.stack.setCurrentIndex(0)
        self.dispose()   # rời khung AI thì giải phóng trình duyệt nhúng để trả lại RAM

    def open_external(self):
        acc = self.win.db.ai_accounts() and self._selected()
        if not acc:
            self.status.setText("Hãy chọn một tài khoản AI trong danh sách.")
            return
        pos = None
        scr = QGuiApplication.primaryScreen()
        if scr:
            geo = scr.availableGeometry()
            x = self.win.x() + self.win.width() + 8
            if x + 520 <= geo.right():
                pos = (x, self.win.y())
        ok, msg = ai_launcher.launch(acc, self.win.profiles_dir(), (520, 760), pos)
        if not ok:
            QDesktopServices.openUrl(QUrl(acc["url"]))
            msg += " Đã mở bằng trình duyệt mặc định."
        self.status.setText(msg)
        if self.stack.currentWidget() is self.chat_page:
            self.web_title.setText(msg)

    def dispose(self):
        if self.web_host is not None:
            self.web_host.dispose()
            self.web_host = None

    def add(self):
        dlg = AiAccountDialog(self)
        if dlg.exec():
            try:
                aid = self.win.db.add_ai_account(*dlg.values())
            except ValueError as e:
                QMessageBox.warning(self, "Không thêm được", str(e))
                return
            self.refresh(aid)

    def edit(self):
        acc = self._selected()
        if not acc:
            return
        dlg = AiAccountDialog(self, acc["provider"], acc["label"], acc["url"])
        if dlg.exec():
            self.win.db.update_ai_account(acc["id"], *dlg.values())
            self.refresh(acc["id"])

    def remove(self):
        acc = self._selected()
        if acc and QMessageBox.question(self, "Xóa tài khoản", f"Xóa “{acc['provider']} · {acc['label']}” khỏi danh sách?") == QMessageBox.Yes:
            self.win.db.delete_ai_account(acc["id"])
            self.refresh()


class ScriptWindow(QWidget):
    def __init__(self, db, store, parent=None):
        super().__init__(parent)
        self.db, self.store = db, store
        self.current = None
        self._loading = False
        self.setWindowFlag(Qt.Window, True)
        self.setObjectName("root")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet(QSS)
        self.setWindowTitle("Kịch bản")
        self.resize(1000, 640)

        self.ai = AiPanel(self)
        listw = self._build_list()
        editor = self._build_editor()
        self.split_left = QSplitter(Qt.Vertical)
        self.split_left.addWidget(self.ai)
        self.split_left.addWidget(listw)
        self.split_left.setChildrenCollapsible(False)
        self.split_main = QSplitter(Qt.Horizontal)
        self.split_main.addWidget(self.split_left)
        self.split_main.addWidget(editor)
        self.split_main.setChildrenCollapsible(False)
        self.split_main.setStretchFactor(1, 1)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.addWidget(self.split_main)
        self.split_main.setSizes([340, 660])
        self.split_left.setSizes([440, 160])
        self._restore_splitters()

        self.save_timer = QTimer(self)
        self.save_timer.setSingleShot(True)
        self.save_timer.timeout.connect(self.save_now)
        self.refresh_list()
        if self.list.count():
            self.list.setCurrentRow(0)

    # ---- dựng giao diện
    def _build_list(self):
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(8, 4, 8, 6)
        v.setSpacing(4)
        top = QHBoxLayout()
        head = QLabel("Kịch bản")
        head.setObjectName("heroTitle")
        top.addWidget(head)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Tìm kịch bản...")
        self.search.setMaximumHeight(26)
        self.search.textChanged.connect(lambda _t: self.refresh_list(self.current))
        top.addWidget(self.search, 1)
        v.addLayout(top)
        self.list = QListWidget()
        self.list.currentItemChanged.connect(self._on_select)
        v.addWidget(self.list, 1)
        row = QHBoxLayout()
        for text, fn in (("+ Mới", self.new_script), ("Đổi tên", self.rename_script), ("Nhân bản", self.duplicate_script),
                         ("Xóa", self.delete_script), ("Nhập .txt", self.import_txt)):
            b = QPushButton(text)
            b.setMaximumHeight(24)
            b.setStyleSheet("padding: 2px 6px; font-size: 12px;")
            b.clicked.connect(fn)
            row.addWidget(b)
        row.setSpacing(3)
        v.addLayout(row)
        return w

    def _build_editor(self):
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(8, 8, 8, 8)
        r1 = QHBoxLayout()
        for text, kind in (("Bối cảnh", "context"), ("Phân cảnh", "scene"), ("Hành động", "action"),
                           ("Lời thoại", "dialog"), ("Ghi chú", "note")):
            b = QPushButton(text)
            b.clicked.connect(lambda _=False, k=kind: self.insert_template(k))
            r1.addWidget(b)
        r1.addStretch(1)
        undo, redo = QPushButton("Hoàn tác"), QPushButton("Làm lại")
        r1.addWidget(undo)
        r1.addWidget(redo)
        v.addLayout(r1)
        v.addLayout(self._build_format_bar())
        self.editor = QTextEdit()
        self.editor.setAcceptRichText(True)
        self.editor.setPlaceholderText("Chọn hoặc tạo một kịch bản ở danh sách bên trái, rồi viết tại đây...")
        self.editor.textChanged.connect(self._on_text)
        self.editor.currentCharFormatChanged.connect(self._sync_fmt)
        undo.clicked.connect(self.editor.undo)
        redo.clicked.connect(self.editor.redo)
        v.addWidget(self.editor, 1)
        r2 = QHBoxLayout()
        self.find_edit = QLineEdit()
        self.find_edit.setPlaceholderText("Tìm trong kịch bản...")
        self.find_edit.returnPressed.connect(self.find_next)
        find_btn = QPushButton("Tìm tiếp")
        find_btn.clicked.connect(self.find_next)
        save_ver = QPushButton("Lưu phiên bản")
        save_ver.clicked.connect(self.save_version)
        vers = QPushButton("Phiên bản...")
        vers.clicked.connect(self.show_versions)
        export = QPushButton("Xuất .txt")
        export.clicked.connect(self.export_txt)
        for wd in (self.find_edit, find_btn):
            r2.addWidget(wd, 1 if wd is self.find_edit else 0)
        for wd in (save_ver, vers, export):
            r2.addWidget(wd)
        v.addLayout(r2)
        self.footer = QLabel("")
        self.footer.setObjectName("muted")
        v.addWidget(self.footer)
        return w

    # ---- định dạng chữ: đậm/nghiêng/gạch chân, cỡ chữ, màu chữ, màu nền, căn dòng
    def _build_format_bar(self):
        row = QHBoxLayout()
        row.setSpacing(3)
        bold_font = QFont()
        bold_font.setBold(True)
        ital_font = QFont()
        ital_font.setItalic(True)
        und_font = QFont()
        und_font.setUnderline(True)
        self.bold_btn = self._fmt_button("B", "Chữ đậm", self.toggle_bold, bold_font)
        self.italic_btn = self._fmt_button("I", "Chữ nghiêng", self.toggle_italic, ital_font)
        self.under_btn = self._fmt_button("U", "Gạch chân", self.toggle_underline, und_font)
        self.size_spin = QSpinBox()
        self.size_spin.setRange(8, 48)
        self.size_spin.setValue(12)
        self.size_spin.setToolTip("Cỡ chữ")
        self.size_spin.valueChanged.connect(self.set_size)
        color_btn = QPushButton("Màu chữ")
        color_btn.clicked.connect(self.pick_color)
        bg_btn = QPushButton("Màu nền chữ")
        bg_btn.clicked.connect(self.pick_background)
        clear_btn = QPushButton("Xóa định dạng")
        clear_btn.clicked.connect(self.clear_format)
        for b in (self.bold_btn, self.italic_btn, self.under_btn, self.size_spin, color_btn, bg_btn):
            row.addWidget(b)
        row.addSpacing(8)
        for icon, tip, flag in (("alignl", "Căn trái", Qt.AlignLeft), ("alignc", "Căn giữa", Qt.AlignHCenter),
                                ("alignr", "Căn phải", Qt.AlignRight), ("alignj", "Căn đều hai bên", Qt.AlignJustify)):
            b = QToolButton()
            b.setIcon(make_icon(icon, "#e6ecf7", 16))
            b.setToolTip(tip)
            b.setAccessibleName(tip)
            b.setFixedSize(28, 26)
            b.clicked.connect(lambda _=False, f=flag: self.set_align(f))
            row.addWidget(b)
        row.addSpacing(8)
        row.addWidget(clear_btn)
        row.addStretch(1)
        return row

    def _fmt_button(self, text, tip, slot, font):
        b = QToolButton()
        b.setText(text)
        b.setToolTip(tip)
        b.setAccessibleName(tip)
        b.setCheckable(True)
        b.setFixedSize(28, 26)
        b.setFont(font)
        b.toggled.connect(slot)
        return b

    def _merge(self, fmt):
        self.editor.mergeCurrentCharFormat(fmt)
        self.editor.setFocus()

    def toggle_bold(self, on):
        f = QTextCharFormat()
        f.setFontWeight(700 if on else 400)
        self._merge(f)

    def toggle_italic(self, on):
        f = QTextCharFormat()
        f.setFontItalic(bool(on))
        self._merge(f)

    def toggle_underline(self, on):
        f = QTextCharFormat()
        f.setFontUnderline(bool(on))
        self._merge(f)

    def set_size(self, value):
        f = QTextCharFormat()
        f.setFontPointSize(float(value))
        self._merge(f)

    def set_color(self, color):
        f = QTextCharFormat()
        f.setForeground(QBrush(QColor(color)))
        self._merge(f)

    def set_background(self, color):
        f = QTextCharFormat()
        f.setBackground(QBrush(QColor(color)))
        self._merge(f)

    def pick_color(self):
        c = QColorDialog.getColor(QColor("#ffd43b"), self, "Chọn màu chữ")
        if c.isValid():
            self.set_color(c)

    def pick_background(self):
        c = QColorDialog.getColor(QColor("#1f4d3a"), self, "Chọn màu nền chữ")
        if c.isValid():
            self.set_background(c)

    def clear_format(self):
        self.editor.setCurrentCharFormat(QTextCharFormat())
        self.editor.setFocus()

    def set_align(self, flag):
        self.editor.setAlignment(flag)
        self.editor.setFocus()

    def _sync_fmt(self, fmt):
        for b, val in ((self.bold_btn, fmt.fontWeight() >= 600), (self.italic_btn, fmt.fontItalic()),
                       (self.under_btn, fmt.fontUnderline())):
            b.blockSignals(True)
            b.setChecked(bool(val))
            b.blockSignals(False)
        size = fmt.fontPointSize() or self.editor.font().pointSizeF() or 12
        self.size_spin.blockSignals(True)
        self.size_spin.setValue(int(round(size)))
        self.size_spin.blockSignals(False)

    # ---- lưu vị trí 3 vùng
    def _restore_splitters(self):
        for key, sp in (("script_split_main", self.split_main), ("script_split_left", self.split_left)):
            s = self.db.get_setting(key)
            if s:
                sp.restoreState(QByteArray.fromBase64(s.encode()))

    def save_layout(self):
        for key, sp in (("script_split_main", self.split_main), ("script_split_left", self.split_left)):
            self.db.set_setting(key, bytes(sp.saveState().toBase64()).decode())

    def make_room_for_ai(self):
        """Khi AI hiện trong khung chat: cột trái rộng hơn và khung AI chiếm gần hết chiều cao,
        danh sách kịch bản chỉ còn một dải nhỏ phía dưới."""
        if self.width() > 900 and self.split_main.sizes()[0] < 560:
            self.split_main.setSizes([560, max(300, self.width() - 600)])
        total = sum(self.split_left.sizes())
        if total > 360:
            self.split_left.setSizes([total - 140, 140])

    def profiles_dir(self):
        return os.path.join(os.path.dirname(self.db.path), "ai_profiles")

    # ---- danh sách kịch bản
    def refresh_list(self, select=None):
        q = self.search.text().strip().lower() if hasattr(self, "search") else ""
        self.list.blockSignals(True)
        self.list.clear()
        for n in self.store.list():
            if q and q not in n.lower():
                continue
            self.list.addItem(n)
        self.list.blockSignals(False)
        if select:
            for i in range(self.list.count()):
                if self.list.item(i).text() == select:
                    self.list.blockSignals(True)
                    self.list.setCurrentRow(i)
                    self.list.blockSignals(False)

    def _on_select(self, item, _prev):
        self.save_now()
        self.open_script(item.text() if item else None)

    def open_script(self, name):
        self.current = name
        self._loading = True
        html = self.store.read_html(name) if name else None
        if html:
            self.editor.setHtml(html)
        else:
            self.editor.setPlainText(self.store.read(name) if name else "")
        self.editor.document().clearUndoRedoStacks()
        self.editor.setEnabled(name is not None)
        self._loading = False
        self.footer.setText(f"{name or ''}" + (f" · {len(self.editor.toPlainText())} ký tự" if name else ""))

    def new_script(self):
        self.save_now()
        name = self.store.create()
        self.refresh_list(name)
        self.open_script(name)

    def rename_script(self):
        if not self.current:
            return
        new, ok = QInputDialog.getText(self, "Đổi tên kịch bản", "Tên mới:", text=self.current)
        if not ok:
            return
        self.save_now()
        try:
            new = self.store.rename(self.current, new)
        except ValueError as e:
            QMessageBox.warning(self, "Không đổi được", str(e))
            return
        self.db.rename_versions_of(self.current, new)
        self.current = new
        self.refresh_list(new)

    def duplicate_script(self):
        if not self.current:
            return
        self.save_now()
        name = self.store.duplicate(self.current)
        self.refresh_list(name)
        self.open_script(name)

    def delete_script(self):
        if not self.current:
            return
        if QMessageBox.question(self, "Xóa kịch bản",
                                f"Xóa kịch bản “{self.current}” (cả tệp .txt và các phiên bản đã lưu)?") != QMessageBox.Yes:
            return
        name = self.current
        self.current = None
        self.store.delete(name)
        self.db.delete_versions_of(name)
        self.refresh_list()
        self.open_script(self.list.item(0).text() if self.list.count() else None)
        if self.list.count():
            self.list.setCurrentRow(0)

    def import_txt(self):
        path, _f = QFileDialog.getOpenFileName(self, "Nhập kịch bản từ tệp .txt", "", "Văn bản (*.txt)")
        if path:
            self.save_now()
            name = self.store.import_file(path)
            self.refresh_list(name)
            self.open_script(name)

    def export_txt(self):
        if not self.current:
            return
        path, _f = QFileDialog.getSaveFileName(self, "Xuất kịch bản", self.current + ".txt", "Văn bản (*.txt)")
        if path:
            with open(path, "w", encoding=ENC, newline="") as f:
                f.write(self.editor.toPlainText())
            self.footer.setText(f"Đã xuất: {path}")

    # ---- soạn thảo, tự lưu
    def _on_text(self):
        if self._loading or not self.current:
            return
        self.footer.setText(f"{self.current} · đang chỉnh sửa...")
        self.save_timer.start(800)

    def save_now(self):
        self.save_timer.stop()
        if self.current and self.store.exists(self.current) and self.editor.isEnabled():
            text = self.editor.toPlainText()
            self.store.write(self.current, text, self.editor.toHtml())
            self.footer.setText(f"{self.current} · đã tự lưu · {len(text)} ký tự")

    def insert_template(self, kind):
        if not self.current:
            return
        self.editor.textCursor().insertText(template_text(kind, self.editor.toPlainText()))
        self.editor.setFocus()

    def find_next(self):
        t = self.find_edit.text()
        if t and not self.editor.find(t):
            self.editor.moveCursor(QTextCursor.Start)
            self.editor.find(t)

    # ---- phiên bản
    def save_version(self, label=None):
        if not self.current:
            return None
        if label is None:
            label, ok = QInputDialog.getText(self, "Lưu phiên bản", "Tên phiên bản:", text="Bản nháp")
            if not ok:
                return None
        self.save_now()
        vid = self.db.add_version(self.current, label, self.editor.toHtml())
        self.footer.setText(f"Đã lưu phiên bản “{label}”")
        return vid

    def show_versions(self):
        if not self.current:
            return
        self.save_now()
        dlg = VersionsDialog(self, self.db, self.current, self.editor.toPlainText())
        if dlg.exec() and dlg.chosen is not None:
            self.restore_version(dlg.chosen)

    def restore_version(self, vid):
        v = self.db.get_version(vid)
        if not v or not self.current:
            return
        self.save_now()
        self.db.add_version(self.current, "Trước khi khôi phục", self.editor.toHtml())
        if looks_like_html(v["content"]):
            self.editor.setHtml(v["content"])
        else:
            self.editor.setPlainText(v["content"])
        self.save_now()

    # ---- cầu nối với cửa sổ AI (qua bộ nhớ tạm)
    def send_selection(self):
        text = self.editor.textCursor().selectedText().replace("\u2029", "\n").strip()
        if not text:
            self.ai.status.setText("Hãy bôi đen một đoạn trong kịch bản trước.")
            return
        QGuiApplication.clipboard().setText(text)
        self.ai.status.setText("Đã sao chép đoạn đang chọn. Dán (Ctrl+V) vào cửa sổ AI.")

    def paste_reply(self):
        text = QGuiApplication.clipboard().text()
        if not (text and self.current):
            self.ai.status.setText("Chưa có gì trong bộ nhớ tạm hoặc chưa mở kịch bản.")
            return
        self.editor.textCursor().insertText("\n" + text + "\n")
        self.ai.status.setText("Đã chép nội dung vào kịch bản.")

    def closeEvent(self, e):
        self.save_now()
        self.save_layout()
        self.ai.dispose()
        super().closeEvent(e)
