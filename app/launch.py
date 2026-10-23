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
import tempfile
import threading
import time
import urllib.error
import urllib.request

import webview

ROOT = os.path.dirname(sys.executable if getattr(sys, "frozen", False) else os.path.abspath(__file__))
os.chdir(ROOT)
PDF_DIR = os.path.join(ROOT, "pdf")
LIB_PATH = os.path.join(ROOT, "library.json")
SRC_PATH = os.path.join(ROOT, "sources.js")
AI_PATH = os.path.join(ROOT, "ai.json")
INDEX = pathlib.Path(ROOT, "index.html")


def stop(msg):
    ctypes.windll.user32.MessageBoxW(0, msg, "Claim Viewer", 0x10)
    sys.exit(1)


_LOCKS = {}
_LOCK_GUARD = threading.Lock()


def _lock_for(path):
    with _LOCK_GUARD:
        return _LOCKS.setdefault(os.path.normcase(os.path.abspath(path)), threading.Lock())


def _swap(tmp, path):
    """os.replace until the other handle lets go: 320 saves at once used to half-fail with WinError 5."""
    for i in range(40):
        try:
            os.replace(tmp, path)
            return
        except PermissionError:
            if i == 39:
                raise
            time.sleep(0.01 * (1 + i % 5))


def _atomic(path, text):
    """Write beside the target under a unique name, then swap it in.

    A shared "<name>.tmp" made two saves collide with WinError 32, and a save that
    died halfway left the old file replaced by a truncated one."""
    d = os.path.dirname(path) or "."
    fd, tmp = tempfile.mkstemp(prefix=".tmp-", suffix=".part", dir=d)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        with _lock_for(path):
            _swap(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _atomic_bytes(path, data):
    d = os.path.dirname(path) or "."
    fd, tmp = tempfile.mkstemp(prefix=".tmp-", suffix=".part", dir=d)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        with _lock_for(path):
            _swap(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def read_lib():
    """Read library.json, or an empty library, and never hand back a shape the page cannot read.

    A file that fails to parse is copied aside first: the next import used to replace a
    damaged library with a one-item one and the old readings were gone."""
    try:
        with open(LIB_PATH, encoding="utf-8-sig") as f:  # PowerShell 5.1 writes a BOM; json.load rejects it
            lib = json.load(f)
    except FileNotFoundError:
        lib = {"version": 1, "collections": [], "items": {}}
    except Exception:
        try:
            shutil.copy2(LIB_PATH, LIB_PATH + time.strftime(".damaged-%Y%m%d-%H%M%S.json"))
        except Exception:
            pass
        lib = {"version": 1, "collections": [], "items": {}}
    if not isinstance(lib, dict):
        lib = {"version": 1, "collections": [], "items": {}}
    lib.setdefault("collections", [])
    lib.setdefault("items", {})
    items = {}
    for k, v in list(lib["items"].items()):
        if not isinstance(k, str) or not isinstance(v, dict):
            continue  # a string item used to stop the app before the window opened
        if not isinstance(v.get("title"), str):
            v["title"] = str(v.get("title") or k)
        cols = v.get("collections")
        v["collections"] = [str(c) for c in cols] if isinstance(cols, list) else []
        items[k] = v
    lib["items"] = items
    lib["collections"] = [c for c in lib["collections"] if isinstance(c, dict) and isinstance(c.get("id"), str)]
    return lib


def write_lib(lib):
    _atomic(LIB_PATH, json.dumps(lib, ensure_ascii=False, indent=1))


def write_sources(lib):
    """sources.js is the only way the file:// page can read the library at load."""
    rows = [{"id": i, "title": v.get("title") or i} for i, v in sorted(
        lib["items"].items(), key=lambda kv: (kv[1].get("title") or kv[0]).lower())]
    lib_json = json.dumps(lib, ensure_ascii=False).replace("</", "<\\/")
    body = "window.SOURCES=%s;\nwindow.LIBRARY=%s;\n" % (
        json.dumps(rows, ensure_ascii=False).replace("</", "<\\/"), lib_json)
    _atomic(SRC_PATH, "// Written by ClaimViewer.exe from library.json at every start. Do not edit.\n" + body)


RESERVED = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}


def _ai_cfg():
    try:
        with open(AI_PATH, encoding="utf-8-sig") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def _dialog(kind, **kw):
    """pywebview 6.2.1 has no window= argument; older builds took one to keep the dialog owned by the app."""
    try:
        return win.create_file_dialog(kind, window=win, **kw)
    except TypeError:
        return win.create_file_dialog(kind, **kw)


def safe_id(path):
    stem = re.sub(r"\.pdf$", "", os.path.basename(path), flags=re.I)
    stem = re.sub(r'[\\/:*?"<>|]', "-", stem).strip() or "untitled"
    if stem.split(".")[0].upper() in RESERVED:
        stem += "_"  # a reading called NUL.pdf used to create a file Windows cannot delete
    return stem


class Api:
    def save_pdf(self, name, b64):  # PDF-only save dialog; "" when cancelled
        try:
            r = _dialog(webview.FileDialog.SAVE, save_filename=name, file_types=("PDF files (*.pdf)",))
        except Exception:
            return ""
        if not r:
            return ""
        f = r if isinstance(r, str) else r[0]
        if not f.lower().endswith(".pdf"):
            f += ".pdf"
        try:
            data = base64.b64decode(b64, validate=True)  # decode first: a bad payload used to leave a 0-byte file
        except Exception:
            return ""
        _atomic_bytes(f, data)
        return f

    def save_image(self, name, b64):  # PNG/JPG save dialog for a graph export; "" when cancelled
        ext = os.path.splitext(name)[1].lower() or ".png"  # the dialog lists the three image types and nothing else
        types = ("PNG image (*.png)", "JPG image (*.jpg)", "JPEG image (*.jpeg)")
        try:
            r = _dialog(webview.FileDialog.SAVE, save_filename=name, file_types=types)
        except Exception:
            return ""
        if not r:
            return ""
        f = r if isinstance(r, str) else r[0]
        if not f.lower().endswith((".png", ".jpg", ".jpeg")):
            f += ext or ".png"
        try:
            data = base64.b64decode(b64, validate=True)
        except Exception:
            return ""
        _atomic_bytes(f, data)
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
            _atomic(os.path.join(ROOT, "last-pages.json"), json.dumps(clean, ensure_ascii=False))
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
            if not isinstance(lib, dict) or not isinstance(lib.get("collections"), list) or not isinstance(lib.get("items"), dict):
                return {"ok": False, "error": "not a library"}
            for k, v in lib["items"].items():
                if not isinstance(k, str) or not isinstance(v, dict):
                    return {"ok": False, "error": "item %r is not an object" % (k,)}
                if not isinstance(v.get("title"), str):
                    return {"ok": False, "error": "item %r has no text title" % (k,)}
                if not isinstance(v.get("collections", []), list):
                    return {"ok": False, "error": "item %r has no collection list" % (k,)}
            for c in lib["collections"]:
                if not isinstance(c, dict) or not isinstance(c.get("id"), str):
                    return {"ok": False, "error": "a collection is not an object with an id"}
            write_lib(lib)  # nothing is written until the whole library checks out
            write_sources(lib)
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def import_pdfs(self, collection="", paths=None):
        if paths:  # testing hook: the native dialog cannot be driven from the page
            picked = list(paths)
        else:
            try:
                picked = _dialog(webview.FileDialog.OPEN, allow_multiple=True,
                                 file_types=("PDF files (*.pdf)",))
            except Exception as e:
                return {"error": str(e)}
        if not picked:
            return {"added": [], "library": read_lib()}
        os.makedirs(PDF_DIR, exist_ok=True)
        lib = read_lib()
        added, failed = [], []
        taken = {k.lower() for k in lib["items"]}
        try:  # NTFS is case-insensitive: "Smith.pdf" and "smith.pdf" are the same file on disk
            taken |= {os.path.splitext(f)[0].lower() for f in os.listdir(PDF_DIR)}
        except OSError:
            pass
        for src in picked:
            name = os.path.basename(str(src))
            try:
                if not str(src).lower().endswith(".pdf"):
                    continue
                if not os.path.isfile(src):
                    failed.append([name, "file not found"])
                    continue
                if os.path.getsize(src) == 0:
                    failed.append([name, "empty file"])
                    continue
                base = safe_id(src)
                i, n = base, 2
                while i.lower() in taken:  # same file name twice: keep both
                    i = "%s (%d)" % (base, n)
                    n += 1
                dst = os.path.join(PDF_DIR, i + ".pdf")
                if os.path.normcase(os.path.abspath(src)) != os.path.normcase(os.path.abspath(dst)):
                    shutil.copy2(src, dst)  # picking a file already in pdf\\ threw WinError 32
                lib["items"][i] = {"title": i, "collections": [collection] if collection else [],
                                   "tags": []}
                taken.add(i.lower())
                added.append(i)
            except Exception as e:  # one unreadable file must not strand the rest of the batch
                failed.append([name, str(e)])
        if added:
            write_lib(lib)
            write_sources(lib)
        return {"added": added, "failed": failed, "library": lib}  # the page adopts this: its in-memory LIB is stale after a write

    def ai_status(self):  # the Ask AI tab asks this before it shows the key box
        c = _ai_cfg()
        return {"has_key": bool((c.get("key") or "").strip()), "base": c.get("base") or "",
                "model": c.get("model") or "deepseek-chat"}

    def ai_set_key(self, key="", base=""):
        """Save the key and an optional base URL. An empty key keeps the stored one."""
        key = (key or "").strip()
        base = (base or "").strip().rstrip("/")
        if base and not base.lower().startswith(("http://", "https://")):
            return {"ok": False, "error": "the base URL must start with http:// or https://"}
        c = _ai_cfg()
        if key:
            c["key"] = key
        if not (c.get("key") or "").strip():
            return {"ok": False, "error": "paste an API key first"}
        if base:
            c["base"] = base
        else:
            c.pop("base", None)
        c.setdefault("model", "deepseek-chat")
        _atomic(AI_PATH, json.dumps(c, ensure_ascii=False, indent=1))
        return {"ok": True, "has_key": True, "base": c.get("base") or "", "model": c["model"]}

    def ai_models(self):  # the picker asks what the endpoint really serves, so a renamed id cannot break it
        c = _ai_cfg()
        key = (c.get("key") or "").strip()
        if not key:
            return {"ok": False, "models": [], "error": "no API key yet"}
        base = (c.get("base") or "https://api.deepseek.com").rstrip("/")
        req = urllib.request.Request(base + "/models",
                                     headers={"Authorization": "Bearer " + key})
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                j = json.loads(r.read().decode("utf-8"))
            ids = [m.get("id") for m in (j.get("data") or []) if isinstance(m, dict) and m.get("id")]
            return {"ok": True, "models": ids[:40]}
        except urllib.error.HTTPError as e:
            return {"ok": False, "models": [], "error": "HTTP %s" % e.code}
        except Exception as e:
            return {"ok": False, "models": [], "error": str(e)[:200]}

    def ai_chat(self, messages_json, model=""):  # DeepSeek is OpenAI-compatible; the page cannot POST from file://
        c = _ai_cfg()
        key = (c.get("key") or "").strip()
        if not key:
            return {"ok": False, "error": "no API key yet: paste one in the Ask AI tab"}
        try:
            msgs = json.loads(messages_json)
            if not isinstance(msgs, list) or not msgs:
                return {"ok": False, "error": "no messages"}
        except Exception as e:
            return {"ok": False, "error": "bad messages: %s" % e}
        base = (c.get("base") or "https://api.deepseek.com").rstrip("/")
        url = base if base.endswith("/chat/completions") else base + "/chat/completions"
        want = (model or "").strip() or (c.get("model") or "deepseek-v4-flash")
        if not re.match(r"^[A-Za-z0-9._:\-]{1,64}$", want):  # only a plain id reaches the request body
            want = c.get("model") or "deepseek-v4-flash"
        body = json.dumps({"model": want, "messages": msgs[-14:],
                           "temperature": 0.3, "max_tokens": 1200, "stream": False}).encode("utf-8")
        req = urllib.request.Request(
            url, data=body,
            headers={"Content-Type": "application/json", "Authorization": "Bearer " + key})
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                j = json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            try:
                msg = json.loads(e.read().decode("utf-8")).get("error", {}).get("message") or str(e)
            except Exception:
                msg = str(e)
            return {"ok": False, "error": "%s (HTTP %s)" % (msg[:300], e.code)}
        except Exception as e:
            return {"ok": False, "error": str(e)[:300]}
        try:
            txt = j["choices"][0]["message"]["content"]
        except Exception:
            return {"ok": False, "error": "unexpected reply: " + json.dumps(j)[:200]}
        return {"ok": True, "text": txt, "model": j.get("model") or ""}

    def log(self, line):  # the page's timing probes land in perf.log next to the exe
        try:
            with open(os.path.join(ROOT, "perf.log"), "a", encoding="utf-8") as f:
                f.write("%s\t%s\n" % (time.strftime("%H:%M:%S"), line))
        except Exception:
            pass
        return True

    def open_library_folder(self):
        try:
            os.makedirs(PDF_DIR, exist_ok=True)
            os.startfile(PDF_DIR)
            return True
        except Exception:
            return False


h = hashlib.md5(ROOT.lower().encode()).hexdigest()
store = os.path.join(os.environ.get("LOCALAPPDATA") or ROOT, "ClaimViewer", "p-" + h[:8])
os.makedirs(store, exist_ok=True)

for f in os.listdir(ROOT):  # halves of a save that died before it could swap the file in
    if f.startswith(".tmp-") and f.endswith(".part"):
        try:
            os.unlink(os.path.join(ROOT, f))
        except OSError:
            pass

lib = read_lib()
try:
    write_sources(lib)
except Exception as e:  # the window still opens; the user sees an empty list instead of no app
    print("sources.js could not be written:", e)
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
