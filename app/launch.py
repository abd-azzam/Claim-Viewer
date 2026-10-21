"""Claim Viewer: native window (pywebview over WebView2) for index.html, plus the library API.

The page runs over file://, so it cannot write files. Everything that touches the disk
(importing a PDF, saving library.json) goes through the js_api below.

At every start this rewrites sources.js from library.json, so the page sees the current
library: <script src="sources.js"> works over file:// where fetch() would be blocked.
"""
import base64
import ctypes
import hashlib
import json
import os
import pathlib
import re
import shutil
import sys
import time

import webview

ROOT = os.path.dirname(sys.executable if getattr(sys, "frozen", False) else os.path.abspath(__file__))
os.chdir(ROOT)
PDF_DIR = os.path.join(ROOT, "pdf")
LIB_PATH = os.path.join(ROOT, "library.json")
SRC_PATH = os.path.join(ROOT, "sources.js")
INDEX = pathlib.Path(ROOT, "index.html")


def stop(msg):
    ctypes.windll.user32.MessageBoxW(0, msg, "Claim Viewer", 0x10)
    sys.exit(1)


def read_lib():
    try:
        with open(LIB_PATH, encoding="utf-8") as f:
            lib = json.load(f)
    except Exception:
        lib = {"version": 1, "collections": [], "items": {}}
    lib.setdefault("collections", [])
    lib.setdefault("items", {})
    return lib


def write_lib(lib):
    tmp = LIB_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(lib, f, ensure_ascii=False, indent=1)
    os.replace(tmp, LIB_PATH)


def write_sources(lib):
    """sources.js is the only way the file:// page can read the library at load."""
    rows = [{"id": i, "title": v.get("title") or i} for i, v in sorted(
        lib["items"].items(), key=lambda kv: (kv[1].get("title") or kv[0]).lower())]
    lib_json = json.dumps(lib, ensure_ascii=False).replace("</", "<\\/")
    body = "window.SOURCES=%s;\nwindow.LIBRARY=%s;\n" % (
        json.dumps(rows, ensure_ascii=False).replace("</", "<\\/"), lib_json)
    with open(SRC_PATH, "w", encoding="utf-8") as f:
        f.write("// Written by ClaimViewer.exe from library.json at every start. Do not edit.\n" + body)


def safe_id(path):
    stem = re.sub(r"\.pdf$", "", os.path.basename(path), flags=re.I)
    return re.sub(r'[\\/:*?"<>|]', "-", stem).strip() or "untitled"


class Api:
    def save_pdf(self, name, b64):  # PDF-only save dialog; "" when cancelled
        try:  # window=win keeps the dialog owned by the app, so it cannot open behind it
            r = win.create_file_dialog(webview.FileDialog.SAVE, save_filename=name,
                                       file_types=("PDF files (*.pdf)",), window=win)
        except TypeError:  # pywebview without the window= argument
            r = win.create_file_dialog(webview.FileDialog.SAVE, save_filename=name,
                                       file_types=("PDF files (*.pdf)",))
        except Exception:
            return ""
        if not r:
            return ""
        f = r if isinstance(r, str) else r[0]
        if not f.lower().endswith(".pdf"):
            f += ".pdf"
        with open(f, "wb") as fh:
            fh.write(base64.b64decode(b64))
        return f

    def save_pages(self, text):  # reading positions live beside the library, so a wiped WebView2 profile does not lose them
        try:
            d = json.loads(text)
            if not isinstance(d, dict):
                return {"ok": False, "error": "not a page map"}
            clean = {}
            for k, v in d.items():
                try:
                    n = int(v)
                except Exception:
                    continue
                if n > 0:
                    clean[str(k)] = n
            p = os.path.join(ROOT, "last-pages.json")
            tmp = p + ".tmp"
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(clean, fh, ensure_ascii=False)
            os.replace(tmp, p)
            return {"ok": True, "count": len(clean)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def load_pages(self):
        try:
            with open(os.path.join(ROOT, "last-pages.json"), encoding="utf-8") as fh:
                d = json.load(fh)
            return d if isinstance(d, dict) else {}
        except Exception:
            return {}

    def save_library(self, text):
        try:
            lib = json.loads(text)
            if not isinstance(lib.get("collections"), list) or not isinstance(lib.get("items"), dict):
                return {"ok": False, "error": "not a library"}
            write_lib(lib)
            write_sources(lib)
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def import_pdfs(self, collection="", paths=None):
        if paths:  # testing hook: the native dialog cannot be driven from the page
            picked = list(paths)
        else:
            try:
                picked = win.create_file_dialog(webview.FileDialog.OPEN, allow_multiple=True,
                                                file_types=("PDF files (*.pdf)",), window=win)
            except Exception as e:
                return {"error": str(e)}
        if not picked:
            return {"added": [], "library": read_lib()}
        os.makedirs(PDF_DIR, exist_ok=True)
        lib = read_lib()
        added = []
        for src in picked:
            if not src.lower().endswith(".pdf"):
                continue
            i = safe_id(src)
            n = 2
            while i in lib["items"]:  # same file name twice: keep both
                i = "%s (%d)" % (safe_id(src), n)
                n += 1
            dst = os.path.join(PDF_DIR, i + ".pdf")
            if os.path.abspath(src) != os.path.abspath(dst):  # picking a file already in pdf\ threw WinError 32
                shutil.copy2(src, dst)
            lib["items"][i] = {"title": i, "collections": [collection] if collection else [],
                               "tags": []}
            added.append(i)
        if added:
            write_lib(lib)
            write_sources(lib)
        return {"added": added, "library": lib}  # the page adopts this: its in-memory LIB is stale after a write

    def log(self, line):  # the page's timing probes land in perf.log next to the exe
        try:
            with open(os.path.join(ROOT, "perf.log"), "a", encoding="utf-8") as f:
                f.write("%s\t%s\n" % (time.strftime("%H:%M:%S"), line))
        except Exception:
            pass
        return True

    def open_library_folder(self):
        os.startfile(PDF_DIR)
        return True


h = hashlib.md5(ROOT.lower().encode()).hexdigest()
store = os.path.join(os.environ.get("LOCALAPPDATA") or ROOT, "ClaimViewer", "p-" + h[:8])
os.makedirs(store, exist_ok=True)

lib = read_lib()
write_sources(lib)
if "--selftest" in sys.argv:  # round-trip check used by the build: python launch.py --selftest
    n = len(lib["items"])
    got = json.loads(open(SRC_PATH, encoding="utf-8").read().split("window.LIBRARY=", 1)[1].rstrip().rstrip(";"))
    assert got["items"].keys() == lib["items"].keys(), "sources.js does not mirror library.json"
    assert len(got["collections"]) == len(lib["collections"]), "collections lost"
    print("selftest ok: %d readings, %d collections, %d pdfs" % (
        n, len(lib["collections"]), len([f for f in os.listdir(PDF_DIR) if f.lower().endswith(".pdf")])))
    sys.exit(0)
if not INDEX.exists():
    stop("index.html is missing from %s.\n\nCopy it next to ClaimViewer.exe." % ROOT)

def _place(w, h):  # the window opened off to the right, and on a small screen it did not fit at all
    try:
        import ctypes

        class RECT(ctypes.Structure):
            _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                        ("right", ctypes.c_long), ("bottom", ctypes.c_long)]
        r = RECT()
        ctypes.windll.user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(r), 0)  # SPI_GETWORKAREA
        aw, ah = r.right - r.left, r.bottom - r.top
        w, h = min(w, max(900, aw - 40)), min(h, max(600, ah - 80))
        return w, h, r.left + max(0, (aw - w) // 2), r.top + max(0, (ah - h) // 2)
    except Exception:
        return w, h, None, None


_ww, _wh, _cx, _cy = _place(1500, 920)
win = webview.create_window("Claim Viewer", INDEX.as_uri(), js_api=Api(),
                            width=_ww, height=_wh, min_size=(900, 600), text_select=True,
                            x=_cx, y=_cy)
webview.settings["ALLOW_DOWNLOADS"] = True
webview.start(storage_path=store, private_mode=False)
os._exit(0)
