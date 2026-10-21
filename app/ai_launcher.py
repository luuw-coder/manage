"""Mở AI bằng cửa sổ riêng gọn (Chrome/Edge có sẵn trong máy), mỗi tài khoản một phiên đăng nhập riêng."""
import os
import shutil
import subprocess
import sys


def find_browser():
    env = os.environ
    pf = env.get("ProgramFiles", r"C:\Program Files")
    pf86 = env.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
    local = env.get("LocalAppData", "")
    cands = [
        os.path.join(pf, "Google", "Chrome", "Application", "chrome.exe"),
        os.path.join(pf86, "Google", "Chrome", "Application", "chrome.exe"),
        os.path.join(local, "Google", "Chrome", "Application", "chrome.exe") if local else "",
        os.path.join(pf86, "Microsoft", "Edge", "Application", "msedge.exe"),
        os.path.join(pf, "Microsoft", "Edge", "Application", "msedge.exe"),
    ]
    for c in cands:
        if c and os.path.exists(c):
            return c
    for name in ("chrome", "msedge", "google-chrome", "chromium"):
        w = shutil.which(name)
        if w:
            return w
    return None


def build_command(browser, url, profile_dir, size=(520, 760), pos=None):
    cmd = [browser, f"--app={url}", f"--user-data-dir={profile_dir}", "--no-first-run",
           "--no-default-browser-check", f"--window-size={size[0]},{size[1]}"]
    if pos:
        cmd.append(f"--window-position={pos[0]},{pos[1]}")
    return cmd


def launch(account, profiles_dir, size=(520, 760), pos=None):
    """Trả về (thành công, thông báo). Thất bại nghĩa là chưa tìm thấy Chrome/Edge."""
    browser = find_browser()
    if not browser:
        return False, "Chưa tìm thấy Chrome hoặc Edge trong máy."
    profile = os.path.join(profiles_dir, f"acc{account['id']}")
    os.makedirs(profile, exist_ok=True)
    flags = 0
    if sys.platform == "win32":
        flags = 0x00000008 | 0x00000200  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
    try:
        subprocess.Popen(build_command(browser, account["url"], profile, size, pos),
                         close_fds=True, creationflags=flags)
    except OSError as e:
        return False, f"Không mở được trình duyệt: {e}"
    return True, f"Đã mở {account['provider']} · {account['label']}"
