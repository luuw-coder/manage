"""Cơ sở dữ liệu SQLite của Manage Moho.

Nguyên tắc: chỉ lưu LIÊN KẾT tới thư mục/tệp. Không bao giờ xóa/đổi tên/di chuyển tệp thật.
"""
import os
import sqlite3
import time

from .ai_presets import PRESETS, SEED_COUNT
from .fsbrowse import is_within, pkey

SCHEMA = 3

# (tên, biểu tượng, màu, loại, bộ lọc nhóm đuôi tệp)
DEFAULT_CATEGORIES = [
    ("Tất cả", "stack", "#35c3e8", "all", ""),
    ("Nhân vật", "user", "#ff6b6b", "normal", ""),
    ("Âm thanh", "music", "#ffa94d", "normal", ""),
    ("Ảnh", "image", "#b197fc", "normal", ""),
    ("GIF", "gif", "#51cf66", "normal", ""),
    ("Video", "film", "#f783ac", "normal", ""),
    ("Model 3D", "cube", "#74c0fc", "normal", ""),
    ("Dự án", "clapper", "#ffd8a8", "normal", ""),
    ("Vector", "pen", "#63e6be", "normal", ""),
    ("Tài liệu", "doc", "#adb5bd", "normal", ""),
    ("Yêu thích", "heart", "#ffd43b", "fav", ""),
]
CAT_FIELDS = "id,name,kind,icon,icon_image,color,filters"
OLD_DEFAULT_FILTERS = {"Âm thanh": "audio", "Ảnh": "image", "GIF": "gif", "Video": "video",
                       "Model 3D": "model3d", "Dự án": "project", "Vector": "vector", "Tài liệu": "doc"}


class Database:
    def __init__(self, path):
        self.path = path
        folder = os.path.dirname(path)
        if folder:
            os.makedirs(folder, exist_ok=True)
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys=ON")
        self._create()
        self._ensure_columns()
        self._upgrade()

    # ------------------------------------------------------------ khởi tạo / nâng cấp
    def _create(self):
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS categories(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                position INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS roots(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
                path TEXT NOT NULL,
                added_at REAL NOT NULL,
                UNIQUE(category_id, path)
            );
            CREATE TABLE IF NOT EXISTS meta(
                key TEXT PRIMARY KEY,
                path TEXT NOT NULL,
                display_name TEXT,
                favorite INTEGER NOT NULL DEFAULT 0,
                pinned INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS ai_accounts(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                provider TEXT NOT NULL,
                label TEXT NOT NULL,
                url TEXT NOT NULL,
                position INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS script_versions(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                script TEXT NOT NULL,
                label TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS settings(
                key TEXT PRIMARY KEY,
                value TEXT
            );
            """
        )
        self.conn.commit()

    def _ensure_columns(self):
        have = {r["name"] for r in self.conn.execute("PRAGMA table_info(categories)")}
        add = {
            "kind": "TEXT NOT NULL DEFAULT 'normal'",
            "icon": "TEXT NOT NULL DEFAULT 'folder'",
            "icon_image": "TEXT",
            "color": "TEXT NOT NULL DEFAULT '#74c0fc'",
            "filters": "TEXT NOT NULL DEFAULT ''",
        }
        for col, decl in add.items():
            if col not in have:
                self.conn.execute(f"ALTER TABLE categories ADD COLUMN {col} {decl}")
        self.conn.commit()

    def _upgrade(self):
        cur = int(self.get_setting("schema", "0") or 0)
        if cur >= SCHEMA:
            return
        if cur < 2:
            # bản cũ (bước 1) lưu từng tệp trong bảng items -> chuyển thành "gốc" của mục
            try:
                for r in self.conn.execute("SELECT category_id,path FROM items").fetchall():
                    self.conn.execute(
                        "INSERT OR IGNORE INTO roots(category_id,path,added_at) VALUES(?,?,?)",
                        (r["category_id"], r["path"], time.time()))
            except sqlite3.OperationalError:
                pass
            for name, icon, color, kind, filters in DEFAULT_CATEGORIES:
                row = self.conn.execute("SELECT id FROM categories WHERE name=?", (name,)).fetchone()
                if row:
                    self.conn.execute(
                        "UPDATE categories SET kind=?,icon=?,color=?,filters=? WHERE id=?",
                        (kind, icon, color, filters, row["id"]))
                else:
                    self._insert_category(name, icon, color, None, kind, filters)
            # sắp lại: mục mặc định theo thứ tự mặc định, mục tự tạo đứng sau
            order = {n: i for i, (n, *_r) in enumerate(DEFAULT_CATEGORIES)}
            rows = self.conn.execute("SELECT id,name,position FROM categories").fetchall()
            rows.sort(key=lambda r: (order.get(r["name"], 1000), r["position"], r["id"]))
            for i, r in enumerate(rows, 1):
                self.conn.execute("UPDATE categories SET position=? WHERE id=?", (i, r["id"]))
        if cur < 3:
            # bộ lọc định dạng mặc định giờ là "tất cả": bỏ bộ lọc cũ do phần mềm tự đặt
            for name, old in OLD_DEFAULT_FILTERS.items():
                self.conn.execute("UPDATE categories SET filters='' WHERE name=? AND filters=?", (name, old))
            if not self.conn.execute("SELECT 1 FROM ai_accounts LIMIT 1").fetchone():
                for i, (prov, url) in enumerate(PRESETS[:SEED_COUNT], 1):
                    self.conn.execute(
                        "INSERT INTO ai_accounts(provider,label,url,position) VALUES(?,?,?,?)",
                        (prov, "Tài khoản 1", url, i))
        self.conn.commit()
        self.set_setting("schema", SCHEMA)

    def _insert_category(self, name, icon, color, icon_image, kind, filters):
        pos = self.conn.execute("SELECT COALESCE(MAX(position),0)+1 FROM categories").fetchone()[0]
        cur = self.conn.execute(
            "INSERT INTO categories(name,position,kind,icon,icon_image,color,filters) VALUES(?,?,?,?,?,?,?)",
            (name, pos, kind, icon, icon_image, color, filters))
        return cur.lastrowid

    # ------------------------------------------------------------ cài đặt
    def get_setting(self, key, default=None):
        row = self.conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return row["value"] if row else default

    def set_setting(self, key, value):
        self.conn.execute(
            "INSERT INTO settings(key,value) VALUES(?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, str(value)))
        self.conn.commit()

    # ------------------------------------------------------------ mục
    def categories(self):
        return [dict(r) for r in self.conn.execute(
            f"SELECT {CAT_FIELDS} FROM categories ORDER BY position,id")]

    def category(self, cat_id):
        row = self.conn.execute(f"SELECT {CAT_FIELDS} FROM categories WHERE id=?", (cat_id,)).fetchone()
        return dict(row) if row else None

    def add_category(self, name, icon="folder", color="#74c0fc", icon_image=None, kind="normal", filters=""):
        name = (name or "").strip()
        if not name:
            raise ValueError("Tên mục không được để trống")
        try:
            cid = self._insert_category(name, icon, color, icon_image, kind, filters)
        except sqlite3.IntegrityError:
            raise ValueError("Đã có mục tên này")
        self.conn.commit()
        return cid

    def update_category(self, cat_id, **fields):
        allowed = {"name", "icon", "icon_image", "color", "filters"}
        bad = set(fields) - allowed
        if bad:
            raise ValueError(f"Trường không hợp lệ: {bad}")
        if "name" in fields:
            fields["name"] = (fields["name"] or "").strip()
            if not fields["name"]:
                raise ValueError("Tên mục không được để trống")
        if not fields:
            return
        sets = ",".join(f"{k}=?" for k in fields)
        try:
            self.conn.execute(f"UPDATE categories SET {sets} WHERE id=?", (*fields.values(), cat_id))
        except sqlite3.IntegrityError:
            raise ValueError("Đã có mục tên này")
        self.conn.commit()

    def rename_category(self, cat_id, name):
        self.update_category(cat_id, name=name)

    def delete_category(self, cat_id):
        """Xóa mục và danh sách trong mục. KHÔNG đụng tới tệp thật."""
        self.conn.execute("DELETE FROM categories WHERE id=?", (cat_id,))
        self.conn.commit()

    def move_category(self, cat_id, delta):
        ids = [c["id"] for c in self.categories()]
        if cat_id not in ids:
            return
        i = ids.index(cat_id)
        j = min(max(0, i + delta), len(ids) - 1)
        ids.insert(j, ids.pop(i))
        for pos, cid in enumerate(ids, 1):
            self.conn.execute("UPDATE categories SET position=? WHERE id=?", (pos, cid))
        self.conn.commit()

    def restore_defaults(self):
        """Thêm lại các mục mặc định đã bị xóa. Trả về số mục được thêm."""
        added = 0
        for name, icon, color, kind, filters in DEFAULT_CATEGORIES:
            if not self.conn.execute("SELECT 1 FROM categories WHERE name=?", (name,)).fetchone():
                self._insert_category(name, icon, color, None, kind, filters)
                added += 1
        self.conn.commit()
        return added

    # ------------------------------------------------------------ thư mục/tệp gốc của mục
    def roots(self, cat_id):
        return [dict(r) for r in self.conn.execute(
            "SELECT id,path FROM roots WHERE category_id=? ORDER BY id", (cat_id,))]

    def all_roots(self):
        seen, out = set(), []
        for r in self.conn.execute(
                "SELECT r.id,r.path FROM roots r JOIN categories c ON c.id=r.category_id "
                "ORDER BY c.position,r.id"):
            k = pkey(r["path"])
            if k not in seen:
                seen.add(k)
                out.append(dict(r))
        return out

    def add_roots(self, cat_id, paths):
        """Thêm thư mục hoặc tệp vào mục (chỉ lưu liên kết). Trả về số mục mới."""
        existing = {pkey(r["path"]) for r in self.roots(cat_id)}
        added = 0
        for p in paths:
            if not p or not os.path.exists(p):
                continue
            p = os.path.normpath(p)
            if pkey(p) in existing:
                continue
            self.conn.execute("INSERT INTO roots(category_id,path,added_at) VALUES(?,?,?)",
                              (cat_id, p, time.time()))
            existing.add(pkey(p))
            added += 1
        self.conn.commit()
        return added

    def remove_root(self, root_id):
        self.conn.execute("DELETE FROM roots WHERE id=?", (root_id,))
        self.conn.commit()

    def remove_root_path(self, cat_id, path):
        k = pkey(path)
        for r in self.roots(cat_id):
            if pkey(r["path"]) == k:
                self.remove_root(r["id"])

    def remove_root_everywhere(self, path):
        k = pkey(path)
        for r in self.conn.execute("SELECT id,path FROM roots").fetchall():
            if pkey(r["path"]) == k:
                self.conn.execute("DELETE FROM roots WHERE id=?", (r["id"],))
        self.conn.commit()

    def prune_missing_roots(self, cat_id=None):
        """Bỏ khỏi danh sách những gốc không còn trên máy. Trả về số mục bỏ."""
        q = "SELECT id,path FROM roots" + (" WHERE category_id=?" if cat_id is not None else "")
        rows = self.conn.execute(q, (cat_id,) if cat_id is not None else ()).fetchall()
        removed = 0
        for r in rows:
            if not os.path.exists(r["path"]):
                self.conn.execute("DELETE FROM roots WHERE id=?", (r["id"],))
                removed += 1
        self.conn.commit()
        return removed

    # ------------------------------------------------------------ tên hiển thị / yêu thích / ghim
    def meta_map(self, paths):
        keys = list({pkey(p) for p in paths})
        out = {}
        for i in range(0, len(keys), 500):
            chunk = keys[i:i + 500]
            marks = ",".join("?" * len(chunk))
            for r in self.conn.execute(
                    f"SELECT key,display_name,favorite,pinned FROM meta WHERE key IN ({marks})", chunk):
                out[r["key"]] = dict(r)
        return out

    def _upsert(self, path, **fields):
        key = pkey(path)
        self.conn.execute("INSERT OR IGNORE INTO meta(key,path) VALUES(?,?)", (key, os.path.normpath(path)))
        for col, val in fields.items():
            self.conn.execute(f"UPDATE meta SET {col}=? WHERE key=?", (val, key))
        self.conn.commit()

    def set_display_name(self, path, name):
        name = (name or "").strip() or None
        self._upsert(path, display_name=name)

    def set_favorite(self, path, on):
        self._upsert(path, favorite=1 if on else 0)

    def set_pinned(self, path, on):
        self._upsert(path, pinned=1 if on else 0)

    def favorites(self):
        return [r["path"] for r in self.conn.execute("SELECT path FROM meta WHERE favorite=1 ORDER BY path")]

    def reset_names(self, paths):
        """Đưa tên hiển thị về tên tệp gốc cho các đường dẫn (và mọi thứ bên trong). Trả về số tên đã đặt lại."""
        cleared = 0
        rows = self.conn.execute("SELECT key,path FROM meta WHERE display_name IS NOT NULL").fetchall()
        for r in rows:
            if any(is_within(r["path"], p) for p in paths):
                self.conn.execute("UPDATE meta SET display_name=NULL WHERE key=?", (r["key"],))
                cleared += 1
        self.conn.commit()
        return cleared

    # ------------------------------------------------------------ tài khoản AI
    def ai_accounts(self):
        return [dict(r) for r in self.conn.execute(
            "SELECT id,provider,label,url FROM ai_accounts ORDER BY position,id")]

    def add_ai_account(self, provider, label, url):
        provider, label, url = (provider or "").strip(), (label or "").strip(), (url or "").strip()
        if not provider or not url:
            raise ValueError("Cần tên AI và địa chỉ trang web")
        if not url.lower().startswith(("http://", "https://")):
            url = "https://" + url
        pos = self.conn.execute("SELECT COALESCE(MAX(position),0)+1 FROM ai_accounts").fetchone()[0]
        cur = self.conn.execute("INSERT INTO ai_accounts(provider,label,url,position) VALUES(?,?,?,?)",
                                (provider, label or "Tài khoản", url, pos))
        self.conn.commit()
        return cur.lastrowid

    def update_ai_account(self, acc_id, provider, label, url):
        url = (url or "").strip()
        if url and not url.lower().startswith(("http://", "https://")):
            url = "https://" + url
        self.conn.execute("UPDATE ai_accounts SET provider=?,label=?,url=? WHERE id=?",
                          ((provider or "").strip(), (label or "").strip() or "Tài khoản", url, acc_id))
        self.conn.commit()

    def delete_ai_account(self, acc_id):
        self.conn.execute("DELETE FROM ai_accounts WHERE id=?", (acc_id,))
        self.conn.commit()

    # ------------------------------------------------------------ phiên bản kịch bản
    def add_version(self, script, label, content):
        cur = self.conn.execute(
            "INSERT INTO script_versions(script,label,content,created_at) VALUES(?,?,?,?)",
            (script, (label or "").strip() or "Phiên bản", content, time.time()))
        self.conn.commit()
        return cur.lastrowid

    def versions(self, script):
        return [dict(r) for r in self.conn.execute(
            "SELECT id,label,created_at FROM script_versions WHERE script=? ORDER BY id DESC", (script,))]

    def get_version(self, ver_id):
        row = self.conn.execute(
            "SELECT id,script,label,content,created_at FROM script_versions WHERE id=?", (ver_id,)).fetchone()
        return dict(row) if row else None

    def delete_version(self, ver_id):
        self.conn.execute("DELETE FROM script_versions WHERE id=?", (ver_id,))
        self.conn.commit()

    def delete_versions_of(self, script):
        self.conn.execute("DELETE FROM script_versions WHERE script=?", (script,))
        self.conn.commit()

    def rename_versions_of(self, old, new):
        self.conn.execute("UPDATE script_versions SET script=? WHERE script=?", (new, old))
        self.conn.commit()

    # ------------------------------------------------------------ sao lưu / khôi phục
    def export_state(self):
        cats = []
        for c in self.categories():
            cats.append({"name": c["name"], "kind": c["kind"], "icon": c["icon"], "icon_image": c["icon_image"],
                         "color": c["color"], "filters": c["filters"],
                         "roots": [r["path"] for r in self.roots(c["id"])]})
        meta = [dict(r) for r in self.conn.execute("SELECT path,display_name,favorite,pinned FROM meta")]
        settings = {r["key"]: r["value"] for r in self.conn.execute("SELECT key,value FROM settings")
                    if r["key"] not in ("schema", "geometry")}
        versions = [dict(r) for r in self.conn.execute(
            "SELECT script,label,content,created_at FROM script_versions ORDER BY id")]
        return {"version": 1, "categories": cats, "meta": meta, "settings": settings,
                "ai_accounts": self.ai_accounts(), "script_versions": versions}

    def import_state(self, state):
        """Thay toàn bộ mục, tên hiển thị, cài đặt, tài khoản AI bằng dữ liệu sao lưu."""
        c = self.conn
        try:
            c.execute("DELETE FROM roots")
            c.execute("DELETE FROM categories")
            c.execute("DELETE FROM meta")
            c.execute("DELETE FROM ai_accounts")
            c.execute("DELETE FROM script_versions")
            for pos, cat in enumerate(state.get("categories", []), 1):
                cur = c.execute(
                    "INSERT INTO categories(name,position,kind,icon,icon_image,color,filters) VALUES(?,?,?,?,?,?,?)",
                    (cat["name"], pos, cat.get("kind", "normal"), cat.get("icon", "folder"), cat.get("icon_image"),
                     cat.get("color", "#74c0fc"), cat.get("filters", "")))
                for p in cat.get("roots", []):
                    c.execute("INSERT OR IGNORE INTO roots(category_id,path,added_at) VALUES(?,?,?)",
                              (cur.lastrowid, p, time.time()))
            for m in state.get("meta", []):
                c.execute("INSERT OR REPLACE INTO meta(key,path,display_name,favorite,pinned) VALUES(?,?,?,?,?)",
                          (pkey(m["path"]), m["path"], m.get("display_name"), int(m.get("favorite", 0)),
                           int(m.get("pinned", 0))))
            for k, v in state.get("settings", {}).items():
                c.execute("INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                          (k, v))
            for i, a in enumerate(state.get("ai_accounts", []), 1):
                c.execute("INSERT INTO ai_accounts(provider,label,url,position) VALUES(?,?,?,?)",
                          (a["provider"], a["label"], a["url"], i))
            for v in state.get("script_versions", []):
                c.execute("INSERT INTO script_versions(script,label,content,created_at) VALUES(?,?,?,?)",
                          (v["script"], v["label"], v["content"], v.get("created_at", time.time())))
            c.commit()
        except Exception:
            c.rollback()
            raise

    def close(self):
        self.conn.close()
