# Claim Viewer

Read a PDF, save passages as claims, tag them, and see how the claims connect. It runs on your own computer: your PDFs and claims are never uploaded.

![Claim list next to the PDF, with the quotes highlighted in the page](docs/screenshot-list.png)

*Sample data: the two "papers" in these screenshots are invented placeholder text.*

## Why this exists

Zotero keeps your PDFs and highlights, but it does not draw a graph of how the claims across your readings fit together. I also did not want to keep switching back to Obsidian while reading. So this is a small viewer that does the reading, the tagging and the graph in one place. It was built with Claude Code, under my supervision.

## What it does

- **Read** PDFs in the app, with zoom, fit width, four highlight colors, and Save PDF (your highlights are written into the PDF as real highlight annotations).
- **Save claims.** Select 20 or more characters, right-click, and choose **Add as claim** (or press Alt+A). Selecting alone never creates a claim. Double-click a quote to fix its wording.
- **Tag claims** with a role, one or more pathways, a Q1 factor, a Q2 outcome, the direction of the change (+, -, mixed, none), a PDF page and a section.
- **Filter and group** the list by those tags, by free text, by reading, by kind of evidence, or by own versus cited claim. (Kind of evidence is set only by the optional pipeline below, not in the editor.)
- **Graph them.** *Layers* draws Q1 factors, pathways and Q2 outcomes as columns, with a line wherever claims carry both tags. A box or line shows how many claims it stands for; click one to list them. *Claim network* links up to 60 claims at a time by similar wording or shared tags.
- **Edit your own lists** (pencil button): rename, add or remove pathways, Q1 factors and Q2 outcomes. Claims you tagged with a renamed label follow the new name.
- **Export and import** your edits as `claim-edits.json` (download and upload buttons).

![Graph of pathways, factors and outcomes](docs/screenshot-graph.png)

### How the tags are meant to be used

The tag set came from a literature review that compares several *pathways* (variants of one process):

| Tag | Meaning |
|---|---|
| **Pathway** | A variant you compare, for example "FDI-led" or "developmental state". |
| **Q1 factor** | A cause: why the variants differ. |
| **Q2 outcome** | An effect: what a variant does. |
| **Direction** | The sign of change in the *named* outcome (+ rises, - falls), never "good" or "bad". |

You define the pathway, factor and outcome lists yourself. The Q1 and Q2 labels in the interface are fixed in this version. [`vocab.thesis.json`](vocab.thesis.json) is a filled-in example (reindustrialization pathways), and it also holds the tagging rules written out in words.

## Use it without installing anything

1. Copy the [`reader/`](reader) folder anywhere.
2. Put your PDFs in `reader/pdf/`.
3. List each PDF in `reader/sources.js` (`id` = the file name without `.pdf`):
   ```js
   window.SOURCES = [
     { id: "smith-2020", title: "Smith 2020" },
   ];
   ```
4. Double-click `reader/index.html`.

When you open it by double-click, the browser cannot read the `pdf` folder by itself. The first time, a yellow banner asks you to pick the `pdf` folder. Only Chromium-based browsers (Chrome, Edge) have been checked; others may work but are untested.

## Use it as a Windows app

1. Download [`ClaimViewer-Setup-1.0.0.exe`](ClaimViewer-Setup-1.0.0.exe) and run it.
2. Pick the folder (default: `Documents\Claim Viewer`) and, if you want, a Desktop shortcut. It always adds a Start menu shortcut.
3. Put your PDFs in the `pdf` folder inside it and list them in `sources.js`.
4. Open **Claim Viewer** from the Start menu. It opens its own window (no browser) and stops when you close it.

The install folder is also the viewer folder: the app serves the `index.html` that sits next to `ClaimViewer.exe`. To use a viewer you built with `build.py`, replace `index.html` there. Setup never overwrites `index.html` or `sources.js`, and never deletes them, `pdf`, or your saved claims when you upgrade or uninstall.

Needs the Microsoft WebView2 runtime (already on Windows 11 and current Windows 10).

## Build the installer yourself

```
build_exe.bat
```

Needs Python 3 and [Inno Setup 6](https://jrsoftware.org/isinfo.php) (`winget install JRSoftware.InnoSetup`). The script refreshes `reader/index.html` from `template.html`, then builds `release/ClaimViewer.exe` (PyInstaller) and `release/ClaimViewer-Setup-<version>.exe`. Change the version in `ClaimViewer.iss`.

## Optional: fill the viewer with claims you prepared

If you already have claims as quotes in JSON (written by hand, or extracted by a script or an AI assistant), two scripts check them against the PDFs and build a ready-filled `index.html`. You do not need this to use the viewer.

```
pip install -r requirements.txt
python verify.py          # checks every quote against the PDF text
python build.py           # writes index.html
python -m http.server 8000
```

Then open <http://localhost:8000> (PDFs cannot load from `file://`). Everything lives next to the scripts:

| Input | What it is |
|---|---|
| `sources.json` | `[{"id": "smith-2020", "kind": "paper", "pdf": "papers/smith-2020.pdf"}]`. `pdf` is the original file; keep it outside `pdf/`. Add `"cite_offset": N` if printed page numbers differ from PDF page numbers by N. |
| `vocab.json` | The pathway, factor, outcome, role, evidence and direction lists. Start from [`vocab.starter.json`](vocab.starter.json) or [`vocab.thesis.json`](vocab.thesis.json). |
| `claims/<id>.json` | `{"claims": [{"id": "c1", "quote": "...", "role": "Q2", "pathway": [1], "outcome": "employment", "direction": "+"}]}`. Other fields the viewer reads: `gist`, `factor`, `evidence`, `own_claim`, `expected`, `section`. |
| `overrides.json` | Optional. `{"c1": {"direction": "-"}}` changes fields of a claim without editing its file. |

`verify.py` marks each quote `exact`, `anchored` (only its first and last words matched), `ambiguous` (it appears more than once) or `failed`. A failed quote is never rewritten. It also writes `claims/<id>.verified.json` and a copy of the PDF with the quotes highlighted to `pdf/<id>.pdf`. `build.py` adds the links between readings: similar claims by word overlap (TF-IDF, not meaning), and claims on the same outcome with the opposite sign. These links appear only for sources built this way.

## Files

| Path | Purpose |
|---|---|
| `template.html` | The whole viewer. A built `index.html` is this file with its data filled in. |
| `reader/` | A ready, empty copy to start from (made by `make_reader.py`). |
| `make_reader.py`, `vocab.starter.json` | Rebuild `reader/index.html` from the template with an empty library. |
| `app/launch.py` | The Windows app: a native window (WebView2) around a small local server. |
| `app/setup_shortcuts.py` | Small shortcut-only setup helper (the installer below covers this). |
| `ClaimViewer.iss`, `build_exe.bat` | Inno Setup script and build script for the Windows installer. |
| `ClaimViewer-Setup-1.0.0.exe` | The prebuilt, unsigned Windows installer. |
| `verify.py`, `build.py`, `requirements.txt`, `vocab.thesis.json` | The optional claims pipeline and an example vocabulary. |
| `docs/` | Screenshots used in this README. |

## Known limits

- The reader loads pdf.js (and pdf-lib, when you save a PDF) from cdnjs, so it needs internet. These script downloads are the only network requests it makes.
- Your edits live in the browser or app storage for that folder. The Windows app keys storage to the folder path, so moving the folder loses them: use Export first, then Import.
- Claims saved in `index.html` over `file://` do not appear in the app: use Export and Import.
- The Q1/Q2 wording in the interface is fixed (see above).
- Save PDF writes a copy of the PDF with your highlights as real highlight annotations. Each highlight carries your note (or the highlighted text) as its comment. The app opens a PDF-only save dialog.
- The exe and the installer are unsigned, so Windows SmartScreen may warn.
- Do not commit copyrighted PDFs. `.gitignore` already skips `reader/pdf/*.pdf` and the pipeline's `pdf/`, `papers/` and `claims/` folders.

## License

[MIT](LICENSE)
