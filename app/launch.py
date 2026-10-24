"""Claim Viewer: native window (pywebview over WebView2) for index.html, plus the library API.

The page runs over file://, so it cannot write files. Everything that touches the disk
(importing a PDF, saving library.json) goes through the js_api below.

At every start this rewrites sources.js from library.json, so the page sees the current
library: <script src="sources.js"> works over file:// where fetch() would be blocked.
"""
import base64
import ctypes
import hashlib
import html
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.parse
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
_VOICE_CACHE = None  # the voice list is fetched once per run: it costs a network round trip


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


def _lib_mtime():
    """The version token the page sends back on its next save, so a stale copy cannot clobber."""
    try:
        return os.path.getmtime(LIB_PATH)
    except OSError:
        return 0


def meta_query_from_title(name):
    """Build a search string from a PDF file name: 'Bates-AreaStudiesPolitical-1997' -> 'Bates Area Studies Political 1997'."""
    s = re.sub(r"\.pdf$", "", os.path.basename(name or ""), flags=re.I)
    s = s.replace("_", " ").replace("-", " ")
    s = re.sub(r"([a-z])([A-Z])", r"\1 \2", s)
    s = re.sub(r"[^A-Za-z0-9 ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def write_sources(lib):
    """sources.js is the only way the file:// page can read the library at load."""
    rows = [{"id": i, "title": v.get("title") or i} for i, v in sorted(
        lib["items"].items(), key=lambda kv: (kv[1].get("title") or kv[0]).lower())]
    lib_json = json.dumps(lib, ensure_ascii=False).replace("</", "<\\/")
    body = "window.SOURCES=%s;\nwindow.LIBRARY=%s;\n" % (
        json.dumps(rows, ensure_ascii=False).replace("</", "<\\/"), lib_json)
    _atomic(SRC_PATH, "// Written by ClaimViewer.exe from library.json at every start. Do not edit.\n" + body)


RESERVED = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}


class _Blob(ctypes.Structure):
    _fields_ = [("n", ctypes.c_ulong), ("p", ctypes.POINTER(ctypes.c_ubyte))]


def _dpapi(data, protect):
    """Windows DPAPI: the bytes open only for the same Windows user on the same machine."""
    buf = ctypes.create_string_buffer(data, len(data))
    src, out = _Blob(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_ubyte))), _Blob()
    f = ctypes.windll.crypt32.CryptProtectData if protect else ctypes.windll.crypt32.CryptUnprotectData
    if not f(ctypes.byref(src), None, None, None, None, 0, ctypes.byref(out)):
        raise OSError("DPAPI refused")
    try:
        return ctypes.string_at(out.p, out.n)
    finally:
        ctypes.windll.kernel32.LocalFree.argtypes = [ctypes.c_void_p]
        ctypes.windll.kernel32.LocalFree(out.p)


def _ai_save(c):
    """ai.json never holds the key in clear: it keeps key_enc, the DPAPI blob in base64."""
    d = {k: v for k, v in c.items() if k != "key"}
    if (c.get("key") or "").strip():
        d["key_enc"] = base64.b64encode(_dpapi(c["key"].strip().encode("utf-8"), True)).decode("ascii")
    _atomic(AI_PATH, json.dumps(d, ensure_ascii=False, indent=1))


def _ai_cfg():
    """The stored settings with the key decrypted in memory only. An old plaintext key is encrypted on first read."""
    try:
        with open(AI_PATH, encoding="utf-8-sig") as f:
            d = json.load(f)
        if not isinstance(d, dict):
            return {}
    except Exception:
        return {}
    enc = d.pop("key_enc", None)
    if enc:
        try:
            d["key"] = _dpapi(base64.b64decode(enc), False).decode("utf-8")
        except Exception:  # another Windows user or machine: the key is unreadable, so ask for it again
            d["key"] = ""
    elif (d.get("key") or "").strip():
        try:
            _ai_save(d)
        except Exception:  # keep working with the clear key rather than lose it
            pass
    return d


def _tts_cfg():
    """The voice lives in ai.json beside the model; a missing file just means the default voice."""
    d = _ai_cfg()
    return {"voice": d.get("voice") or "en-US-AriaNeural"}


_TESS = {"path": None, "checked": False}


def _tess_exe():
    """Find tesseract once: PATH, then the two usual install folders. None means not installed."""
    if _TESS["checked"]:
        return _TESS["path"]
    _TESS["checked"] = True
    for cand in (shutil.which("tesseract"),
                 r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                 r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
                 os.path.join(os.environ.get("LOCALAPPDATA") or "", "Programs", "Tesseract-OCR", "tesseract.exe")):
        if cand and os.path.exists(cand):
            _TESS["path"] = cand
            break
    return _TESS["path"]


def _tess_version():
    exe = _tess_exe()
    if not exe:
        return ""
    try:
        r = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=20,
                           creationflags=0x08000000 if os.name == "nt" else 0)
        return (r.stdout or r.stderr or "").splitlines()[0][:80]
    except Exception:
        return ""


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

    def library_version(self):  # the page seeds LIBMT from this, so its very first save is guarded
        return {"ok": True, "mtime": _lib_mtime()}

    def save_library(self, text, base_mtime=0):
        try:
            lib = json.loads(text)
            if not isinstance(lib, dict) or not isinstance(lib.get("collections"), list) or not isinstance(lib.get("items"), dict):
                return {"ok": False, "error": "not a library"}
            # A stale in-memory copy must never overwrite a newer library.json: two saves racing
            # (web fill + a cell edit, or two windows) silently dropped one of them.
            try:
                cur = os.path.getmtime(LIB_PATH)
                if base_mtime and cur > float(base_mtime) + 1.5:
                    return {"ok": False, "error": "stale", "mtime": cur}
            except OSError:
                pass
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
            return {"ok": True, "mtime": _lib_mtime()}
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
        # Fill each new reading's bibliography from the web as it arrives, so the library is
        # usable without pressing anything. A failure here must never lose the import.
        filled = 0
        for i in added:
            try:
                q = meta_query_from_title(i)
                if not q:
                    continue
                got = self.lookup_meta(q)
                if got and got.get("ok"):
                    m = lib["items"][i].setdefault("meta", {})
                    for k in ("type", "title", "author", "year", "journal", "volume", "issue",
                              "pages", "doi", "publisher", "city", "isbn"):
                        if not m.get(k) and got.get(k):
                            m[k] = got[k]
                    filled += 1
            except Exception:
                pass
        if added:
            write_lib(lib)
            write_sources(lib)
        return {"added": added, "failed": failed, "library": lib, "filled": filled}  # the page adopts this: its in-memory LIB is stale after a write

    def ai_status(self):  # the Ask AI tab asks this before it shows the key box
        c = _ai_cfg()
        return {"has_key": bool((c.get("key") or "").strip()), "base": c.get("base") or "",
                "model": c.get("model") or "deepseek-chat", "voice": c.get("voice") or ""}

    def ai_set_key(self, key="", base=None):
        """Save the key and an optional base URL. An empty key keeps the stored one; base None keeps the stored base, "" clears it."""
        key = (key or "").strip()
        base = None if base is None else base.strip().rstrip("/")
        if base and not base.lower().startswith(("http://", "https://")):
            return {"ok": False, "error": "the base URL must start with http:// or https://"}
        c = _ai_cfg()
        if key:
            c["key"] = key
        if not (c.get("key") or "").strip():
            return {"ok": False, "error": "paste an API key first"}
        if base:
            c["base"] = base
        elif base is not None:
            c.pop("base", None)
        c.setdefault("model", "deepseek-chat")
        try:
            _ai_save(c)
        except Exception as e:
            return {"ok": False, "error": "could not store the key: %s" % e}
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
        if not isinstance(txt, str) or not txt.strip():  # reasoning models can answer with content null
            return {"ok": False, "error": "the model sent an empty reply: try again or pick another model"}
        return {"ok": True, "text": txt, "model": j.get("model") or ""}

    def ai_speak(self, text, voice=""):  # natural neural voice; the browser's own voice is robotic
        """Return base64 MP3 for one sentence. Empty audio means the machine is offline."""
        text = (text or "").strip()
        if not text:
            return {"ok": False, "error": "nothing to read"}
        if len(text) > 1200:
            text = text[:1200]
        v = (voice or "").strip() or _tts_cfg().get("voice") or "en-US-AriaNeural"
        if not re.match(r"^[a-z]{2}-[A-Z]{2}-[A-Za-z]{2,20}Neural$", v):
            v = "en-US-AriaNeural"
        try:
            import asyncio
            import edge_tts
        except Exception as e:
            return {"ok": False, "error": "edge-tts is not installed: %s" % e}
        async def go():
            com = edge_tts.Communicate(text, v)
            buf = bytearray()
            async for ch in com.stream():
                if ch.get("type") == "audio":
                    buf.extend(ch["data"])
            return bytes(buf)
        try:
            audio = asyncio.run(go())
        except Exception as e:
            return {"ok": False, "error": "the voice service did not answer: %s" % str(e)[:200]}
        if not audio:
            return {"ok": False, "error": "the voice service returned no audio"}
        return {"ok": True, "audio": base64.b64encode(audio).decode("ascii"), "voice": v}

    def ai_voices(self):  # the picker asks which voices exist; cached, because the list rarely changes
        """English voices only, grouped by accent. Falls back to a fixed list when offline."""
        global _VOICE_CACHE
        if _VOICE_CACHE is not None:
            return {"ok": True, "voices": _VOICE_CACHE, "cached": True}
        fallback = [
            {"id": "en-US-AriaNeural", "label": "Aria (US, female)"},
            {"id": "en-US-AndrewNeural", "label": "Andrew (US, male)"},
            {"id": "en-US-EmmaNeural", "label": "Emma (US, female)"},
            {"id": "en-US-BrianNeural", "label": "Brian (US, male)"},
            {"id": "en-GB-SoniaNeural", "label": "Sonia (UK, female)"},
            {"id": "en-GB-RyanNeural", "label": "Ryan (UK, male)"},
        ]
        try:
            import asyncio
            import edge_tts
            vs = asyncio.run(edge_tts.list_voices())
        except Exception as e:
            return {"ok": False, "voices": fallback, "error": "could not reach the voice service: %s" % str(e)[:160]}
        acc = {"en-US": "US", "en-GB": "UK", "en-AU": "Australia", "en-CA": "Canada", "en-IE": "Ireland",
               "en-IN": "India", "en-NZ": "New Zealand", "en-ZA": "South Africa", "en-SG": "Singapore",
               "en-KE": "Kenya", "en-NG": "Nigeria", "en-TZ": "Tanzania", "en-PH": "Philippines", "en-HK": "Hong Kong"}
        out = []
        for v in vs:
            sn = v.get("ShortName") or ""
            if not sn.startswith("en-"):
                continue
            loc = v.get("Locale") or ""
            name = re.sub(r"Neural$", "", sn.split("-")[-1])
            tag = ""
            if name.endswith("Multilingual"):
                name, tag = name[:-len("Multilingual")], ", multilingual"
            elif name.endswith("Expressive"):
                name, tag = name[:-len("Expressive")], ", expressive"
            sex = (v.get("Gender") or "").lower()
            out.append({"id": sn, "label": "%s (%s, %s%s)" % (name, acc.get(loc, loc), sex, tag),
                        "gender": sex, "locale": loc})
        # the six best-known voices first, then the rest by accent and name
        first = ["en-US-AriaNeural", "en-US-AndrewNeural", "en-US-EmmaNeural", "en-US-BrianNeural",
                 "en-GB-SoniaNeural", "en-GB-RyanNeural"]
        rank = {k: i for i, k in enumerate(first)}
        out.sort(key=lambda v: (rank.get(v["id"], 99), v["locale"], v["label"]))
        _VOICE_CACHE = out
        return {"ok": True, "voices": out, "cached": False}

    def ai_set_voice(self, voice=""):
        """Remember the chosen voice in ai.json beside the model."""
        v = (voice or "").strip()
        if not re.match(r"^[a-z]{2}-[A-Z]{2}-[A-Za-z]{2,24}Neural$", v):
            return {"ok": False, "error": "that is not a voice id"}
        c = _ai_cfg()
        c["voice"] = v
        try:
            _ai_save(c)
        except Exception as e:
            return {"ok": False, "error": "could not store the voice: %s" % e}
        return {"ok": True, "voice": v}

    def ocr_status(self):  # does this machine have Tesseract?
        exe = _tess_exe()
        return {"ok": bool(exe), "path": exe or "", "version": _tess_version()}

    def ocr_image(self, b64_png, scale=1.0):  # read a page the reader already rendered
        """Tesseract on a PNG the page drew with pdf.js. Boxes come back in PDF points (pixels / scale)."""
        exe = _tess_exe()
        if not exe:
            return {"ok": False, "error": "Tesseract is not installed on this machine"}
        try:
            raw = base64.b64decode((b64_png or "").split(",")[-1])
        except Exception as e:
            return {"ok": False, "error": "bad image: %s" % e}
        if len(raw) < 2000:
            return {"ok": False, "error": "the page image is empty"}
        # the format from the BYTES: leptonica picks the reader from the magic number, not the name
        ext = ".jpg" if raw[:2] == b"\xff\xd8" else ".png" if raw[:4] == b"\x89PNG" else ".bin"
        try:
            scale = float(scale) or 1.0
        except (TypeError, ValueError):
            scale = 1.0
        tmp = tempfile.NamedTemporaryFile(suffix=ext, delete=False, dir=tempfile.gettempdir())
        tmp.close()
        outbase = tmp.name + ".out"
        try:
            with open(tmp.name, "wb") as f:
                f.write(raw)
            # Write the TSV to a FILE, not stdout: a windowed PyInstaller build gives Tesseract no
            # usable stdout pipe, which is why scanned pages came back empty in the installed exe.
            r = subprocess.run([exe, tmp.name, outbase, "--psm", "3", "-l", "eng", "tsv"],
                               capture_output=True, text=True, timeout=180,
                               creationflags=0x08000000 if os.name == "nt" else 0)
            tsv_path = outbase + ".tsv"
            if r.returncode != 0 or not os.path.exists(tsv_path):
                # fall back to stdout for the plain build, where the pipe does work
                r2 = subprocess.run([exe, tmp.name, "stdout", "--psm", "3", "-l", "eng", "tsv"],
                                    capture_output=True, text=True, timeout=180,
                                    creationflags=0x08000000 if os.name == "nt" else 0)
                out = r2.stdout or ""
            else:
                with open(tsv_path, "r", encoding="utf-8", errors="replace") as f:
                    out = f.read()
        except subprocess.TimeoutExpired:
            return {"ok": False, "error": "Tesseract took too long on this page (180s). Try a smaller page range."}
        except Exception as e:
            return {"ok": False, "error": "tesseract failed: %s" % str(e)[:160]}
        finally:
            for pth in (tmp.name, outbase, outbase + ".tsv"):
                try:
                    os.unlink(pth)
                except OSError:
                    pass
        # stdout is None (not "") when the process was killed: never assume it is a string
        if not out.strip():
            return {"ok": False, "error": "no output (rc=%s bytes=%d head=%s)" % (
                r.returncode, len(raw), raw[:8].hex())}
        words, lines = [], {}
        for row in out.splitlines()[1:]:  # level page block par line word left top width height conf text
            f = row.split("\t")
            if len(f) < 12 or f[0] != "5":
                continue
            try:
                conf = float(f[10])
            except ValueError:
                continue
            txt = (f[11] or "").strip()
            if not txt or conf < 40:  # low-confidence noise is what makes a bad highlight worse
                continue
            lines.setdefault((f[2], f[3], f[4]), []).append(txt)
            words.append({"t": txt,
                          "x": round(int(f[6]) / scale, 2), "y": round(int(f[7]) / scale, 2),
                          "w": round(int(f[8]) / scale, 2), "h": round(int(f[9]) / scale, 2),
                          "c": round(conf)})
        text = "\n".join(" ".join(v) for _, v in sorted(lines.items()))
        return {"ok": bool(text.strip()), "text": text, "words": words,
                "error": "" if text.strip() else "Tesseract read no text from this page"}

    def lookup_meta(self, query):  # Crossref: free, no key, and it answers by title
        """Fill bibliography fields from the internet. Crossref first, then OpenAlex as a fallback."""
        q = (query or "").strip()
        if len(q) < 4:
            return {"ok": False, "error": "nothing to search for"}
        ua = "ClaimViewer/2.1 (desktop reference manager)"

        def get(url):
            req = urllib.request.Request(url, headers={"User-Agent": ua, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=25) as r:
                return json.loads(r.read().decode("utf-8", "replace"))

        def clean(s):
            s = html.unescape(str(s or ""))  # Crossref sends "Politics &amp; Society"
            return re.sub(r"\s+", " ", s).strip()

        STOP = {"the", "and", "for", "with", "from", "that", "this", "their", "state", "states",
                "new", "how", "why", "into", "over", "under", "its", "his", "her", "our", "not",
                "book", "paper", "article", "review", "edited", "press", "university"}

        def _words(t):
            return [x for x in re.findall(r"[a-z]{3,}", (t or "").lower()) if x not in STOP]

        def alike(a, b):  # is the hit really the thing we asked for?
            # Compare the query against the hit's MAIN title (the part before a colon or dash),
            # because that is what identifies the work. "Swimming Against the Current" then passes
            # while "Going with the flow or swimming against the current?" does not, even though
            # they share four words. A different work fails; when in doubt we refuse, since an
            # empty field beats a confidently wrong citation.
            qw = _words(a)
            main = re.split(r"[:;?]|\s[\u2013\u2014-]\s", b or "")[0]
            tw = _words(main)
            if len(qw) < 2 or len(tw) < 2:
                return False
            q = " " + " ".join(qw) + " "
            best = 0
            for i in range(len(tw)):
                for j in range(i + 2, len(tw) + 1):
                    if (" " + " ".join(tw[i:j]) + " ") in q:
                        best = max(best, j - i)
                    else:
                        break
            return best >= max(2, int(len(tw) * 0.75))

        def is_review(ttl, pages):
            # a review names the book in its own title; refuse those and single-page blurbs
            t = (ttl or "").lower()
            if len(t) > 200:
                return True
            if re.search(r"\breview\b|\breviewed by\b|\bby [A-Z]", ttl or ""):
                return True
            return bool(re.fullmatch(r"\d+-\d+", (pages or "").strip())) and (pages or "").split("-")[0] == (pages or "").split("-")[-1]

        # --- Crossref: the best source for a DOI, journal, volume, issue and pages
        try:
            j = get("https://api.crossref.org/works?rows=3&select=title,author,issued,container-title,"
                    "volume,issue,page,DOI,publisher,publisher-location,type,ISBN,editor"
                    "&query.bibliographic=" + urllib.parse.quote(q))
            items = (j.get("message") or {}).get("items") or []
        except Exception:
            items = []
        for it in items:
            ttl = clean((it.get("title") or [""])[0])
            if not ttl:
                continue
            names = [clean((a.get("family") or "") + (", " + a.get("given") if a.get("given") else ""))
                     for a in (it.get("author") or []) if a.get("family")]
            # a review record lists the reviewer first and the reviewed book's author second
            qn = set(re.findall(r"[a-z]{3,}", (q or "").lower()))
            named = [n for n in names if set(re.findall(r"[a-z]{3,}", n.lower())) & qn]
            au = "; ".join(named or names)
            yr = ""
            try:
                yr = str((it.get("issued") or {}).get("date-parts", [[""]])[0][0] or "")
            except Exception:
                pass
            typ = {"journal-article": "article", "book": "book", "book-chapter": "chapter",
                   "proceedings-article": "chapter", "report": "report"}.get(it.get("type") or "", "book")
            if is_review(ttl, clean(it.get("page"))) or not alike(q, ttl):
                continue  # a wrong citation is worse than an empty one
            out = {"ok": True, "source": "crossref", "type": typ, "title": ttl, "author": au, "year": yr,
                   "journal": clean((it.get("container-title") or [""])[0]),
                   "volume": clean(it.get("volume")), "issue": clean(it.get("issue")),
                   "pages": clean(it.get("page")), "doi": clean(it.get("DOI")),
                   "publisher": clean(it.get("publisher")), "city": clean(it.get("publisher-location")),
                   "isbn": clean((it.get("ISBN") or [""])[0])}
            if any(out.get(k) for k in ("journal", "doi", "publisher", "volume")):
                return out
        # --- OpenAlex: broader coverage for books and working papers
        try:
            j = get("https://api.openalex.org/works?per-page=3&search=" + urllib.parse.quote(q))
            for it in (j.get("results") or []):
                ttl = clean(it.get("title"))
                if not ttl:
                    continue
                au = "; ".join(clean(a.get("author", {}).get("display_name"))
                               for a in (it.get("authorships") or [])[:6])
                if not alike(q, ttl):
                    continue
                host = ((it.get("primary_location") or {}).get("source") or {})
                out = {"ok": True, "source": "openalex", "type": "article" if it.get("doi") else "book",
                       "title": ttl, "author": au, "year": str(it.get("publication_year") or ""),
                       "journal": clean(host.get("display_name")),
                       "volume": clean((it.get("biblio") or {}).get("volume")),
                       "issue": clean((it.get("biblio") or {}).get("issue")),
                       "pages": ("%s-%s" % ((it.get("biblio") or {}).get("first_page") or "",
                                            (it.get("biblio") or {}).get("last_page") or "")).strip("-"),
                       "doi": clean((it.get("doi") or "").replace("https://doi.org/", "")),
                       "publisher": clean((it.get("primary_location") or {}).get("source", {}).get("host_organization_name")
                                          if isinstance((it.get("primary_location") or {}).get("source"), dict) else ""),
                       "city": "", "isbn": ""}
                return out
        except Exception:
            pass
        # --- Google Books: the best source for books that Crossref has no record of
        try:
            j = get("https://www.googleapis.com/books/v1/volumes?maxResults=3&q=" + urllib.parse.quote(q))
            for it in (j.get("items") or []):
                v = it.get("volumeInfo") or {}
                ttl = clean(v.get("title"))
                if not ttl or not alike(q, ttl):
                    continue
                return {"ok": True, "source": "googlebooks", "type": "book", "title": ttl,
                        "author": clean("; ".join(v.get("authors") or [])),
                        "year": clean((v.get("publishedDate") or "")[:4]),
                        "journal": "", "volume": "", "issue": "",
                        "pages": clean(str(v.get("pageCount") or "")),
                        "doi": "", "publisher": clean(v.get("publisher")), "city": "",
                        "isbn": clean((v.get("industryIdentifiers") or [{}])[0].get("identifier"))}
        except Exception:
            pass
        return {"ok": False, "error": "no match found online"}

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


def _single_instance():
    """One ClaimViewer per machine, from any folder. A copy run outside its install folder would
    otherwise open a blank library (it reads library.json beside itself) and look like data loss."""
    try:
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateMutexW.restype = wintypes.HANDLE
        h = kernel32.CreateMutexW(None, True, "ClaimViewer.SingleInstance.v1")
        err = ctypes.get_last_error()
        if not h or err == 183:  # ERROR_ALREADY_EXISTS: another copy owns the mutex
            kernel32.CloseHandle(h)
            return False, h
        return True, h
    except Exception:
        return True, None  # never block startup on a platform quirk


_first, _hMutex = _single_instance()
if not _first:
    # Do not show a modal box: it blocks the process forever until someone clicks it. The window
    # that is already open is the feedback; just leave.
    os._exit(0)

# A copy run outside its install folder finds no library.json beside itself and opens a blank app,
# which looks exactly like lost data. Refuse that, and say where the real library is.
_LIB_HERE = os.path.join(ROOT, "library.json")
_REAL_LIB = r"C:\Apps\ClaimViewer\library.json"
if not os.path.exists(_LIB_HERE) and os.path.exists(_REAL_LIB):
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(
            None,
            "This copy of Claim Viewer has no library next to it, so it would open empty.\n\n"
            "Your readings are in C:\\Apps\\ClaimViewer.\n"
            "Open Claim Viewer from there (or the Start Menu) instead.",
            "Claim Viewer - wrong folder", 0x00000030)
    except Exception:
        pass
    os._exit(0)

win = webview.create_window("Claim Viewer", INDEX.as_uri(), js_api=Api(),
                            width=_ww, height=_wh, min_size=(900, 600), text_select=True,
                            x=_cx, y=_cy)
webview.settings["ALLOW_DOWNLOADS"] = True
webview.start(storage_path=store, private_mode=False)
os._exit(0)
