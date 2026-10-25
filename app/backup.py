"""Sao lưu và khôi phục cài đặt, mục, tên hiển thị, tài khoản AI và kịch bản."""
import json

from .scripts_store import sanitize_name

MAGIC = "manage_moho_backup"


def make_backup(db, store):
    state = db.export_state()
    state["magic"] = MAGIC
    state["scripts"] = [{"name": n, "content": store.read(n), "html": store.read_html(n)} for n in store.list()]
    return state


def restore_backup(db, store, state):
    if state.get("magic") != MAGIC:
        raise ValueError("Đây không phải tệp sao lưu của Manage Moho")
    db.import_state(state)
    for s in state.get("scripts", []):
        name = sanitize_name(s.get("name", ""))
        if name:
            store.write(name, s.get("content", ""), s.get("html"))


def save_backup_file(path, state):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def load_backup_file(path):
    with open(path, "r", encoding="utf-8") as f:
        state = json.load(f)
    if not isinstance(state, dict) or state.get("magic") != MAGIC:
        raise ValueError("Đây không phải tệp sao lưu của Manage Moho")
    return state
