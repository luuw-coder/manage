"""Dựng thư mục đóng gói MSIX: chép bản đã build, tạo logo đúng kích thước, điền AppxManifest.

Chạy:  python msix/build_layout.py dist/ManageMoho msix_layout
Biến môi trường (lấy từ Partner Center, phải khớp từng ký tự):
  MSIX_IDENTITY_NAME, MSIX_PUBLISHER, MSIX_PUBLISHER_DISPLAY, MSIX_VERSION (mặc định 0.1.0.0)
"""
import os
import re
import shutil
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def make_assets(dest):
    os.makedirs(dest, exist_ok=True)
    logo = Image.open(os.path.join(ROOT, "assets", "logo.png")).convert("RGBA")
    for name, (w, h) in {"StoreLogo.png": (50, 50), "Square44x44Logo.png": (44, 44),
                         "Square150x150Logo.png": (150, 150), "Wide310x150Logo.png": (310, 150)}.items():
        canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        side = min(w, h)
        icon = logo.resize((side, side), Image.LANCZOS)
        canvas.paste(icon, ((w - side) // 2, (h - side) // 2), icon)
        canvas.save(os.path.join(dest, name))


def render_manifest(values):
    with open(os.path.join(HERE, "AppxManifest.xml"), "r", encoding="utf-8") as f:
        text = f.read()
    for key, val in values.items():
        text = text.replace("{{" + key + "}}", val)
    left = re.findall(r"\{\{[A-Z_]+\}\}", text)
    if left:
        raise SystemExit(f"Còn giá trị chưa điền trong manifest: {left}")
    return text


def main(dist, layout):
    env = os.environ
    values = {
        "IDENTITY_NAME": env.get("MSIX_IDENTITY_NAME", "").strip(),
        "PUBLISHER": env.get("MSIX_PUBLISHER", "").strip(),
        "PUBLISHER_DISPLAY": env.get("MSIX_PUBLISHER_DISPLAY", "").strip(),
        "VERSION": env.get("MSIX_VERSION", "0.1.0.0").strip(),
    }
    missing = [k for k, v in values.items() if not v]
    if missing:
        raise SystemExit("Thiếu giá trị từ Partner Center: " + ", ".join(missing) +
                         ". Xem HUONG_DAN_PHAT_HANH_STORE.md.")
    if not re.fullmatch(r"\d+\.\d+\.\d+\.0", values["VERSION"]):
        raise SystemExit("MSIX_VERSION phải có 4 số và số cuối là 0, ví dụ 0.1.0.0 (quy định của Microsoft Store).")
    if os.path.exists(layout):
        shutil.rmtree(layout)
    shutil.copytree(dist, layout)
    make_assets(os.path.join(layout, "Assets"))
    with open(os.path.join(layout, "AppxManifest.xml"), "w", encoding="utf-8") as f:
        f.write(render_manifest(values))
    print("Đã dựng", layout)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    main(sys.argv[1], sys.argv[2])
