r"""Bug hunter for Claim Viewer. Read-only on the real app: anything risky runs on a temp copy.

    python tools\bughunt.py              all three layers (about 2-4 minutes)
    python tools\bughunt.py --no-ui      static + API only (about 20 s)
    python tools\bughunt.py --no-pdf     skip the per-PDF page-count checks
    python tools\bughunt.py --quick      skip the localStorage fuzzing in the UI layer
    python tools\bughunt.py --app D:\path\ClaimViewer

Layer 1  static   files, template syntax, library.json, claims files, index.html freshness, stray files
Layer 2  api      launch.py's Api class on a copy, with a fake webview (no window opens)
Layer 3  ui       a copy of ClaimViewer.exe driven over the DevTools protocol by bughunt_ui.mjs

Writes tools\bughunt-report.md. Exit code 1 when any HIGH finding exists, else 0.
Run it without -I: the PDF checks need pypdf from the user site.
"""
import argparse
import ast
import collections
import hashlib
import importlib.util
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import types
import unicodedata
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
SEVS = ("HIGH", "MED", "LOW", "INFO")
FINDINGS, SKIPPED = [], []
BOM = b"\xef\xbb\xbf"
RESERVED = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}
SYNC_COPIES = [Path.home() / ".claude/skills/claim-viewer/template/template.html",
               Path.home() / "Documents/UIII/claim-viewer-github/template.html"]


def add(sev, area, title, detail=""):
    FINDINGS.append((sev, area, title, str(detail)))


def skip(area, why):
    SKIPPED.append((area, why))


def say(msg):
    print(msg, flush=True)


def eg(items, n=6):
    items = list(items)
    return "; ".join(map(str, items[:n])) + (f" ... +{len(items) - n} more" if len(items) > n else "")


def load_json(p):
    """(data, problem). A BOM is reported, not hidden: launch.py and build.py both choke on it."""
    try:
        raw = Path(p).read_bytes()
    except OSError as e:
        return None, f"unreadable: {e}"
    try:
        return json.loads(raw.decode("utf-8").lstrip("\ufeff")), ("BOM" if raw.startswith(BOM) else None)
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"


def node_check(code, module=False):
    node = shutil.which("node")
    if not node:
        return None
    with tempfile.NamedTemporaryFile("w", suffix=".mjs" if module else ".js", delete=False, encoding="utf-8") as f:
        f.write(code)
    try:
        r = subprocess.run([node, "--check", f.name], capture_output=True, text=True, encoding="utf-8")
        return r.returncode == 0, r.stderr.strip()[:500]
    finally:
        os.unlink(f.name)


# --------------------------------------------------------------------------- layer 1: static

def check_template(root):
    tp = root / "template" / "template.html"
    if not tp.exists():
        return None
    t = tp.read_text(encoding="utf-8")
    n = t.count("/*DATA*/null")
    if n != 1:
        add("HIGH", "template", f"/*DATA*/null marker appears {n} times", "build.py refuses to build unless it is exactly 1")
    for i, m in enumerate(re.finditer(r"<script([^>]*)>(.*?)</script>", t, re.S | re.I)):
        attrs, code = m.group(1), m.group(2)
        if "src=" in attrs.lower() or not code.strip():
            continue
        res = node_check(code, "module" in attrs.lower())
        if res is None:
            skip("template", "node not on PATH: the JavaScript syntax check did not run")
            break
        if not res[0]:
            add("HIGH", "template", f"inline script #{i} has a syntax error", res[1])
    markup = re.sub(r"<script.*?</script>", "", t, flags=re.S | re.I)
    dup = [k for k, v in collections.Counter(re.findall(r'\bid="([^"]+)"', markup)).items() if v > 1]
    if dup:
        add("MED", "template", "duplicate ids in the static markup", eg(dup))
    scripts = "\n".join(m.group(1) for m in re.finditer(r"<script[^>]*>(.*?)</script>", t, re.S | re.I))
    dyn = [k for k, v in collections.Counter(re.findall(r'\bid=\\?"([\w-]+)\\?"', scripts)).items() if v > 1]
    if dyn:
        add("LOW", "template", "ids written by more than one script string",
            f"{eg(dyn)}. Fine only if one is in the DOM at a time; the UI layer checks the live DOM.")
    used = set(re.findall(r'\$\(\s*["\']([\w-]+)["\']\s*\)', t)) | set(re.findall(r'getElementById\(\s*["\']([\w-]+)["\']', t))
    defined = set(re.findall(r'\bid\s*=\s*\\?["\']?([\w-]+)', t)) | set(re.findall(r'\.id\s*=\s*["\']([\w-]+)', t))
    if used - defined:
        add("LOW", "template", "$(id) calls whose id never appears in the file", eg(sorted(used - defined)))
    bridge = set(re.findall(r"pywebview\.api\.(\w+)", t))
    try:
        tree = ast.parse((root / "launch.py").read_text(encoding="utf-8"))
        api = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "Api")
        have = {f.name for f in api.body if isinstance(f, ast.FunctionDef)}
        if bridge - have:
            add("HIGH", "template", "the page calls API methods launch.py does not define", eg(sorted(bridge - have)))
        if have - bridge:
            add("INFO", "template", "Api methods the page never calls", eg(sorted(have - bridge)))
    except Exception as e:
        add("HIGH", "launch.py", "launch.py does not parse", f"{type(e).__name__}: {e}")
    return t


def check_index(root, tpl):
    ip = root / "index.html"
    if not ip.exists() or tpl is None:
        return
    idx = ip.read_text(encoding="utf-8")
    pre, suf = tpl.split("/*DATA*/null")
    if not (idx.startswith(pre) and idx.endswith(suf)):
        add("HIGH", "index.html", "index.html was not built from the current template",
            "The installed app does not have the latest template code. Run build.py.")
        return
    blob = idx[len(pre): len(idx) - len(suf)]
    try:
        data = json.loads(blob)
    except Exception as e:
        add("HIGH", "index.html", "the DATA blob is not valid JSON", f"{type(e).__name__}: {e}")
        return
    lib, _ = load_json(root / "library.json")
    if isinstance(lib, dict):
        built = {s["id"]: len(s["claims"]) for s in data["sources"]}
        miss = [i for i in lib.get("items", {}) if i not in built]
        extra = [i for i in built if i not in lib.get("items", {})]
        if miss or extra:
            add("MED", "index.html", "index.html and library.json list different readings",
                f"in library, not built: {eg(miss)}; built, not in library: {eg(extra)}. Run build.py.")
        stale = []
        for sid, n in built.items():
            p = root / "data" / "claims" / f"{sid}.verified.json"
            d, _ = load_json(p) if p.exists() else (None, None)
            if isinstance(d, dict) and len(d.get("claims", [])) != n:
                stale.append(f"{sid}: file {len(d['claims'])}, built {n}")
        if stale:
            add("MED", "index.html", "claim counts in index.html differ from the claims files", eg(stale))


def check_files(root):
    names = os.listdir(root)
    for n in names:
        if n.split(".")[0].upper() in RESERVED:
            add("MED", "files", f"stray file with a reserved device name: {n}",
                f'{(root / n).stat().st_size} bytes. Explorer cannot delete it. Run: del "\\\\?\\{root / n}"')
    tmps = [n for n in names if n.endswith(".tmp")]
    if tmps:
        add("LOW", "files", "leftover .tmp files (an atomic save did not finish)", eg(tmps))
    baks = [n for n in names if ".bak" in n]
    if len(baks) > 3:
        add("INFO", "files", f"{len(baks)} backup files in the app folder", eg(baks))
    pl = root / "perf.log"
    if pl.exists() and pl.stat().st_size > 1_000_000:
        add("LOW", "files", "perf.log is over 1 MB and Api.log never trims it", f"{pl.stat().st_size} bytes")
    exe, lp = root / "ClaimViewer.exe", root / "launch.py"
    if exe.exists() and lp.exists() and exe.stat().st_mtime < lp.stat().st_mtime - 2:
        add("MED", "files", "launch.py is newer than ClaimViewer.exe",
            "The exe is the frozen copy of launch.py, so a launch.py fix is not in the app until the exe is rebuilt.")
    lpj, lpt = root / "last-pages.json", root / "last-pages.json.tmp"
    if lpt.exists() and lpj.exists() and lpt.stat().st_mtime > lpj.stat().st_mtime:
        add("LOW", "files", "last-pages.json.tmp is newer than last-pages.json", "the last save_pages did not finish")
    sj = root / "sources.js"
    if sj.exists():
        try:
            got = json.loads(sj.read_text(encoding="utf-8").split("window.LIBRARY=", 1)[1].rstrip().rstrip(";"))
            lib, _ = load_json(root / "library.json")
            if isinstance(lib, dict) and set(got["items"]) != set(lib["items"]):
                add("LOW", "files", "sources.js does not match library.json", "launch.py rewrites it at the next start")
        except Exception as e:
            add("MED", "files", "sources.js cannot be parsed", f"{type(e).__name__}: {e}")
    if len({p.read_bytes() for p in [root / "template/template.html", *SYNC_COPIES] if p.exists()}) > 1:
        add("MED", "files", "template.html copies differ",
            eg([f"{p} {hashlib.md5(p.read_bytes()).hexdigest()[:8]}" for p in [root / "template/template.html", *SYNC_COPIES] if p.exists()], 4))


def check_library(root):
    p = root / "library.json"
    lib, prob = load_json(p)
    if lib is None:
        add("HIGH", "library", "library.json is not valid JSON", prob)
        return None
    if prob == "BOM":
        add("HIGH", "library", "library.json starts with a BOM",
            "launch.py read_lib() cannot parse it, treats the library as EMPTY, and the next import overwrites the file.")
    if not isinstance(lib.get("collections"), list) or not isinstance(lib.get("items"), dict):
        add("HIGH", "library", "library.json lacks a collections list or an items object")
        return None
    cols = {}
    for c in lib["collections"]:
        if not isinstance(c, dict) or not c.get("id"):
            add("MED", "library", "a collection has no id", c)
            continue
        if c["id"] in cols:
            add("MED", "library", f"duplicate collection id {c['id']}")
        cols[c["id"]] = c
        if not c.get("name"):
            add("LOW", "library", f"collection {c['id']} has no name")
    for c in cols.values():
        par, seen = c.get("parent"), {c["id"]}
        while par:
            if par not in cols:
                add("MED", "library", f"collection {c['id']} has a parent that does not exist", par)
                break
            if par in seen:
                add("HIGH", "library", f"collection parent cycle through {c['id']}", "the collection tree cannot be drawn")
                break
            seen.add(par)
            par = cols[par].get("parent")
    pdfdir = root / "pdf"
    onDisk = {f.name.lower() for f in pdfdir.iterdir()} if pdfdir.is_dir() else set()
    items = lib["items"]
    norm = collections.defaultdict(list)
    for i, v in items.items():
        norm[unicodedata.normalize("NFC", i).lower()].append(i)
    d = [v for v in norm.values() if len(v) > 1]
    if d:
        add("HIGH", "library", "reading ids that differ only by case or Unicode form",
            f"{eg(d)}. On NTFS they share one pdf file, so one reading shows the other's PDF.")
    bad_ids = [i for i in items if re.search(r'[\\/:*?"<>|]', i) or i != i.strip() or i.split(".")[0].upper() in RESERVED or i.endswith(".")]
    if bad_ids:
        add("MED", "library", "reading ids that are not valid Windows file names", eg(bad_ids))
    nopdf = [i for i in items if (i + ".pdf").lower() not in onDisk]
    if nopdf:
        add("HIGH", "library", f"{len(nopdf)} reading(s) in library.json have no PDF in pdf\\", eg(nopdf))
    inlib = {(i + ".pdf").lower() for i in items}
    orph = [n for n in onDisk if n.endswith(".pdf") and n not in inlib]
    if orph:
        add("LOW", "library", f"{len(orph)} PDF(s) in pdf\\ that no reading uses", eg(orph))
    for i, v in items.items():
        if not isinstance(v, dict):
            add("HIGH", "library", f"item {i} is not an object", "the app fails to start (write_sources)")
            continue
        if not isinstance(v.get("title", ""), str):
            add("HIGH", "library", f"item {i} has a non-text title", "write_sources sorts on title.lower()")
        unk = [c for c in v.get("collections", []) if c not in cols]
        if unk:
            add("MED", "library", f"item {i} sits in collections that do not exist", eg(unk))
    return lib


def check_claims(root, lib, use_pdf):
    if not isinstance(lib, dict):
        return
    cdir = root / "data" / "claims"
    files = {f.name[:-len(".verified.json")].lower(): f for f in cdir.glob("*.verified.json")} if cdir.is_dir() else {}
    items = lib["items"]
    none = [i for i in items if i.lower() not in files]
    if none:
        add("INFO", "claims", f"{len(none)} reading(s) have no claims file", eg(none))
    orph = [k for k in files if k not in {i.lower() for i in items}]
    if orph:
        add("LOW", "claims", "claims files for readings not in the library (build.py ignores them)", eg(orph))
    pages = {}
    if use_pdf:
        try:
            from pypdf import PdfReader
            import logging
            logging.getLogger("pypdf").setLevel(logging.CRITICAL)
        except ImportError:
            PdfReader = None
            skip("pdf", "pypdf is not installed: PDF header, page-count and page-range checks did not run")
        if PdfReader:
            say("  counting PDF pages ...")
            unreadable, enc, odd = [], [], []
            for i in items:
                f = root / "pdf" / f"{i}.pdf"
                if not f.exists():
                    continue
                head = f.open("rb").read(1024)
                if f.stat().st_size == 0 or b"%PDF-" not in head:
                    unreadable.append(f"{i} (no %PDF header or empty)")
                    continue
                try:
                    r = PdfReader(str(f), strict=False)
                    if r.is_encrypted:
                        enc.append(i)
                    pages[i] = len(r.pages)
                    if pages[i] == 0:
                        unreadable.append(f"{i} (0 pages)")
                except Exception as e:
                    # pypdf is stricter than pdf.js: a cyclic page tree opens fine in the app,
                    # so this is a note about the checker, not a defect in the viewer
                    odd.append(f"{i} ({type(e).__name__}: {str(e)[:70]})")
            if unreadable:
                add("MED", "pdf", "pypdf cannot parse these PDFs (pdf.js may still open them: click them in the app)", eg(unreadable))
            if odd:
                add("INFO", "pdf", "pypdf rejects these but the viewer opens them (cyclic page tree, not a defect)", eg(odd))
            if enc:
                add("MED", "pdf", "encrypted PDFs (pdf.js needs a password)", eg(enc))
    ov, _ = load_json(root / "data" / "overrides.json")
    ids, bad = collections.defaultdict(list), collections.defaultdict(list)
    st, roles = collections.Counter(), collections.Counter()
    for k, f in files.items():
        d, prob = load_json(f)
        if d is None:
            add("HIGH", "claims", f"{f.name} is not valid JSON", prob)
            continue
        if prob == "BOM":
            add("MED", "claims", f"{f.name} starts with a BOM", "build.py read_text(utf-8) then json.loads raises on it")
        cl = d.get("claims") if isinstance(d, dict) else None
        if not isinstance(cl, list):
            add("HIGH", "claims", f"{f.name} has no claims list", "build.py does load(p)['claims'] and crashes")
            continue
        seenq = set()
        for n, c in enumerate(cl):
            where = f"{f.name[:28]}#{n}"
            if not isinstance(c, dict) or "id" not in c:
                bad["no id (build.py c['id'] raises KeyError)"].append(where)
                continue
            ids[c["id"]].append(f.name)
            q = c.get("quote")
            if not isinstance(q, str) or not q.strip():
                bad["empty quote"].append(where)
            else:
                w = len(q.split())
                if w < 5 or w > 150:
                    bad["quote length outside 5-150 words"].append(f"{where} ({w})")
                if "\ufffd" in q or re.search(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", q) or "\ufeff" in q:
                    bad["quote holds a replacement or control character"].append(where)
                sig = (q, c.get("role"), c.get("page"), c.get("claim"))  # an exact copy, not two claims that share a sentence
                if sig in seenq:
                    bad["duplicate claim (same quote, role, page and claim text)"].append(where)
                seenq.add(sig)
            s = c.get("status")
            st[s] += 1
            roles[c.get("role")] += 1
            if s not in ("exact", "anchored", "ambiguous", "failed", "user"):
                bad["status outside exact/anchored/ambiguous/failed/user"].append(f"{where} ({s})")
            pp = c.get("pdf_page")
            if s in ("exact", "anchored") and not isinstance(pp, int):
                bad["matched claim without an integer pdf_page"].append(f"{where} ({pp!r})")
            elif isinstance(pp, int):
                if pp < 1:
                    bad["pdf_page below 1"].append(where)
                if k in {i.lower() for i in pages} and pp > next(v for i, v in pages.items() if i.lower() == k):
                    bad["pdf_page beyond the PDF's last page"].append(f"{where} (p.{pp})")
    for k, v in ids.items():
        if len(v) > 1:
            bad["claim id used more than once (overrides.json would hit all)"].append(f"{k} in {eg(set(v), 2)}")
    if isinstance(ov, dict):
        gone = [i for i in ov if i not in ids and not i.startswith("_")]
        if gone:
            bad["overrides.json id matches no claim"].extend(gone)
    sev = {"empty quote": "HIGH", "no id (build.py c['id'] raises KeyError)": "HIGH",
           "matched claim without an integer pdf_page": "MED", "pdf_page beyond the PDF's last page": "MED",
           "claim id used more than once (overrides.json would hit all)": "MED",
           "quote holds a replacement or control character": "MED", "pdf_page below 1": "MED"}
    for title, lst in bad.items():
        add(sev.get(title, "LOW"), "claims", f"{len(lst)} claim(s): {title}", eg(lst))
    add("INFO", "claims", f"status counts {dict(st)}; roles {dict(roles)}")


def static_layer(root, o):
    say("Layer 1: static checks")
    tpl = check_template(root)
    check_index(root, tpl)
    check_files(root)
    lib = check_library(root)
    check_claims(root, lib, not o.no_pdf)
    return lib


# --------------------------------------------------------------------------- layer 2: Api on a copy

class _Done(BaseException):
    """Raised by the patched os._exit so launch.py's module level ends without opening a window."""


def fake_webview():
    m = types.ModuleType("webview")
    m.FileDialog = types.SimpleNamespace(SAVE=1, OPEN=2)
    m.settings = {}

    class Win:
        result = ""

        def create_file_dialog(self, *a, **k):
            return self.result
    m.create_window = lambda *a, **k: Win()
    m.start = lambda *a, **k: None
    return m


def load_launch(tmp, argv=None):
    sys.modules["webview"] = fake_webview()
    real_exit, cwd, real_argv = os._exit, os.getcwd(), sys.argv

    def boom(code=0):
        raise _Done()
    os._exit, sys.argv = boom, ["launch.py", *(argv or [])]
    spec = importlib.util.spec_from_file_location("launch_copy", tmp / "launch.py")
    mod, err = importlib.util.module_from_spec(spec), None
    try:
        spec.loader.exec_module(mod)
    except _Done:
        pass
    except BaseException as e:  # SystemExit from stop() or --selftest, or a crash at start
        err = e
    finally:
        os._exit, sys.argv = real_exit, real_argv
        os.chdir(cwd)
    return mod, err


def mkpdf(path, pages=1):
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        from pypdf import PdfWriter
        w = PdfWriter()
        for _ in range(pages):
            w.add_blank_page(72 + pages, 72)
        with open(path, "wb") as f:
            w.write(f)
    except ImportError:
        path.write_bytes(b"%PDF-1.4\n" + b"%" * pages + b"\n%%EOF\n")


def profile_dirs():
    base = Path(os.environ.get("LOCALAPPDATA", "")) / "ClaimViewer"
    return {p for p in base.glob("p-*")} if base.is_dir() else set()


def api_layer(root):
    say("Layer 2: launch.py Api on a temp copy")
    if not (root / "launch.py").exists():
        skip("api", "launch.py missing")
        return
    before = profile_dirs()
    tmp = Path(tempfile.mkdtemp(prefix="bughunt-api-"))
    shutil.copy2(root / "launch.py", tmp / "launch.py")
    (tmp / "index.html").write_text("<html></html>")  # without it launch.py opens a blocking MessageBox
    (tmp / "pdf").mkdir()
    if (root / "library.json").exists():
        shutil.copy2(root / "library.json", tmp / "library.json")
    pdf, libp = tmp / "pdf", tmp / "library.json"
    try:
        mod, err = load_launch(tmp)
        if err:
            add("HIGH", "api", "launch.py crashes at start on the real library.json", repr(err))
            return
        mod, err = load_launch(tmp, ["--selftest"])
        if not (isinstance(err, SystemExit) and err.code == 0):
            add("HIGH", "api", "launch.py --selftest fails on the real library.json", repr(err))
        mod, _ = load_launch(tmp)
        api = mod.Api()

        def reset(items=None):
            shutil.rmtree(pdf, ignore_errors=True)
            pdf.mkdir()
            libp.write_text(json.dumps({"version": 1, "collections": [], "items": items or {}}), encoding="utf-8")

        def src(name, pages=1, sub="in"):
            p = tmp / sub / name
            mkpdf(p, pages)
            return str(p)

        def case(title, fn):
            try:
                fn()
            except Exception as e:
                add("LOW", "api", f"test crashed: {title}", f"{type(e).__name__}: {e}")

        def t_case_collision():
            reset()
            a, b = src("Smith.pdf", 1, "s1"), src("smith.pdf", 2, "s2")
            r = api.import_pdfs("", paths=[a, b])
            on_disk = sorted(f.name for f in pdf.iterdir())
            if len(on_disk) < len(r["added"]):
                add("HIGH", "api", "importing Smith.pdf and smith.pdf overwrites the first PDF",
                    f"items {r['added']}, files on disk {on_disk}. while-loop compares ids case-sensitively; NTFS does not.")
            reset()
            api.import_pdfs("", paths=[a])
            r = api.import_pdfs("", paths=[b])
            on_disk = sorted(f.name for f in pdf.iterdir())
            if len(on_disk) < 2 and len(json.loads(libp.read_text())["items"]) >= 2:
                add("HIGH", "api", "importing smith.pdf after Smith.pdf (separate calls) overwrites Smith.pdf",
                    f"files on disk {on_disk}")
        case("case collision", t_case_collision)

        def t_dup_name():
            reset()
            r = api.import_pdfs("", paths=[src("a.pdf", 1, "s1"), src("a.pdf", 2, "s2")])
            if sorted(r["added"]) != ["a", "a (2)"] or len(list(pdf.iterdir())) != 2:
                add("MED", "api", "two files with the same name are not both kept", r["added"])
        case("same name twice", t_dup_name)

        def t_partial():
            reset()
            try:
                r = api.import_pdfs("", paths=[src("g1.pdf"), str(tmp / "in" / "missing.pdf"), src("g2.pdf")])
                got = r.get("added")
            except Exception as e:
                got = f"raised {type(e).__name__}"
            items = json.loads(libp.read_text())["items"]
            if isinstance(got, str) or len(items) < 2:
                add("MED", "api", "one unreadable file aborts the whole import and strands copied PDFs",
                    f"result {got}; library has {len(items)} item(s); {len(list(pdf.iterdir()))} PDF(s) now sit in pdf\\ unlisted")
        case("partial failure", t_partial)

        def t_samefile_case():
            reset()
            f = pdf / "z.pdf"
            mkpdf(f)
            alt = str(f).replace("\\pdf\\", "\\PDF\\").replace("z.pdf", "Z.PDF")
            try:
                api.import_pdfs("", paths=[alt])
            except Exception as e:
                add("LOW", "api", "picking a PDF already in pdf\\ with different path casing raises",
                    f"{type(e).__name__}: {e} (the same-file guard compares abspath case-sensitively)")
        case("same file, other casing", t_samefile_case)

        def t_nonpdf():
            reset()
            e = tmp / "in" / "empty.pdf"
            e.parent.mkdir(exist_ok=True)
            e.write_bytes(b"")
            r = api.import_pdfs("", paths=[str(e)])
            if r.get("added"):
                add("LOW", "api", "a 0-byte file named .pdf is added to the library", "the viewer fails only when it is clicked")
        case("empty pdf", t_nonpdf)

        def t_unicode():
            reset()
            r = api.import_pdfs("", paths=[src("Ünï — çödé 100% #1.pdf")])
            sj = (tmp / "sources.js").read_text(encoding="utf-8")
            if r.get("added") != ["Ünï — çödé 100% #1"] or "Ünï — çödé 100% #1" not in sj:
                add("MED", "api", "a Unicode / % / # file name is not imported cleanly", r.get("added"))
        case("unicode name", t_unicode)

        def t_poison():
            variants = {"item is a string": {"x": "oops"}, "item is null": {"x": None},
                        "title is a number": {"x": {"title": 5, "collections": []}}}
            crashed = []
            for label, items in variants.items():
                reset()
                api.save_library(json.dumps({"version": 1, "collections": [], "items": items}))
                _, e2 = load_launch(tmp)
                if e2:
                    crashed.append(label)
            reset()
            if crashed:
                add("HIGH", "api", "save_library can write a library.json that stops the app from starting",
                    f"{eg(crashed)}. It writes the file first, validates items inside write_sources afterwards, and launch.py "
                    "then calls write_sources unguarded at start.")
        case("poisoned library", t_poison)

        def t_corrupt():
            reset()
            api.import_pdfs("", paths=[src("keep1.pdf"), src("keep2.pdf")])
            txt = libp.read_text(encoding="utf-8")
            libp.write_text(txt[: len(txt) // 2], encoding="utf-8")
            r = api.import_pdfs("", paths=[src("new.pdf")])
            left = json.loads(libp.read_text())["items"]
            baks = [f.name for f in tmp.glob("library.json.*") if not f.name.endswith(".tmp")]
            if len(left) < 3 and not baks:
                add("MED", "api", "a damaged library.json is read as empty and then overwritten, no backup",
                    f"2 readings before, {len(left)} after the next import; backups: {baks}")
            reset()
            api.import_pdfs("", paths=[src("keep1.pdf")])
            libp.write_bytes(BOM + libp.read_bytes())
            if mod.read_lib()["items"] == {}:
                add("MED", "api", "a library.json saved WITH a BOM (PowerShell 5.1 Set-Content -Encoding utf8) reads as empty",
                    "the next import then replaces the whole library")
        case("corrupt library", t_corrupt)

        def t_pages():
            reset()
            fails = []

            def w(k):
                for j in range(20):
                    r = api.save_pages(json.dumps({f"id{k}": j + 1}))
                    if not r.get("ok"):
                        fails.append(r.get("error"))
            ts = [threading.Thread(target=w, args=(k,)) for k in range(16)]
            [t.start() for t in ts]
            [t.join() for t in ts]
            if fails:
                add("MED", "api", f"save_pages failed {len(fails)} of 320 concurrent calls",
                    f"{eg(set(fails), 2)}. All calls share one last-pages.json.tmp.")
            if (tmp / "last-pages.json.tmp").exists():
                add("LOW", "api", "save_pages leaves last-pages.json.tmp behind after concurrent calls")
            for bad in ("[1,2]", "not json", '{"a":"x","b":-3}'):
                r = api.save_pages(bad)
                if bad == '{"a":"x","b":-3}' and r.get("count") != 0:
                    add("LOW", "api", "save_pages keeps non-positive or non-numeric pages", r)
        case("save_pages", t_pages)

        def t_inject():
            reset()
            api.save_library(json.dumps({"version": 1, "collections": [], "items": {"a": {"title": "x</script><b>", "collections": []}}}))
            s = (tmp / "sources.js").read_text(encoding="utf-8")
            if "</script" in s.lower():
                add("HIGH", "api", "a reading title containing </script> ends the sources.js tag early")
        case("script injection", t_inject)

        def t_folder():
            shutil.rmtree(pdf, ignore_errors=True)
            try:
                api.open_library_folder()
            except Exception as e:
                add("LOW", "api", "open_library_folder raises when pdf\\ does not exist", f"{type(e).__name__}: {e}")
            pdf.mkdir(exist_ok=True)
        case("open folder", t_folder)

        def t_savepdf():
            t = tmp / "keep.pdf"
            t.write_bytes(b"KEEP")
            mod.win.result = str(t)
            try:
                api.save_pdf("keep.pdf", "!!!not-base64!!!")
            except Exception:
                pass
            if t.stat().st_size == 0:
                add("LOW", "api", "save_pdf truncates the chosen file before it decodes the data",
                    "bad base64 over an existing file leaves 0 bytes. Decode first, then open.")
            mod.win.result = ""
            if api.save_pdf("x.pdf", "") != "":
                add("LOW", "api", "save_pdf does not return '' when the dialog is cancelled")
        case("save_pdf", t_savepdf)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        for p in profile_dirs() - before:
            shutil.rmtree(p, ignore_errors=True)
        sys.modules.pop("webview", None)


# --------------------------------------------------------------------------- layer 3: UI over CDP

def link_tree(src, dst):
    dst.mkdir()
    for f in src.iterdir():
        if f.is_file():
            try:
                os.link(f, dst / f.name)  # same volume: instant, no extra space; a delete in the copy keeps the original
            except OSError:
                shutil.copy2(f, dst / f.name)


def ui_layer(root, o):
    say("Layer 3: UI (copy of the exe driven over CDP)")
    node, exe = shutil.which("node"), root / "ClaimViewer.exe"
    if not node:
        skip("ui", "node not on PATH")
        return
    if not exe.exists() or not (root / "index.html").exists():
        skip("ui", "ClaimViewer.exe or index.html missing")
        return
    before = profile_dirs()
    tmp = Path(tempfile.mkdtemp(prefix="bughunt-ui-"))
    proc = None
    try:
        for f in ("ClaimViewer.exe", "index.html", "library.json"):
            if (root / f).exists():
                shutil.copy2(root / f, tmp / f)
        shutil.copytree(root / "lib", tmp / "lib")
        link_tree(root / "pdf", tmp / "pdf")
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
        s.close()
        env = dict(os.environ, WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS=f"--remote-debugging-port={port}")
        proc = subprocess.Popen([str(tmp / "ClaimViewer.exe")], cwd=tmp, env=env)
        t0, ready = time.time(), False
        while time.time() - t0 < 60 and not ready:
            time.sleep(1)
            try:
                tg = json.load(urllib.request.urlopen(f"http://127.0.0.1:{port}/json", timeout=2))
                ready = any(t.get("type") == "page" and t.get("url", "").startswith("file:") for t in tg)
            except Exception:
                pass
        if not ready:
            add("HIGH", "ui", "the app window never exposed a page within 60 s", "exe copy did not start, or WebView2 refused the debug port")
            return
        args = [node, str(HERE / "bughunt_ui.mjs"), str(port), str(tmp)] + (["--quick"] if o.quick else [])
        r = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", timeout=420)
        n = 0
        for line in r.stdout.splitlines():
            if line.startswith("CHK\t"):
                c = json.loads(line[4:])
                n += 1
                if c.get("skip"):
                    skip("ui", f"{c['name']}: {c.get('detail', '')}")
                elif not c["ok"]:
                    add(c.get("sev", "MED"), "ui", c["name"], c.get("detail", ""))
                else:
                    say(f"  ok   {c['name']}")
        if r.returncode not in (0, 1) or n == 0:
            add("MED", "ui", "the UI script did not finish normally", (r.stderr or r.stdout)[-600:])
    except subprocess.TimeoutExpired:
        add("MED", "ui", "the UI script timed out after 7 minutes", "a check hung; the app may be deadlocked")
    finally:
        if proc:
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], capture_output=True)
            time.sleep(1)
        shutil.rmtree(tmp, ignore_errors=True)
        for p in profile_dirs() - before:
            shutil.rmtree(p, ignore_errors=True)


# --------------------------------------------------------------------------- report

NOT_TESTED = [
    "Whether each quote really sits on its pdf_page (verify.py's job; this script checks page ranges only).",
    "The native Open/Save dialogs, the Inno installer, and the first-run experience on a clean PC.",
    "Right-click highlights and text selection inside the PDF canvas.",
    "Anything that needs network (the Wiktionary lookup).",
    "Visual layout quality: this finds overflow and runtime errors, not ugly spacing.",
]


def write_report(root, t0, o):
    counts = collections.Counter(f[0] for f in FINDINGS)
    order = {s: i for i, s in enumerate(SEVS)}
    FINDINGS.sort(key=lambda f: (order[f[0]], f[1]))
    L = [f"# Claim Viewer bug hunt", "",
         f"Run {time.strftime('%Y-%m-%d %H:%M')} on `{root}` in {time.time() - t0:.0f} s. "
         f"HIGH {counts['HIGH']}, MED {counts['MED']}, LOW {counts['LOW']}, INFO {counts['INFO']}.", ""]
    for sev in SEVS:
        rows = [f for f in FINDINGS if f[0] == sev]
        if rows:
            L += [f"## {sev} ({len(rows)})", ""]
            for _, area, title, detail in rows:
                L.append(f"- **[{area}] {title}**" + (f"\n  {detail}" if detail else ""))
            L.append("")
    L += ["## Not tested (UNTESTED, not passed)", ""]
    L += [f"- {a}: {w}" for a, w in SKIPPED] + [f"- {x}" for x in NOT_TESTED]
    out = HERE / "bughunt-report.md"
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    return out, counts


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--app", default=str(HERE.parent))
    ap.add_argument("--no-ui", action="store_true")
    ap.add_argument("--no-pdf", action="store_true")
    ap.add_argument("--quick", action="store_true")
    o = ap.parse_args()
    root = Path(o.app).resolve()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    t0 = time.time()
    static_layer(root, o)
    api_layer(root)
    if o.no_ui:
        skip("ui", "--no-ui")
    else:
        ui_layer(root, o)
    out, counts = write_report(root, t0, o)
    say(f"\nHIGH {counts['HIGH']}  MED {counts['MED']}  LOW {counts['LOW']}  INFO {counts['INFO']}   ->  {out}")
    for sev, area, title, _ in FINDINGS:
        if sev in ("HIGH", "MED"):
            say(f"  {sev:4} [{area}] {title}")
    sys.exit(1 if counts["HIGH"] else 0)


if __name__ == "__main__":
    main()
