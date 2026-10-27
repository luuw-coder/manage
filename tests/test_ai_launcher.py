import os
import tempfile
import unittest
from unittest import mock

from app import ai_launcher as al


class LauncherTests(unittest.TestCase):
    def test_build_command(self):
        cmd = al.build_command("C:\\chrome.exe", "https://grok.com", "D:\\p\\acc1", (500, 700), (900, 40))
        self.assertEqual(cmd[0], "C:\\chrome.exe")
        self.assertIn("--app=https://grok.com", cmd)
        self.assertIn("--user-data-dir=D:\\p\\acc1", cmd)
        self.assertIn("--window-size=500,700", cmd)
        self.assertIn("--window-position=900,40", cmd)
        self.assertNotIn("--window-position", " ".join(al.build_command("c", "u", "p")))

    def test_find_browser_prefers_installed_chrome(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            exe = os.path.join(tmp, "Google", "Chrome", "Application", "chrome.exe")
            os.makedirs(os.path.dirname(exe))
            open(exe, "w").close()
            with mock.patch.dict(os.environ, {"ProgramFiles": tmp, "ProgramFiles(x86)": "", "LocalAppData": ""}):
                self.assertEqual(al.find_browser(), exe)

    def test_launch_without_browser_reports_failure(self):
        with mock.patch.object(al, "find_browser", return_value=None):
            ok, msg = al.launch({"id": 1, "url": "https://x.y", "provider": "X", "label": "A"}, "p")
        self.assertFalse(ok)
        self.assertIn("Chrome", msg)

    def test_launch_uses_separate_profile_per_account(self):
        calls = []
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            with mock.patch.object(al, "find_browser", return_value="chrome"), \
                    mock.patch.object(al.subprocess, "Popen", side_effect=lambda cmd, **kw: calls.append(cmd)):
                for i in (1, 2):
                    ok, _ = al.launch({"id": i, "url": "https://x.y", "provider": "X", "label": "A"}, tmp)
                    self.assertTrue(ok)
        dirs = [c for cmd in calls for c in cmd if c.startswith("--user-data-dir=")]
        self.assertEqual(len(set(dirs)), 2)


if __name__ == "__main__":
    unittest.main()
