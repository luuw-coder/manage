import os
import tempfile
import unittest

from app import fsbrowse as fb
from app.moho_bridge import is_moho_exe


class FsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.root = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def mk(self, rel):
        p = os.path.join(self.root, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w") as f:
            f.write("x")
        return p

    def test_parse_exts(self):
        self.assertEqual(fb.parse_exts("PNG, .jpg; gif  .PNG ."), [".png", ".jpg", ".gif"])
        self.assertEqual(fb.parse_exts(""), [])

    def test_groups_roundtrip_and_bad_json(self):
        g = fb.default_groups()
        g["x"] = ["Của tôi", [".abc"]]
        self.assertEqual(fb.groups_from_json(fb.groups_to_json(g))["x"], ["Của tôi", [".abc"]])
        self.assertIn("audio", fb.groups_from_json("không phải json"))
        self.assertIn(".m4a", fb.default_groups()["audio"][1])
        self.assertIn(".blend", fb.default_groups()["model3d"][1])

    def test_exts_for(self):
        g = fb.default_groups()
        self.assertIsNone(fb.exts_for(g, []))
        self.assertIsNone(fb.exts_for(g, ["khong_co"]))
        self.assertEqual(fb.exts_for(g, ["gif"]), {".gif", ".apng"})
        self.assertIn(".moho", fb.exts_for(g, ["project", "gif"]))

    def test_list_dir_shows_folders_always_and_filters_files(self):
        self.mk("a.wav")
        self.mk("b.png")
        self.mk("sub/c.wav")
        self.mk("Thumbs.db")
        items = fb.list_dir(self.root, {".wav"})
        names = sorted(i["name"] for i in items)
        self.assertEqual(names, ["a.wav", "sub"])
        self.assertEqual(len(fb.list_dir(self.root, None)), 3)

    def test_sort_pinned_then_folders_then_natural(self):
        items = [
            {"name": "file10.png", "is_dir": False, "mtime": 1, "size": 1, "ext": ".png"},
            {"name": "file2.png", "is_dir": False, "mtime": 2, "size": 5, "ext": ".png"},
            {"name": "zdir", "is_dir": True, "mtime": 3, "size": 0, "ext": ""},
            {"name": "pinned.png", "is_dir": False, "mtime": 0, "size": 9, "ext": ".png", "pinned": True},
        ]
        order = [i["name"] for i in fb.sort_items(list(items), "name")]
        self.assertEqual(order, ["pinned.png", "zdir", "file2.png", "file10.png"])
        order = [i["name"] for i in fb.sort_items(list(items), "size")]
        self.assertEqual(order[:2], ["pinned.png", "zdir"])
        self.assertEqual(order[2:], ["file2.png", "file10.png"])

    def test_pagination(self):
        items = list(range(25))
        part, page, pages = fb.page_slice(items, 0, 10)
        self.assertEqual((len(part), page, pages), (10, 0, 3))
        part, page, pages = fb.page_slice(items, 99, 10)
        self.assertEqual((len(part), page, pages), (5, 2, 3))
        self.assertEqual(fb.page_count(0, 10), 1)

    def test_page_buttons(self):
        self.assertEqual(fb.page_buttons(0, 3), [1, 2, 3])
        self.assertEqual(fb.page_buttons(0, 10), [1, 2, 3, 4, 5, "…", 10])
        self.assertEqual(fb.page_buttons(5, 10), [1, "…", 5, 6, 7, "…", 10])
        self.assertEqual(fb.page_buttons(9, 10), [1, "…", 6, 7, 8, 9, 10])

    def test_breadcrumb_and_root_of(self):
        a = os.path.join(self.root, "chars")
        deep = os.path.join(a, "x", "y")
        bc = fb.breadcrumb(deep, a)
        self.assertEqual([n for n, _ in bc], ["chars", "x", "y"])
        self.assertEqual(fb.root_of(deep, [self.root, a]), a)
        self.assertIsNone(fb.root_of("Z:\\khac", [a]))
        self.assertTrue(fb.is_within(deep, a))
        self.assertFalse(fb.is_within(a + "2", a))

    def test_deep_search(self):
        self.mk("a/boss_theme.wav")
        self.mk("a/b/boss.png")
        self.mk("c/other.wav")
        res, trunc = fb.deep_search([self.root], "boss", {".wav"})
        self.assertEqual([r["name"] for r in res], ["boss_theme.wav"])
        self.assertFalse(trunc)
        res, _ = fb.deep_search([self.root], "boss", None)
        self.assertEqual(len(res), 2)

    def test_human_size(self):
        self.assertEqual(fb.human_size(0), "0 B")
        self.assertEqual(fb.human_size(1536), "1.5 KB")

    def test_is_moho_exe(self):
        self.assertTrue(is_moho_exe("C:\\Program Files\\Moho 14\\Moho.exe"))
        self.assertTrue(is_moho_exe("C:/x/MohoPro.exe"))
        self.assertFalse(is_moho_exe("C:\\x\\ManageMoho.exe"))
        self.assertFalse(is_moho_exe("C:\\x\\notepad.exe"))
        self.assertFalse(is_moho_exe(""))

    def test_many_formats_present(self):
        g = fb.default_groups()
        for ext in (".webm", ".wmv", ".m4v", ".mpeg", ".ts"):
            self.assertIn(ext, g["video"][1])
        for ext in (".aac", ".wma", ".opus", ".aiff"):
            self.assertIn(ext, g["audio"][1])
        for ext in (".tif", ".heic", ".tga", ".kra"):
            self.assertIn(ext, g["image"][1])
        for ext in (".dae", ".ply", ".usdz"):
            self.assertIn(ext, g["model3d"][1])
        self.assertGreaterEqual(len(g["video"][1]), 15)

    def test_merge_default_groups_keeps_user_changes(self):
        old = {"video": ["Video", [".mp4", ".xyz"]], "mine": ["Của tôi", [".abc"]]}
        merged = fb.merge_default_groups(old)
        self.assertIn(".xyz", merged["video"][1])
        self.assertIn(".webm", merged["video"][1])
        self.assertEqual(merged["mine"], ["Của tôi", [".abc"]])
        self.assertIn("audio", merged)

    def test_media_kind(self):
        self.assertEqual(fb.media_kind(".GIF"), "gif")
        self.assertEqual(fb.media_kind(".mkv"), "video")
        self.assertEqual(fb.media_kind(".flac"), "audio")
        self.assertEqual(fb.media_kind(".png"), "image")
        self.assertEqual(fb.media_kind(".glb"), "model3d")
        self.assertEqual(fb.media_kind(".moho"), "other")

    def test_folder_summary(self):
        self.mk("d/a.png")
        self.mk("d/b.txt")
        self.mk("d/sub/c.png")
        s = fb.folder_summary(os.path.join(self.root, "d"))
        self.assertEqual((s["files"], s["dirs"], len(s["images"])), (2, 1, 1))
        self.assertTrue(fb.folder_summary(os.path.join(self.root, "none"))["error"])


if __name__ == "__main__":
    unittest.main()
