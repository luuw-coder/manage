import os
import tempfile
import unittest

from app.db import Database


class DbTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Database(os.path.join(self.tmp.name, "t.db"))

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def make(self, name, text="x"):
        p = os.path.join(self.tmp.name, name)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w") as f:
            f.write(text)
        return p

    def test_default_categories(self):
        self.assertEqual([c["name"] for c in self.db.categories()],
                         ["Âm thanh", "Nhân vật", "Ảnh", "GIF"])

    def test_seed_only_once(self):
        for c in self.db.categories():
            self.db.delete_category(c["id"])
        path = os.path.join(self.tmp.name, "t.db")
        db2 = Database(path)
        self.assertEqual(db2.categories(), [])
        db2.close()

    def test_add_rename_delete_category(self):
        cid = self.db.add_category("Cảnh phim")
        with self.assertRaises(ValueError):
            self.db.add_category("Cảnh phim")
        with self.assertRaises(ValueError):
            self.db.add_category("  ")
        self.db.rename_category(cid, "Tập 01")
        self.assertIn("Tập 01", [c["name"] for c in self.db.categories()])
        self.db.delete_category(cid)
        self.assertNotIn("Tập 01", [c["name"] for c in self.db.categories()])

    def test_add_files_and_folder_no_duplicates(self):
        cid = self.db.categories()[1]["id"]
        a = self.make("a.png")
        self.make("sub/b.png")
        self.make("sub/deep/c.png")
        self.assertEqual(self.db.add_items(cid, [a]), 1)
        self.assertEqual(self.db.add_items(cid, [a]), 0)
        self.assertEqual(self.db.add_items(cid, [os.path.join(self.tmp.name, "sub")]), 2)
        self.assertEqual(len(self.db.items(cid)), 3)

    def test_same_file_in_many_categories(self):
        c1, c2 = [c["id"] for c in self.db.categories()[:2]]
        a = self.make("a.png")
        self.db.add_items(c1, [a])
        self.db.add_items(c2, [a])
        self.assertEqual(len(self.db.items(c1)), 1)
        self.assertEqual(len(self.db.items(c2)), 1)

    def test_prune_missing_removes_only_missing(self):
        cid = self.db.categories()[0]["id"]
        a, b = self.make("a.wav"), self.make("b.wav")
        self.db.add_items(cid, [a, b])
        os.remove(a)
        self.assertEqual(self.db.prune_missing(cid), 1)
        self.assertEqual([i["path"] for i in self.db.items(cid)], [os.path.normpath(b)])

    def test_delete_category_never_deletes_real_files(self):
        cid = self.db.categories()[0]["id"]
        a = self.make("keep.png")
        self.db.add_items(cid, [a])
        self.db.delete_category(cid)
        self.assertTrue(os.path.exists(a))

    def test_nonexistent_path_ignored(self):
        cid = self.db.categories()[0]["id"]
        self.assertEqual(self.db.add_items(cid, ["Z:/khong/ton/tai.png"]), 0)

    def test_settings_roundtrip(self):
        self.db.set_setting("opacity", 55)
        self.assertEqual(self.db.get_setting("opacity"), "55")
        self.db.set_setting("opacity", 70)
        self.assertEqual(self.db.get_setting("opacity"), "70")


if __name__ == "__main__":
    unittest.main()
