import os
import tempfile
import unittest

from app.db import DEFAULT_CATEGORIES, Database


class DbTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.path = os.path.join(self.tmp.name, "t.db")
        self.db = Database(self.path)

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def make(self, rel, text="x"):
        p = os.path.join(self.tmp.name, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(text)
        return p

    def names(self):
        return [c["name"] for c in self.db.categories()]

    def cid(self, name):
        return next(c["id"] for c in self.db.categories() if c["name"] == name)

    def test_default_categories_in_order(self):
        self.assertEqual(self.names(), [d[0] for d in DEFAULT_CATEGORIES])

    def test_default_flags(self):
        cats = {c["name"]: c for c in self.db.categories()}
        self.assertEqual(cats["Tất cả"]["kind"], "all")
        self.assertEqual(cats["Yêu thích"]["kind"], "fav")
        self.assertEqual(cats["Âm thanh"]["filters"], "")

    def test_not_reseeded_after_delete(self):
        for c in self.db.categories():
            self.db.delete_category(c["id"])
        self.db.close()
        self.db = Database(self.path)
        self.assertEqual(self.names(), [])

    def test_restore_defaults_only_missing(self):
        self.db.delete_category(self.cid("Video"))
        self.db.delete_category(self.cid("GIF"))
        self.assertEqual(self.db.restore_defaults(), 2)
        self.assertIn("Video", self.names())
        self.assertEqual(self.db.restore_defaults(), 0)

    def test_add_update_move_category(self):
        cid = self.db.add_category("Cảnh phim", icon="film", color="#fff")
        with self.assertRaises(ValueError):
            self.db.add_category("Cảnh phim")
        with self.assertRaises(ValueError):
            self.db.add_category("  ")
        self.db.update_category(cid, name="Tập 01", icon_image="x.png")
        c = self.db.category(cid)
        self.assertEqual((c["name"], c["icon_image"]), ("Tập 01", "x.png"))
        self.db.update_category(cid, icon_image=None)
        self.assertIsNone(self.db.category(cid)["icon_image"])
        self.db.move_category(cid, -2)
        self.assertEqual(self.names().index("Tập 01"), len(DEFAULT_CATEGORIES) - 2)
        with self.assertRaises(ValueError):
            self.db.update_category(cid, nope=1)

    def test_roots_dedupe_and_nonexistent(self):
        cid = self.cid("Nhân vật")
        folder = os.path.join(self.tmp.name, "chars")
        self.make("chars/a.png")
        self.assertEqual(self.db.add_roots(cid, [folder, folder, "Z:/khong/co"]), 1)
        self.assertEqual(len(self.db.roots(cid)), 1)

    def test_same_folder_in_many_categories_and_all_roots_dedupe(self):
        folder = os.path.join(self.tmp.name, "f")
        self.make("f/a.png")
        self.db.add_roots(self.cid("Nhân vật"), [folder])
        self.db.add_roots(self.cid("Ảnh"), [folder])
        self.assertEqual(len(self.db.all_roots()), 1)

    def test_prune_missing_roots_only_missing(self):
        cid = self.cid("Âm thanh")
        a, b = self.make("a.wav"), self.make("b.wav")
        self.db.add_roots(cid, [a, b])
        os.remove(a)
        self.assertEqual(self.db.prune_missing_roots(cid), 1)
        self.assertEqual([r["path"] for r in self.db.roots(cid)], [os.path.normpath(b)])

    def test_delete_category_never_deletes_files(self):
        a = self.make("keep/x.png")
        cid = self.cid("Ảnh")
        self.db.add_roots(cid, [os.path.dirname(a)])
        self.db.delete_category(cid)
        self.assertTrue(os.path.exists(a))

    def test_remove_root_path_and_everywhere(self):
        a = self.make("a.png")
        c1, c2 = self.cid("Ảnh"), self.cid("GIF")
        self.db.add_roots(c1, [a])
        self.db.add_roots(c2, [a])
        self.db.remove_root_path(c1, a)
        self.assertEqual(len(self.db.roots(c1)), 0)
        self.assertEqual(len(self.db.roots(c2)), 1)
        self.db.remove_root_everywhere(a)
        self.assertEqual(len(self.db.roots(c2)), 0)

    def test_meta_name_favorite_pin(self):
        a = self.make("character_003_final.png")
        self.db.set_display_name(a, "Nhân vật chính")
        self.db.set_favorite(a, True)
        self.db.set_pinned(a, True)
        m = self.db.meta_map([a])[os.path.normcase(os.path.normpath(a))]
        self.assertEqual((m["display_name"], m["favorite"], m["pinned"]), ("Nhân vật chính", 1, 1))
        self.assertEqual(self.db.favorites(), [os.path.normpath(a)])
        self.db.set_display_name(a, "   ")
        m = self.db.meta_map([a])[os.path.normcase(os.path.normpath(a))]
        self.assertIsNone(m["display_name"])

    def test_reset_names_keeps_favorite_and_pin(self):
        folder = os.path.join(self.tmp.name, "chars")
        a = self.make("chars/a.png")
        b = self.make("other/b.png")
        for p in (a, b):
            self.db.set_display_name(p, "Tên mới")
        self.db.set_favorite(a, True)
        self.assertEqual(self.db.reset_names([folder]), 1)
        mm = self.db.meta_map([a, b])
        ka, kb = (os.path.normcase(os.path.normpath(x)) for x in (a, b))
        self.assertIsNone(mm[ka]["display_name"])
        self.assertEqual(mm[ka]["favorite"], 1)
        self.assertEqual(mm[kb]["display_name"], "Tên mới")

    def test_settings_roundtrip(self):
        self.db.set_setting("page_size", 20)
        self.assertEqual(self.db.get_setting("page_size"), "20")

    def test_upgrade_from_step1_database(self):
        import sqlite3
        old = os.path.join(self.tmp.name, "old.db")
        c = sqlite3.connect(old)
        c.executescript("""
            CREATE TABLE categories(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE, position INTEGER NOT NULL DEFAULT 0);
            CREATE TABLE items(id INTEGER PRIMARY KEY AUTOINCREMENT, category_id INTEGER NOT NULL, path TEXT NOT NULL, display_name TEXT, added_at REAL NOT NULL, UNIQUE(category_id,path));
            CREATE TABLE settings(key TEXT PRIMARY KEY, value TEXT);
            INSERT INTO categories(name,position) VALUES('Âm thanh',1),('Nhân vật',2),('Ảnh',3),('GIF',4),('Cảnh phim',5);
            INSERT INTO settings VALUES('seeded','1');
        """)
        f = self.make("legacy/a.wav")
        c.execute("INSERT INTO items(category_id,path,added_at) VALUES(1,?,0)", (f,))
        c.commit()
        c.close()
        db = Database(old)
        names = [x["name"] for x in db.categories()]
        self.assertEqual(names[:len(DEFAULT_CATEGORIES)], [d[0] for d in DEFAULT_CATEGORIES])
        self.assertEqual(names[-1], "Cảnh phim")
        am = next(x for x in db.categories() if x["name"] == "Âm thanh")
        self.assertEqual(am["filters"], "")
        self.assertEqual([r["path"] for r in db.roots(am["id"])], [f])
        db.close()

    def test_upgrade_from_schema2_resets_old_default_filters_and_seeds_ai(self):
        self.db.update_category(self.cid("Âm thanh"), filters="audio")
        self.db.update_category(self.cid("Ảnh"), filters="image,vector")  # người dùng tự đặt: giữ nguyên
        self.db.set_setting("schema", 2)
        self.db.conn.execute("DELETE FROM ai_accounts")
        self.db.conn.commit()
        self.db.close()
        self.db = Database(self.path)
        cats = {c["name"]: c for c in self.db.categories()}
        self.assertEqual(cats["Âm thanh"]["filters"], "")
        self.assertEqual(cats["Ảnh"]["filters"], "image,vector")
        self.assertEqual([a["provider"] for a in self.db.ai_accounts()],
                         ["ChatGPT", "Gemini", "Claude", "Grok", "DeepSeek"])

    def test_ai_accounts_crud(self):
        n = len(self.db.ai_accounts())
        aid = self.db.add_ai_account("Qwen", "Tài khoản 2", "chat.qwen.ai")
        acc = next(a for a in self.db.ai_accounts() if a["id"] == aid)
        self.assertEqual(acc["url"], "https://chat.qwen.ai")
        with self.assertRaises(ValueError):
            self.db.add_ai_account("", "x", "https://a.b")
        self.db.update_ai_account(aid, "Qwen", "Công việc", "https://x.y")
        self.assertEqual(next(a for a in self.db.ai_accounts() if a["id"] == aid)["label"], "Công việc")
        self.db.delete_ai_account(aid)
        self.assertEqual(len(self.db.ai_accounts()), n)

    def test_versions(self):
        v1 = self.db.add_version("Tập 01", "Bản nháp", "abc")
        v2 = self.db.add_version("Tập 01", "", "abcd")
        self.assertEqual([v["id"] for v in self.db.versions("Tập 01")], [v2, v1])
        self.assertEqual(self.db.get_version(v1)["content"], "abc")
        self.db.rename_versions_of("Tập 01", "Tập 1")
        self.assertEqual(len(self.db.versions("Tập 1")), 2)
        self.db.delete_version(v1)
        self.db.delete_versions_of("Tập 1")
        self.assertEqual(self.db.versions("Tập 1"), [])

    def test_export_import_roundtrip(self):
        a = self.make("x/a.png")
        folder = os.path.dirname(a)
        cid = self.cid("Nhân vật")
        self.db.add_roots(cid, [folder])
        self.db.set_display_name(a, "Tên riêng")
        self.db.set_favorite(a, True)
        self.db.add_category("Cảnh phim", icon="film")
        self.db.set_setting("page_size", 40)
        self.db.add_version("S", "L", "nội dung")
        state = self.db.export_state()
        self.db.delete_category(cid)
        self.db.set_setting("page_size", 5)
        self.db.import_state(state)
        self.assertIn("Cảnh phim", self.names())
        self.assertEqual(len(self.db.roots(self.cid("Nhân vật"))), 1)
        m = self.db.meta_map([a])[os.path.normcase(os.path.normpath(a))]
        self.assertEqual((m["display_name"], m["favorite"]), ("Tên riêng", 1))
        self.assertEqual(self.db.get_setting("page_size"), "40")
        self.assertEqual(self.db.versions("S")[0]["label"], "L")
        self.assertEqual(self.db.get_setting("schema"), "3")


if __name__ == "__main__":
    unittest.main()
