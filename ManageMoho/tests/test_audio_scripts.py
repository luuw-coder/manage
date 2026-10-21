import array
import math
import os
import tempfile
import unittest
import wave

from app import audio_tools as at
from app.backup import load_backup_file, make_backup, restore_backup, save_backup_file
from app import drag_log
from app.db import Database
from app.scripts_store import ScriptStore, sanitize_name


def make_wav(path, seconds=2.0, rate=8000, channels=1, width=2):
    n = int(seconds * rate)
    frames = bytearray()
    for i in range(n):
        v = int(12000 * math.sin(2 * math.pi * 440 * i / rate))
        for _ in range(channels):
            if width == 2:
                frames += int(v).to_bytes(2, "little", signed=True)
            elif width == 1:
                frames += bytes([(v >> 8) + 128])
            elif width == 3:
                frames += (v << 8).to_bytes(3, "little", signed=True)
            elif width == 4:
                frames += (v << 16).to_bytes(4, "little", signed=True)
    with wave.open(path, "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(width)
        w.setframerate(rate)
        w.writeframes(bytes(frames))


class AudioTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)

    def tearDown(self):
        self.tmp.cleanup()

    def p(self, name):
        return os.path.join(self.tmp.name, name)

    def test_read_wav_all_widths_and_channels(self):
        for width in (1, 2, 3, 4):
            for ch in (1, 2):
                path = self.p(f"w{width}{ch}.wav")
                make_wav(path, 0.5, 8000, ch, width)
                pcm = at.read_wav(path)
                self.assertEqual((pcm.rate, pcm.channels, pcm.frames), (8000, ch, 4000))
                self.assertGreater(max(pcm.mono()), 8000)

    def test_slice_and_export_do_not_touch_original(self):
        src = self.p("a.wav")
        make_wav(src, 2.0, 8000, 2)
        before = open(src, "rb").read()
        pcm = at.load_pcm(src)
        out = at.export_segment(pcm, 0.5, 1.25, self.p("exports"), src)
        self.assertTrue(os.path.exists(out))
        seg = at.read_wav(out)
        self.assertEqual((seg.rate, seg.channels, seg.frames), (8000, 2, 6000))
        self.assertAlmostEqual(seg.duration, 0.75, places=3)
        self.assertEqual(open(src, "rb").read(), before)
        self.assertEqual(pcm.frames, 16000)

    def test_export_reversed_range_and_unique_names(self):
        src = self.p("a.wav")
        make_wav(src, 1.0)
        pcm = at.load_pcm(src)
        a = at.export_segment(pcm, 0.6, 0.2, self.p("e"), src)
        b = at.export_segment(pcm, 0.2, 0.6, self.p("e"), src)
        self.assertNotEqual(a, b)
        self.assertAlmostEqual(at.read_wav(a).duration, 0.4, places=3)
        with self.assertRaises(ValueError):
            at.export_segment(pcm, 0.3, 0.3, self.p("e"), src)

    def test_peaks_columns(self):
        src = self.p("a.wav")
        make_wav(src, 3.0)
        pcm = at.load_pcm(src)
        mono = pcm.mono()
        pk = at.Peaks(mono)
        cols = at.column_peaks(mono, pk, 0, pcm.frames, 100)
        self.assertEqual(len(cols), 100)
        self.assertTrue(all(lo <= hi for lo, hi in cols))
        self.assertGreater(max(hi for _lo, hi in cols), 10000)
        zoom = at.column_peaks(mono, pk, 100, 200, 50)
        self.assertEqual(len(zoom), 50)
        beyond = at.column_peaks(mono, pk, pcm.frames + 10, pcm.frames + 20, 4)
        self.assertEqual(beyond, [(0, 0)] * 4)

    def test_fmt_time(self):
        self.assertEqual(at.fmt_time(65.5), "01:05.500")

    def test_bad_wav_gives_value_error_and_none(self):
        bad = self.p("bad.wav")
        open(bad, "wb").write(b"not a wav")
        with self.assertRaises(ValueError):
            at.read_wav(bad)
        self.assertIsNone(at.load_pcm(bad))


class ScriptTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.store = ScriptStore(os.path.join(self.tmp.name, "scripts"))

    def tearDown(self):
        self.tmp.cleanup()

    def test_create_write_read_vietnamese(self):
        n = self.store.create()
        self.assertEqual(n, "Kịch bản 1")
        self.assertEqual(self.store.create(), "Kịch bản 2")
        self.store.write(n, "CẢNH 1\nBÉ NA\nMèo ơi!\n")
        self.assertEqual(self.store.read(n), "CẢNH 1\nBÉ NA\nMèo ơi!\n")
        self.assertEqual(self.store.list(), ["Kịch bản 1", "Kịch bản 2"])
        self.assertTrue(open(self.store.path(n), "rb").read().startswith(b"\xef\xbb\xbf"))

    def test_rename_duplicate_delete(self):
        n = self.store.create()
        self.store.write(n, "x")
        new = self.store.rename(n, "Tập 01: Mở đầu?")
        self.assertEqual(new, "Tập 01_ Mở đầu_")
        with self.assertRaises(ValueError):
            self.store.rename(new, "  ")
        other = self.store.create()
        with self.assertRaises(ValueError):
            self.store.rename(other, new)
        dup = self.store.duplicate(new)
        self.assertEqual(self.store.read(dup), "x")
        self.store.delete(dup)
        self.assertNotIn(dup, self.store.list())

    def test_import_file(self):
        src = os.path.join(self.tmp.name, "ngoai.txt")
        with open(src, "w", encoding="utf-8") as f:
            f.write("xin chào")
        name = self.store.import_file(src)
        self.assertEqual(self.store.read(name), "xin chào")
        self.assertEqual(self.store.import_file(src), "ngoai 2")

    def test_html_sidecar_roundtrip_and_cleanup(self):
        n = self.store.create()
        self.store.write(n, "đỏ", "<p style='color:#ff0000'>đỏ</p>")
        self.assertEqual(self.store.read(n), "đỏ")
        self.assertIn("ff0000", self.store.read_html(n))
        self.assertEqual(self.store.list(), [n])  # .txt và .html chỉ tính là một kịch bản
        dup = self.store.duplicate(n)
        self.assertIn("ff0000", self.store.read_html(dup))
        new = self.store.rename(n, "Tập 2")
        self.assertTrue(os.path.exists(self.store.path(new, ".html")))
        self.store.write(new, "chữ thuần")  # ghi lại không kèm html thì bỏ bản html cũ
        self.assertIsNone(self.store.read_html(new))
        self.store.delete(dup)
        self.assertFalse(os.path.exists(self.store.path(dup, ".html")))

    def test_html_only_script_still_listed(self):
        open(self.store.path("chi_html", ".html"), "w").write("<p>x</p>")
        self.assertIn("chi_html", self.store.list())

    def test_sanitize(self):
        self.assertEqual(sanitize_name('a/b\\c:d'), "a_b_c_d")
        self.assertEqual(sanitize_name("..."), "")

    def test_backup_roundtrip_with_scripts(self):
        db = Database(os.path.join(self.tmp.name, "t.db"))
        self.store.write("K1", "nội dung 1", "<p style='color:#00ff00'>nội dung 1</p>")
        db.set_setting("page_size", 33)
        state = make_backup(db, self.store)
        path = os.path.join(self.tmp.name, "backup.json")
        save_backup_file(path, state)
        self.store.write("K1", "đã bị sửa")
        db.set_setting("page_size", 5)
        restore_backup(db, self.store, load_backup_file(path))
        self.assertEqual(self.store.read("K1"), "nội dung 1")
        self.assertIn("00ff00", self.store.read_html("K1"))
        self.assertEqual(db.get_setting("page_size"), "33")
        bad = os.path.join(self.tmp.name, "bad.json")
        open(bad, "w").write('{"a": 1}')
        with self.assertRaises(ValueError):
            load_backup_file(bad)
        db.close()


class DragLogTests(unittest.TestCase):
    def test_log_lines_and_ignore_does_not_raise_moho(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            front = drag_log.after_drag(tmp, ["D:\\hoạt hình\\cười.mp3"], "Ignore", 120, False)
            self.assertFalse(front)
            drag_log.after_drag(tmp, ["a.wav", "b.wav"], "Copy", 900, True)
            lines = open(drag_log.log_path(tmp), encoding="utf-8").read().splitlines()
            self.assertEqual(len(lines), 3)
            self.assertIn("| Ignore |", lines[0])
            self.assertIn("cười.mp3", lines[0])
            self.assertIn("luon_noi=true", lines[1])

    def test_log_is_trimmed_when_big(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            p = drag_log.log_path(tmp)
            open(p, "w", encoding="utf-8").write(("x" * 100 + "\n") * 3000)
            drag_log.append(tmp, "moi")
            lines = open(p, encoding="utf-8").read().splitlines()
            self.assertLessEqual(len(lines), 502)
            self.assertEqual(lines[-1], "moi")


if __name__ == "__main__":
    unittest.main()
