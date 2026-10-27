import os


def data_dir():
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    folder = os.path.join(base, "ManageMoho")
    os.makedirs(folder, exist_ok=True)
    return folder


def db_path():
    return os.path.join(data_dir(), "manage_moho.db")


def resource_path(*parts):
    """Đường dẫn tới tệp đi kèm (logo...), chạy được cả khi đã đóng gói bằng PyInstaller."""
    import sys
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base, *parts)
