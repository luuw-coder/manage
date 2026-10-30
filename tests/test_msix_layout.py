import os
import sys
import xml.dom.minidom

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "msix"))
import build_layout as bl  # noqa: E402


@pytest.fixture()
def dist(tmp_path):
    d = tmp_path / "dist"
    d.mkdir()
    (d / "ManageMoho.exe").write_bytes(b"x")
    return str(d)


def env(monkeypatch, **kw):
    base = {"MSIX_IDENTITY_NAME": "Ten.ManageMoho", "MSIX_PUBLISHER": "CN=ABC-123", "MSIX_PUBLISHER_DISPLAY": "Tên Tôi"}
    base.update(kw)
    for k in ("MSIX_IDENTITY_NAME", "MSIX_PUBLISHER", "MSIX_PUBLISHER_DISPLAY", "MSIX_VERSION"):
        monkeypatch.delenv(k, raising=False)
    for k, v in base.items():
        monkeypatch.setenv(k, v)


def test_layout_has_valid_manifest_assets_and_exe(tmp_path, dist, monkeypatch):
    env(monkeypatch)
    out = str(tmp_path / "layout")
    bl.main(dist, out)
    doc = xml.dom.minidom.parse(os.path.join(out, "AppxManifest.xml"))
    ident = doc.getElementsByTagName("Identity")[0]
    assert ident.getAttribute("Name") == "Ten.ManageMoho" and ident.getAttribute("Publisher") == "CN=ABC-123"
    assert ident.getAttribute("Version") == "0.1.0.0"
    assert doc.getElementsByTagName("rescap:Capability")[0].getAttribute("Name") == "runFullTrust"
    from PIL import Image
    sizes = {n: Image.open(os.path.join(out, "Assets", n)).size for n in os.listdir(os.path.join(out, "Assets"))}
    assert sizes == {"StoreLogo.png": (50, 50), "Square44x44Logo.png": (44, 44),
                     "Square150x150Logo.png": (150, 150), "Wide310x150Logo.png": (310, 150)}
    assert os.path.exists(os.path.join(out, "ManageMoho.exe"))
    assert "{{" not in open(os.path.join(out, "AppxManifest.xml"), encoding="utf-8").read()


def test_missing_identity_and_bad_version_are_rejected_clearly(tmp_path, dist, monkeypatch):
    env(monkeypatch, MSIX_IDENTITY_NAME="")
    with pytest.raises(SystemExit, match="Thiếu giá trị từ Partner Center"):
        bl.main(dist, str(tmp_path / "l1"))
    env(monkeypatch, MSIX_VERSION="1.0.0.1")
    with pytest.raises(SystemExit, match="số cuối là 0"):
        bl.main(dist, str(tmp_path / "l2"))
