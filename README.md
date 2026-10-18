# Claim Viewer

A small reading tool. Open a PDF, select a passage, right-click, and save it as a claim. Tag each claim, filter the list, and see a graph of pathways, factors and outcomes. It runs on your own computer. Nothing is uploaded.

## Use it (no install)

1. Copy the `reader/` folder anywhere.
2. Put your PDFs in `reader/pdf/`.
3. List each PDF in `reader/sources.js` (`id` = file name without `.pdf`).
4. Double-click `reader/index.html`.

The first time over `file://`, pick the `pdf/` folder when the yellow banner asks.

## Use it as an app (Windows)

1. Download `ClaimViewer-Setup-1.0.0.exe` from the Releases page and run it.
2. Pick the folder (default: `Documents\Claim Viewer`) and, if you want, a Desktop shortcut. It always adds a Start menu shortcut.
3. Put your PDFs in the `pdf` folder inside it and list them in `sources.js`.
4. Open **Claim Viewer** from the Start menu. It opens its own window (no browser) and stops when you close it.

The install folder is also the viewer folder: the app serves the `index.html` that sits next to `ClaimViewer.exe`. To use a viewer you built with `build.py`, replace `index.html` there. Setup never overwrites `index.html` or `sources.js` and never deletes them, `pdf`, or your saved claims when you upgrade or uninstall.

Needs the Microsoft WebView2 runtime (already on Windows 11 and current Windows 10).

## Make a claim

Select 20 or more characters in the PDF, then right-click and choose **Add as claim** (or press Alt+A). Selecting alone never creates a claim. The toolbar has zoom, fit width, Save PDF, four highlight colors and Clear highlights.

## Build the installer yourself

```
build_exe.bat
```

Needs Python 3 and [Inno Setup 6](https://jrsoftware.org/isinfo.php) (`winget install JRSoftware.InnoSetup`). Output goes to `release/`: `ClaimViewer.exe` and `ClaimViewer-Setup-<version>.exe`. Change the version in `ClaimViewer.iss`.

## Files

| File | Purpose |
|---|---|
| `template.html` | The whole viewer. `index.html` is this file with its data filled in. |
| `reader/` | A ready, empty copy to start from. |
| `app/launch.py` | Native window around a local server. |
| `ClaimViewer.iss` | Inno Setup script for the Windows installer (per-user, shortcuts, uninstaller). |
| `build.py`, `verify.py`, `vocab.thesis.json` | Optional pipeline that fills `index.html` with claims from `claims/*.json`. |

## Known limits

- The reader loads pdf.js from cdnjs, so it needs internet.
- Saved claims live in the browser or app storage for that folder. The app keys storage to the folder path, so moving the folder loses them: use Export first, then Import.
- Claims saved in `index.html` over `file://` do not appear in the app: use Export and Import.
- Save PDF writes a copy of the PDF with your highlights as real highlight annotations. Each highlight carries your note (or the highlighted text) as its comment. The app opens a PDF-only save dialog.
- The exe and the installer are unsigned, so Windows SmartScreen may warn.
- Do not commit copyrighted PDFs.
