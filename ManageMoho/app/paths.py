import os


def data_dir():
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    folder = os.path.join(base, "ManageMoho")
    os.makedirs(folder, exist_ok=True)
    return folder


def db_path():
    return os.path.join(data_dir(), "manage_moho.db")
