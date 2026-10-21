# Claim Viewer

Read a PDF, save passages as claims, tag them, connect them to other readings, keep Zettelkasten-style notes, and see how it all fits together in a graph.

It runs on your own computer. Your PDFs, claims and notes are never uploaded. The only network request is an optional dictionary lookup of one word, sent to Wiktionary (see [Known limits](#known-limits)).

![Claim list next to the PDF, with the quotes highlighted in the page](docs/screenshot-list.png)

*Sample data: both papers, their text and their claims are invented.*

## Why this exists

Zotero keeps your PDFs and highlights, but it does not draw a graph of how the claims across your readings fit together, and it has no place for your own reading notes. This is a small viewer that does the reading, the tagging, the notes and the graph in one place. It was built with Claude Code and with Hermes (connected to DeepSeek Flash), under my supervision.

## Get started

### Windows app

1. Download [`ClaimViewer-Setup-2.1.0.exe`](release/ClaimViewer-Setup-2.1.0.exe) and run it. It is unsigned, so Windows SmartScreen may warn.
2. Pick the install folder (default `C:\Apps\ClaimViewer`). A Desktop shortcut is offered but not ticked; the Start menu shortcut is always added.
3. Open **Claim Viewer** from the Start menu. It opens its own window (no browser), centred on the screen and shrunk to fit if the screen is small.
4. Open the **Library** tab, add a folder, and use **Add PDFs** on it. The app copies the PDFs into the `pdf` folder of the install folder and records them in `library.json`.

The install folder is also the viewer folder. The app opens the `index.html` in it and rewrites `sources.js` from `library.json` every time it starts, so do not edit `sources.js` by hand. To use a page built with `build.py`, replace `index.html` there. When you upgrade or uninstall, Setup never overwrites or deletes `index.html`, `sources.js`, `pdf` or `data`. Your saved edits live outside the install folder, in the app's own storage under `%LOCALAPPDATA%\ClaimViewer`.

Needs the Microsoft WebView2 runtime (already on Windows 11 and current Windows 10). Confirmations are drawn inside the app. The two file dialogs (import PDFs, save PDF) are native Windows dialogs owned by the app window, so they cannot open behind it.

### In a browser (no install)

1. Put your PDFs in `reader/pdf/` and list each one in `reader/sources.js` (`id` = the file name without `.pdf`). Name every PDF with author, year and title, because the citation copy parses them from the title, for example `Alami (2023) - Ten theses on the new state capitalism`:
   ```js
   window.SOURCES=[
     {id:"smith-2020", title:"Smith (2020) - Why States Build Capacity"}
   ];
   ```
2. Serve the folder and open it:
   ```
   python -m http.server 8000 --directory reader
   ```
   then go to <http://localhost:8000>. Any static file server works.

Do not open `reader/index.html` by double-click. Over `file://` the page cannot read the PDF, says "PDF not found in the pdf folder", and shows the PDF in the browser's plain viewer, where you cannot make claims. Only Chromium-based browsers (Chrome, Edge) have been checked. In a browser your edits live in that browser's storage for that address.

## What it does

### Reading

- **Library** like Zotero: nested folders (collections), each PDF filed in one or more of them, with add-folder, rename, and per-folder PDF import. The reading menu, the list and the graph follow the collection you pick.
- **PDF pane**: zoom, fit width, and full screen (Esc or the same button leaves it). The page box above the PDF shows `8 / 50`; type a number and press Enter to jump. Left/right arrow or PageUp/PageDown turn pages (ignored while you type in a field).
- **Resume where you left off.** The page is saved as soon as scrolling stops and again when the window closes.
- **Five highlight colors**, each with a meaning: blue definition / term, yellow key argument, orange important, green method / example, red critique of other work. *Save PDF* writes your highlights into a copy of the PDF as real highlight annotations; *Clear all highlights* removes them from the open reading.
- **Dictionary**: right-click a word in the claim or note lists (or select one word in the PDF and choose *Define*) for its English definition from Wiktionary. Results are cached.

### Claims

- **Add a claim.** Select 20 or more characters, right-click, and choose **Add as claim** (or press Alt+A). Double-click a quote to fix its wording.
- **Tags.** Role, pathways, a determinant, an effect, the direction of the change, kind of evidence and section. You name the three graph columns (default Determinant / Pathway / Effect) per collection in **Edit lists**, and **+ Add section** there adds a layer of its own.
- **Pathways are a chip field**, like Determinant and Effect: type a name and press Enter, or pick a suggestion. The suggestions are exactly the pathway list of the collection you are in, so a folder never offers another folder's terms. Pathways are stored by name, and renaming one in the Lists dialog renames it on every claim that carries it.
- **Connect claims across readings.** In the claim editor, link a claim to a specific claim (and its paragraph) in another reading, including readings outside the current folder. There are four connection models, each with its own types and colors: *Stance* (supports / challenges / qualifies), *Causal* (causes / mediates / moderates / prevents), *Argument* (premise / rebuttal / counterexample / extension) and *Bibliographic* (cites / extends / replicates / supersedes). If you rename a reading, its links retarget by title.
- **Copy with citation.** The **Copy** chip on a card copies the sentence ending `(Author, Year, p. N)`, parsed from the reading's title (`(Author, p. N)` if the title has no year). Alt+click a card does the same.
- **Cards.** Every card shows Copy, the PDF page, the role and the pathway. A claim you wrote also shows its determinant, effect, direction, tags, evidence and section. A claim imported from a file shows only the first group. A `failed` or `ambiguous` chip appears when a saved quote could not be matched against the PDF text.
- **To note** on a card starts a note from that claim and files it under the claim's pathway.
- **Filter and group** the list by collection, reading, role, pathway, determinant, effect, direction, evidence, author, links, connected reading, or free text.

### Notes (Zettelkasten)

![Notes: a numbered list on the left, the open note with its tags on the right](docs/screenshot-notes.png)

- The **Notes** tab sits beside **Claims**. Each note quotes a passage, names its reading and page, and carries **tags and nested sub-tags** (`Mainstream Parties › Core Supporters`, any depth). Untagged notes sit under "(no tag)".
- **Note numbers follow the list you are looking at**: 1..N for the notes in view. The stored id never changes, so links and the graph stay correct; child notes branch as 1a, 1aa.
- **Closing keeps what you typed**, title and body, without pressing Save. A note you never fill in is discarded and uses up no number. A note started while a folder is selected stays in that folder.
- **Keyword index** lists every tag with its notes and follows the same filters as the list: collection, reading, tag, sub-tag and the *Find a note* box.
- **Merged readings**: by default every note has its own pill; *Merge readings* joins all notes of one reading into a single pill whose click opens a menu of its notes.

### Graph

![Graph of determinants, pathways and effects](docs/screenshot-graph.png)

- **Layers** draws your named columns, with a line wherever claims carry both tags. Links through an empty pathway are blurred so the real structure stands out.
- **Claim network** links up to 60 claims at a time by similar wording or shared tags.
- **Connected claims** shows the cross-reading connections you declared.
- **Notes** draws tag → sub-tag → note trees. Drag a note onto a tag to re-file it, drag a node onto another of the same kind to swap them, or drop it in the strip below a node to nest it there. **Undo** (30 steps, this session only) and **Delete** sit in the toolbar.

### Safety rails and theme

- **Clear filters** and **Clear all** are separate. *Clear all* deletes only the open reading's claims and highlights, after a confirmation in the app's own dialog (never a browser popup). *Remove this reading from the viewer* leaves the PDF file on your computer.
- **Export and import** your edits as `claim-edits.json` (the download and upload buttons), and **Reset edits** discards them.
- A light and a dark theme; the toggle sits next to the title.

<details><summary>Show the light-theme screenshots</summary>

![Claim list in the light theme](docs/screenshot-list-light.png)

![Graph in the light theme](docs/screenshot-graph-light.png)

![Notes in the light theme](docs/screenshot-notes-light.png)

</details>

## Optional: build a page filled with claims from files

If you already have claims as quotes in JSON (written by hand, or extracted by a script or an AI assistant), `build.py` merges them with a library and writes a ready-filled `index.html` next to itself. You do not need this to use the viewer.

```
pip install -r requirements.txt
python build.py                  # reads library.json and data/ in this folder
python build.py --from <dir>     # reads another folder's library.json and data/
```

| Input | What it is |
|---|---|
| `library.json` | `{"collections": [{"id": "c1", "name": "Readings", "parent": null}], "items": {"smith-2020": {"title": "Smith (2020) - Why States Build Capacity", "collections": ["c1"]}}}`. A collection's `parent` is another collection's id. An item may add `"cite_offset": N` when printed page numbers differ from PDF page numbers by N. |
| `data/claims/<id>.verified.json` | `{"claims": [{"id": "c1", "quote": "...", "role": "Q2", "pathway": ["FDI-led"]}]}`. Other fields it reads: `gist`, `axisA`, `axisB` (older files use `factor` and `outcome`, which still load), `evidence`, `own_claim`, `direction`, `section`, `links`. |
| `data/vocab.json` | The pathway, determinant and effect lists. `build.py` converts numeric pathway ids in older claim files to names with its `pathways` map. |
| `data/overrides.json` | Optional. `{"c1": {"direction": "-"}}` changes fields of a claim without editing its file. |

The PDFs go in `pdf/`, named by item id. `build.py` also computes the "similar / opposite sign" links between readings (word overlap, not meaning). To start a new viewer folder, copy [`reader/`](reader), or rebuild its page with `python app/make_reader.py` (it uses `template.html` and `vocab.starter.json`). [`vocab.thesis.json`](vocab.thesis.json) is a filled-in example vocabulary.

> **Note:** `verify.py`, which checks each extracted quote against the PDF text and writes a highlighted copy, still expects the author's own folder layout: it looks for `ClaimViewer/sources.json` and `ClaimViewer/claims/` one level above this repository, and writes `claims/<id>.verified.json` rather than `data/claims/`. It does not run from a fresh clone yet.

## Build the installer yourself

```
build_exe.bat
```

Needs Python 3 and [Inno Setup 6](https://jrsoftware.org/isinfo.php) (`winget install JRSoftware.InnoSetup`). The script refreshes `reader/index.html` from `template.html`, wipes `dist/`, builds `dist/ClaimViewer.exe` (PyInstaller), stages `dist/` with the empty reader page and the pdf.js libraries, and writes `release/ClaimViewer-Setup-<version>.exe`. The Inno script refuses to package a `dist/index.html` larger than 1 MB, because a page that big is somebody's claims. Change the version in `ClaimViewer.iss`. Git tracks only `release/ClaimViewer-Setup-*.exe`.

To check an installer without touching your own install:

```
python test_installer.py
```

It builds the setup with a throwaway AppId and the name **Claim Viewer (test)**, installs it into a temp folder, checks that the packaged page holds zero readings and that pdf.js is there, then uninstalls and deletes the folder. It closes a running Claim Viewer first (a silent install fails with exit code 5 while the app holds its files) and starts it again afterwards.

## Repository layout

| Path | Purpose |
|---|---|
| `template.html` | The whole viewer. A built `index.html` is this file with its data filled in. |
| `reader/` | A ready, empty viewer: `index.html`, `sources.js`, `lib/` (pdf.js and pdf-lib, so reading works offline) and an empty `pdf/`. |
| `app/launch.py` | The Windows app: a native window (WebView2) that opens `index.html`, plus a small API for importing PDFs and saving `library.json`. |
| `app/make_reader.py` | Rebuilds `reader/index.html` from `template.html` and `vocab.starter.json`. |
| `app/setup_shortcuts.py` | A small shortcut-only setup helper (the installer covers this). |
| `build.py`, `verify.py`, `requirements.txt` | The optional claims pipeline (see above). |
| `ClaimViewer.iss`, `build_exe.bat`, `test_installer.py` | Installer script, build script and installer test. |
| `release/` | The prebuilt installer. |
| `vocab.starter.json`, `vocab.thesis.json` | The starter lists inside `reader/index.html`, and an example vocabulary. |
| `docs/` | Screenshots used in this README, in the dark and light theme. |

## Known limits

- **Offline reading.** pdf.js and pdf-lib ship in `lib/` next to the page. The only network request is a dictionary lookup on Wiktionary, and only for a word that is not already cached. A failed lookup (offline, timeout) is not cached, so the word is tried again next time.
- **Where your edits live.** In the browser or app storage for that folder. The Windows app keys storage to the folder path, so moving the folder loses them: *Export edits* first, then *Import*.
- **Undo** in the note graph holds 30 steps for the current session only. It is deliberately not saved, because a stored stack once rewound the notes to a days-old state.
- **Merged readings.** The merged pill joins a reading's notes into one node, so chains that share a reading but sit on different branches all point at it. Turn *Merge readings* off to keep every note separate.
- **Position.** A normal close never loses your page. A force kill or a power cut can lose the last instant.
- **Missing reader files.** If `lib/pdf.min.js` or `lib/pdf.worker.min.js` is missing, the page says which one and shows the PDF in a plain frame instead of a blank pane.
- **Layout.** In the Notes tab with the PDF pane open on a narrow window, the list drops below the note; close the PDF pane for two columns. The window opens centred on the primary screen, not on the monitor holding the cursor.
- **Unsigned.** The exe and the installer are unsigned, so Windows SmartScreen may warn.
- **Do not commit copyrighted PDFs or your own claims.** `.gitignore` skips `reader/pdf/*.pdf`, a built `index.html`, and the pipeline's `pdf/`, `papers/`, `claims/`, `data/` and `library.json`.

## License

[MIT](LICENSE)
