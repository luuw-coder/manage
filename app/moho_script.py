"""Đưa tệp vào Moho / Adobe Animate bằng chính ngôn ngữ lệnh của chúng (cách các công cụ khác như MohoMCP làm).

- Moho: một script Lua chạy TRONG Moho. Manage Moho ghi danh sách tệp vào một "hàng đợi" (tệp văn bản),
  script đọc hàng đợi rồi tạo lớp ảnh / lớp âm thanh bằng lệnh chính thức của Moho
  (moho:CreateNewLayer, ImageLayer:SetSourceImage, AudioLayer:SetAudioFile, moho:ImportEPS)
  và ghi kết quả ra tệp để Manage Moho biết đã nhập được hay chưa.
- Adobe Animate: một tệp JSFL (JavaScript của Animate) gọi document.importFile cho từng tệp,
  chạy bằng "Animate.exe tệp.jsfl -AlwaysRunJSFL".
"""
import json
import os
import pathlib

SCRIPT_NAME = "ManageMoho_Import"
SCRIPT_FILE = SCRIPT_NAME + ".lua"
QUEUE_FILE = "moho_queue.txt"
RESULT_FILE = "moho_result.txt"
JSFL_FILE = "animate_import.jsfl"

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".tga", ".gif"}
MOVIE_EXTS = {".avi", ".mov", ".mp4"}
AUDIO_EXTS = {".wav", ".mp3", ".m4a", ".aiff", ".aif"}
VECTOR_EXTS = {".ai", ".eps"}


def exchange_dir():
    """Thư mục trao đổi giữa Manage Moho và script trong Moho. Dùng thư mục Public để đường dẫn luôn là chữ không dấu."""
    base = os.environ.get("PUBLIC") or r"C:\Users\Public"
    return os.path.join(base, "ManageMoho")


def classify(path):
    """'image' | 'movie' | 'audio' | 'vector' | '' (script không nhập được loại này)."""
    ext = os.path.splitext(path)[1].lower()
    for kind, group in (("image", IMAGE_EXTS), ("movie", MOVIE_EXTS), ("audio", AUDIO_EXTS), ("vector", VECTOR_EXTS)):
        if ext in group:
            return kind
    return ""


# ---------------------------------------------------------------- hàng đợi và kết quả (phía Manage Moho)
def write_queue(paths, folder=None):
    folder = folder or exchange_dir()
    os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, QUEUE_FILE), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(os.path.abspath(p) for p in paths) + "\n")
    clear_result(folder)
    return os.path.join(folder, QUEUE_FILE)


def clear_result(folder=None):
    try:
        os.remove(os.path.join(folder or exchange_dir(), RESULT_FILE))
    except OSError:
        pass


def read_result(folder=None):
    """None nếu Moho chưa phản hồi; ngược lại {'ok': số tệp nhập được, 'failed': [(đường dẫn, lý do)], 'note': ''}."""
    p = os.path.join(folder or exchange_dir(), RESULT_FILE)
    try:
        with open(p, "r", encoding="utf-8", errors="replace") as f:
            lines = [ln.rstrip("\r\n") for ln in f if ln.strip()]
    except OSError:
        return None
    if not lines or not lines[0].startswith("RESULT"):
        return None
    out = {"ok": 0, "failed": [], "note": ""}
    parts = lines[0].split("\t")
    try:
        out["ok"] = int(parts[1])
    except (IndexError, ValueError):
        pass
    for ln in lines[1:]:
        cols = ln.split("\t")
        if cols[0] == "FAIL" and len(cols) >= 3:
            out["failed"].append((cols[1], cols[2]))
        elif cols[0] == "NOTE" and len(cols) >= 2:
            out["note"] = cols[1]
    return out


# ---------------------------------------------------------------- script Lua chạy trong Moho
LUA_SOURCE = r'''-- Manage Moho: nhap cac tep ma phan mem Manage Moho da xep hang doi.
-- Cai dat: dat tep nay vao <Custom Content Folder>/Scripts/Menu roi khoi dong lai Moho.
ScriptName = "ManageMoho_Import"

ManageMoho_Import = {}

function ManageMoho_Import:Name() return "Manage Moho - Import" end
function ManageMoho_Import:Version() return "1.0" end
function ManageMoho_Import:UILabel() return "Manage Moho - Import" end
function ManageMoho_Import:Creator() return "Manage Moho" end
function ManageMoho_Import:Description() return "Imports the files queued by the Manage Moho app into the open project" end

local IMAGE = { png = true, jpg = true, jpeg = true, bmp = true, tga = true, gif = true, avi = true, mov = true, mp4 = true }
local AUDIO = { wav = true, mp3 = true, m4a = true, aiff = true, aif = true }
local VECTOR = { ai = true, eps = true }

local function exchange_dirs()
    local list = {}
    local pub = nil
    if os and os.getenv then pub = os.getenv("PUBLIC") end
    if pub and pub ~= "" then list[#list + 1] = pub .. "\\ManageMoho\\" end
    list[#list + 1] = "C:\\Users\\Public\\ManageMoho\\"
    return list
end

local function say(msg)
    local ok = pcall(function()
        LM.GUI.Alert(LM.GUI.ALERT_INFO, msg, nil, nil, "OK", nil, nil)
    end)
    if not ok then print(msg) end
end

local function basename(path)
    return (path:gsub("^.*[\\/]", ""))
end

local function extension(path)
    return (path:match("%.([^%.\\/]+)$") or ""):lower()
end

function ManageMoho_Import:Run(moho)
    local dir, qpath, f
    for _, d in ipairs(exchange_dirs()) do
        f = io.open(d .. "moho_queue.txt", "rb")
        if f then dir = d; qpath = d .. "moho_queue.txt"; break end
    end
    if not f then
        say("Manage Moho: nothing to import. In Manage Moho, right-click a file and choose Send to Moho.")
        return
    end
    local text = f:read("*a")
    f:close()
    text = text:gsub("^\239\187\191", "")

    local results = { ok = 0, failed = {}, note = "" }
    local function finish()
        local out = io.open(dir .. "moho_result.txt", "wb")
        if out then
            out:write("RESULT\t" .. results.ok .. "\t" .. #results.failed .. "\n")
            for _, r in ipairs(results.failed) do out:write("FAIL\t" .. r[1] .. "\t" .. r[2] .. "\n") end
            if results.note ~= "" then out:write("NOTE\t" .. results.note .. "\n") end
            out:close()
        end
    end

    if not moho.document then
        results.note = "no_document"
        finish()
        say("Manage Moho: open or create a project first, then run this script again.")
        return
    end

    local paths = {}
    for raw in text:gmatch("[^\n]+") do
        local line = raw:gsub("\r", "")
        if line ~= "" then paths[#paths + 1] = line end
    end

    pcall(function() moho.document:PrepUndo(nil) end)
    pcall(function() moho.document:SetDirty() end)

    for _, path in ipairs(paths) do
        local ext = extension(path)
        local name = basename(path)
        local ok, err = pcall(function()
            if IMAGE[ext] then
                local layer = moho:CreateNewLayer(MOHO.LT_IMAGE)
                moho:LayerAsImage(layer):SetSourceImage(path)
                layer:SetName(name)
            elseif AUDIO[ext] then
                local layer = moho:CreateNewLayer(MOHO.LT_AUDIO)
                moho:LayerAsAudio(layer):SetAudioFile(path)
                layer:SetName(name)
            elseif VECTOR[ext] then
                moho:ImportEPS(path)
            else
                error("unsupported_type")
            end
        end)
        if ok then
            results.ok = results.ok + 1
        else
            results.failed[#results.failed + 1] = { path, (tostring(err):gsub("[\t\r\n]", " ")) }
        end
    end

    os.remove(qpath)
    pcall(function() moho:UpdateUI() end)
    finish()
    if #results.failed > 0 then
        say("Manage Moho: imported " .. results.ok .. " file(s), " .. #results.failed .. " failed (unsupported type or file not found).")
    end
end
'''


def jsfl_source(paths):
    """Mã JSFL nhập các tệp vào tài liệu Animate đang mở (lên sân khấu)."""
    uris = [pathlib.Path(os.path.abspath(p)).as_uri() for p in paths]
    return (
        "(function () {\n"
        "  var files = " + json.dumps(uris) + ";\n"
        "  var dom = fl.getDocumentDOM();\n"
        "  if (!dom) { alert(\"Manage Moho: open or create a document in Animate first.\"); return; }\n"
        "  var failed = 0;\n"
        "  for (var i = 0; i < files.length; i++) {\n"
        "    try { dom.importFile(files[i], false); } catch (e) { failed++; }\n"
        "  }\n"
        "  if (failed > 0) { alert(\"Manage Moho: \" + failed + \" file(s) could not be imported.\"); }\n"
        "})();\n"
    )


def write_jsfl(paths, folder=None):
    folder = folder or exchange_dir()
    os.makedirs(folder, exist_ok=True)
    p = os.path.join(folder, JSFL_FILE)
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write(jsfl_source(paths))
    return p


# ---------------------------------------------------------------- cài script vào Moho
def script_dest_dir(root):
    """Thư mục Scripts/Menu bên trong 'Custom Content Folder' (hoặc chính nó nếu người dùng chọn sẵn thư mục Menu)."""
    root = os.path.normpath(root)
    if os.path.basename(root).lower() == "menu":
        return root
    if os.path.basename(root).lower() == "scripts":
        return os.path.join(root, "Menu")
    return os.path.join(root, "Scripts", "Menu")


def install_script(root):
    """Ghi script Lua vào Moho. Trả về đường dẫn tệp đã ghi. Ném OSError nếu không ghi được."""
    dest = script_dest_dir(root)
    os.makedirs(dest, exist_ok=True)
    path = os.path.join(dest, SCRIPT_FILE)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(LUA_SOURCE)
    return path


def save_script_copy(folder):
    """Lưu một bản script ở nơi tùy chọn (để tự chép vào Moho)."""
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, SCRIPT_FILE)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(LUA_SOURCE)
    return path
