"""Duyệt thư mục thật, lọc đuôi tệp, sắp xếp, phân trang. Thuần Python, không dùng Qt."""
import json
import os
import re

DEFAULT_GROUPS = {
    "project": ["Dự án", [".moho", ".fla"]],
    "video": ["Video", [".mp4", ".mov", ".avi", ".mkv"]],
    "gif": ["GIF", [".gif"]],
    "audio": ["Âm thanh", [".wav", ".mp3", ".ogg", ".flac", ".m4a"]],
    "image": ["Hình ảnh", [".png", ".jpg", ".jpeg", ".webp", ".psd"]],
    "vector": ["Vector", [".svg", ".ai", ".eps"]],
    "model3d": ["Model 3D", [".obj", ".fbx", ".glb", ".gltf", ".stl", ".blend"]],
    "doc": ["Tài liệu", [".pdf", ".txt", ".md", ".docx"]],
}
IGNORED_NAMES = {"desktop.ini", "thumbs.db", ".ds_store"}


def pkey(path):
    """Khóa so sánh đường dẫn (không phân biệt hoa/thường trên Windows)."""
    return os.path.normcase(os.path.normpath(path))


def is_within(path, root):
    k, r = pkey(path), pkey(root)
    return k == r or k.startswith(r + os.sep)


def parse_exts(text):
    out = []
    for tok in re.split(r"[,;\s]+", text or ""):
        tok = tok.strip().lower()
        if not tok or tok == ".":
            continue
        if not tok.startswith("."):
            tok = "." + tok
        if tok not in out:
            out.append(tok)
    return out


def default_groups():
    return {k: [v[0], list(v[1])] for k, v in DEFAULT_GROUPS.items()}


def groups_from_json(text):
    try:
        data = json.loads(text)
        out = {}
        for k, v in data.items():
            out[str(k)] = [str(v[0]), parse_exts(" ".join(v[1]))]
        return out if out else default_groups()
    except Exception:
        return default_groups()


def groups_to_json(groups):
    return json.dumps(groups, ensure_ascii=False)


def exts_for(groups, keys):
    """Tập đuôi tệp được phép. None = không lọc (hiện mọi tệp)."""
    out = set()
    for k in keys:
        if k in groups:
            out.update(groups[k][1])
    return out or None


def human_size(n):
    units = ["B", "KB", "MB", "GB", "TB"]
    v, i = float(n), 0
    while v >= 1024 and i < len(units) - 1:
        v /= 1024
        i += 1
    return f"{int(v)} B" if i == 0 else f"{v:.1f} {units[i]}"


def make_entry(path):
    try:
        st = os.stat(path)
    except OSError:
        return None
    is_dir = os.path.isdir(path)
    norm = os.path.normpath(path)
    return {
        "path": norm,
        "name": os.path.basename(norm) or norm,
        "is_dir": is_dir,
        "size": 0 if is_dir else st.st_size,
        "mtime": st.st_mtime,
        "ext": "" if is_dir else os.path.splitext(norm)[1].lower(),
    }


def list_dir(path, exts=None):
    """Liệt kê thư mục thật. Thư mục luôn hiện; tệp lọc theo exts (None = hiện hết)."""
    out = []
    with os.scandir(path) as it:
        for e in it:
            name = e.name
            if name.lower() in IGNORED_NAMES:
                continue
            try:
                is_dir = e.is_dir()
            except OSError:
                continue
            ext = "" if is_dir else os.path.splitext(name)[1].lower()
            if not is_dir and exts is not None and ext not in exts:
                continue
            try:
                st = e.stat()
                size, mtime = (0 if is_dir else st.st_size), st.st_mtime
            except OSError:
                size, mtime = 0, 0
            out.append({"path": os.path.normpath(e.path), "name": name, "is_dir": is_dir,
                        "size": size, "mtime": mtime, "ext": ext})
    return out


def natural_key(s):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", s)]


def sort_items(items, mode="name"):
    """Ghim lên đầu, thư mục trước tệp, rồi theo mode: name | date | size | type."""
    def key(it):
        base = (0 if it.get("pinned") else 1, 0 if it["is_dir"] else 1)
        label = natural_key(it.get("label") or it["name"])
        if mode == "date":
            return base + (-it["mtime"], label)
        if mode == "size":
            return base + (-it["size"], label)
        if mode == "type":
            return base + (it["ext"], label)
        return base + (label,)
    items.sort(key=key)
    return items


def page_count(total, size):
    size = max(1, size)
    return max(1, -(-total // size))


def page_slice(items, page, size):
    size = max(1, size)
    pages = page_count(len(items), size)
    page = min(max(0, page), pages - 1)
    return items[page * size:(page + 1) * size], page, pages


def page_buttons(current, pages):
    """Số trang hiển thị, ví dụ [1,2,3,4,5,'…',10]. current tính từ 0."""
    cur = current + 1
    if pages <= 7:
        return list(range(1, pages + 1))
    if cur <= 4:
        return [1, 2, 3, 4, 5, "…", pages]
    if cur >= pages - 3:
        return [1, "…"] + list(range(pages - 4, pages + 1))
    return [1, "…", cur - 1, cur, cur + 1, "…", pages]


def breadcrumb(path, root):
    path, root = os.path.normpath(path), os.path.normpath(root)
    first = (os.path.basename(root) or root, root)
    try:
        rel = os.path.relpath(path, root)
    except ValueError:
        return [(os.path.basename(path) or path, path)]
    if rel == ".":
        return [first]
    parts, cur = [first], root
    for seg in rel.split(os.sep):
        cur = os.path.join(cur, seg)
        parts.append((seg, cur))
    return parts


def root_of(path, roots):
    """Gốc (đã thêm vào mục) chứa path; chọn gốc sâu nhất."""
    best = None
    for r in roots:
        if is_within(path, r) and (best is None or len(pkey(r)) > len(pkey(best))):
            best = r
    return best


def deep_search(starts, q, exts=None, cap=300, walk_cap=20000):
    """Tìm theo tên trong cả thư mục con. Trả về (kết quả, bị_cắt_bớt)."""
    q = q.lower()
    results, visited, truncated = [], 0, False
    for s in starts:
        if os.path.isfile(s):
            e = make_entry(s)
            if e and q in e["name"].lower():
                results.append(e)
            continue
        for root, dirs, files in os.walk(s):
            for name in dirs:
                visited += 1
                if q in name.lower():
                    e = make_entry(os.path.join(root, name))
                    if e:
                        results.append(e)
            for name in files:
                visited += 1
                if name.lower() in IGNORED_NAMES:
                    continue
                ext = os.path.splitext(name)[1].lower()
                if exts is not None and ext not in exts:
                    continue
                if q in name.lower():
                    e = make_entry(os.path.join(root, name))
                    if e:
                        results.append(e)
            if len(results) >= cap or visited >= walk_cap:
                truncated = True
                break
        if truncated:
            break
    return results[:cap], truncated
