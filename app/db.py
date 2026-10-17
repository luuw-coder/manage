"""Cơ sở dữ liệu SQLite của Manage Moho.

Nguyên tắc: chỉ lưu LIÊN KẾT tới tệp. Không bao giờ xóa/đổi tên/di chuyển tệp thật.
"""
import os
import sqlite3
import time

DEFAULT_CATEGORIES = ["Âm thanh", "Nhân vật", "Ảnh", "GIF"]


def collect_files(paths):
    """Mở rộng thư mục thành danh sách tệp (đệ quy). Bỏ qua đường dẫn không tồn tại."""
    out = []
    for p in paths:
        if os.path.isdir(p):
            for root, _dirs, files in os.walk(p):
                for name in sorted(files):
                    out.append(os.path.normpath(os.path.join(root, name)))
        elif os.path.isfile(p):
            out.append(os.path.normpath(p))
    return out


class Database:
    def __init__(self, path):
        folder = os.path.dirname(path)
        if folder:
            os.makedirs(folder, exist_ok=True)
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys=ON")
        self._create()
        self._seed()

    def _create(self):
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS categories(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                position INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS items(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
                path TEXT NOT NULL,
                display_name TEXT,
                added_at REAL NOT NULL,
                UNIQUE(category_id, path)
            );
            CREATE TABLE IF NOT EXISTS settings(
                key TEXT PRIMARY KEY,
                value TEXT
            );
            """
        )
        self.conn.commit()

    def _seed(self):
        if self.get_setting("seeded") is None:
            for name in DEFAULT_CATEGORIES:
                self.add_category(name)
            self.set_setting("seeded", "1")

    # ---- cài đặt ----
    def get_setting(self, key, default=None):
        row = self.conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return row["value"] if row else default

    def set_setting(self, key, value):
        self.conn.execute(
            "INSERT INTO settings(key,value) VALUES(?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, str(value)),
        )
        self.conn.commit()

    # ---- mục ----
    def categories(self):
        return [dict(r) for r in self.conn.execute(
            "SELECT id,name FROM categories ORDER BY position,id")]

    def add_category(self, name):
        name = (name or "").strip()
        if not name:
            raise ValueError("Tên mục không được để trống")
        pos = self.conn.execute("SELECT COALESCE(MAX(position),0)+1 FROM categories").fetchone()[0]
        try:
            cur = self.conn.execute(
                "INSERT INTO categories(name,position) VALUES(?,?)", (name, pos))
        except sqlite3.IntegrityError:
            raise ValueError("Đã có mục tên này")
        self.conn.commit()
        return cur.lastrowid

    def rename_category(self, cat_id, name):
        name = (name or "").strip()
        if not name:
            raise ValueError("Tên mục không được để trống")
        try:
            self.conn.execute("UPDATE categories SET name=? WHERE id=?", (name, cat_id))
        except sqlite3.IntegrityError:
            raise ValueError("Đã có mục tên này")
        self.conn.commit()

    def delete_category(self, cat_id):
        """Xóa mục và liên kết trong mục. KHÔNG đụng tới tệp thật."""
        self.conn.execute("DELETE FROM categories WHERE id=?", (cat_id,))
        self.conn.commit()

    # ---- tệp trong mục ----
    def items(self, cat_id):
        return [dict(r) for r in self.conn.execute(
            "SELECT id,path,display_name FROM items WHERE category_id=? ORDER BY id", (cat_id,))]

    def add_items(self, cat_id, paths):
        """Thêm tệp (thư mục sẽ được mở rộng). Trả về số tệp mới thêm."""
        added = 0
        for p in collect_files(paths):
            cur = self.conn.execute(
                "INSERT OR IGNORE INTO items(category_id,path,added_at) VALUES(?,?,?)",
                (cat_id, p, time.time()))
            added += cur.rowcount
        self.conn.commit()
        return added

    def remove_item(self, item_id):
        self.conn.execute("DELETE FROM items WHERE id=?", (item_id,))
        self.conn.commit()

    def prune_missing(self, cat_id):
        """Đọc lại: bỏ khỏi danh sách những tệp không còn trên máy. Trả về số tệp bỏ."""
        removed = 0
        for it in self.items(cat_id):
            if not os.path.exists(it["path"]):
                self.remove_item(it["id"])
                removed += 1
        return removed

    def close(self):
        self.conn.close()
