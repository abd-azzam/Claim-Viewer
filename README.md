# Claim Viewer

Windows desktop library for PDFs, claims, notes, research chat and Word citations.

## Install

1. Run **ClaimViewer-Setup-2.6.0.exe**. Python is not required.
2. Keep the suggested folder, or choose a writable folder. Upgrades retain the previous installation folder.
3. Setup installs Microsoft Edge WebView2 if missing. That step needs an internet connection.
4. For desktop Word, select **Add Claim Viewer to Microsoft Word's ribbon**. Save documents and close Word before continuing. Approve the Windows administrator prompt for the Word component.
5. Open Claim Viewer from Start and import PDFs in **Library**. Open Word normally to see its **Claim Viewer** tab.

Requirements: Windows 10 x64 (1809 or later) or Windows 11. Word integration is optional and requires desktop Word for Windows, Office 2016 or later, with bibliography styles installed. Both Word bitnesses are packaged. Word for the web and macOS Word are not supported by this installer.

The installer includes an empty library, offline PDF assets, the app and Word component. It excludes the developer's PDFs, claims, conversations, API keys and local Word credentials. This release is unsigned; verify the download source and compare the adjacent SHA256 file before sharing or installing it.

## First use

- **Library:** import PDFs and organize folders. Fill title, author and year for citations. The DOI search icon performs an exact DOI lookup; missing result fields do not erase existing metadata.
- **Claims:** select PDF text to create a claim. Use List, Graph or Library as the starting view.
- **Settings:** the button stays at the bottom of the left pane in every workspace. Configure appearance, AI, Word and backups there.
- **AI:** add a provider and your API key in **Settings > AI**, then open a reading and choose Ask AI. OpenCode connections list the models provided by their endpoint. Provider charges and limits apply.
- **Thinking:** expand the block above an answer for provider-supplied reasoning, when available, or request status. Some models return only an answer. Hidden internal reasoning is not available. Elapsed time measures the request, not the model's reasoning duration. Returned reasoning is retained with the conversation.

Asking AI sends the PDF text and recent conversation to the selected provider. PDF reading and local organization work offline. AI, DOI lookup and online text-to-speech need their respective services. Optional OCR needs Tesseract installed separately.

## Word

Save the document before using its pane. The **Claim Viewer** ribbon loads at Word startup without My Add-ins. It has **Insert citation**, **Add bibliography**, **Refresh** and **Citation style**.

Browse library folders or search, select a source, choose parenthetical/narrative form and optionally enter a printed page or range. Apply **American Political Science Association (APSA)** from Citation style for APSA author-date output. Verified examples include `(Alami 2023, 12)` and `Alami (2023, 12)`. APA and Word's other installed styles remain available.

Citations use native CITATION fields; bibliography uses BIBLIOGRAPHY. Add bibliography once; later citation operations update it. Narrative citations omit titles, while bibliography retains them. Refresh repairs older Claim Viewer narrative fields that included titles. Actions are bound to the saved document hosting the pane and reject mismatched or closed documents.

## Update and back up

Use Settings' backup action before updating. Save and close Word. Run the new installer into the existing app folder. Library, PDFs and local state are preserved. First launch refreshes the interface from the installed template while retaining embedded research data; `index.html.previous` keeps the prior page.

Settings' **Open data folder** action locates your data. A legacy Program Files executable can use another folder through `data-root.txt`. Library deletions update counts and retain recovery files in `data/deleted-readings`. Restore manually with the app closed, or restore a backup; copying back only a PDF does not restore its library record.

Backup ZIPs include current library/PDFs, claims, notes and reading positions, but exclude API credentials. Windows-protected keys are account-specific; enter them again on another computer. Uninstall through Windows Installed apps. Word removal can need administrator approval. Library files, PDFs and Word documents are retained. Old manual Program Files installs can have a separate uninstall entry.

## Troubleshooting

- **Blank window:** rerun setup or install [Microsoft WebView2 Evergreen Runtime](https://developer.microsoft.com/microsoft-edge/webview2/), then reopen.
- **Word tab missing:** save/close Word; use **Settings > Word Add-in > Install Word add-in**, approve the Windows prompt and restart Word normally. Repair updates the component path and removes only stale Claim Viewer registrations.
- **Word setup canceled:** the main app remains installed. Retry in Settings. Details: `word/installation-error.txt`, `word/ribbon-install-result.json`, `word/service-startup.log` in the app folder.
- **APSA missing:** reinstall Word integration and restart Word. APSA is generated from that computer's Chicago renderer and installed into Word's style folders.
- **Models unavailable:** check provider URL/key/service and refresh models. The saved model remains available if catalog discovery fails. Missing reasoning is not an error.
- **Empty library:** check which installation folder you opened. Installations use separate data unless configured with `data-root.txt`.

## Build a release

Maintainers need Windows x64, Python 3.11, Word's Office/Extensibility interop assemblies, the .NET Framework C# compiler and [Inno Setup 6](https://jrsoftware.org/isinfo.php).

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements-build.txt
powershell -ExecutionPolicy Bypass -File tools\build-release.ps1 -Python .venv\Scripts\python.exe
```

Override `-ISCC` if needed. The script builds the component/executable, creates fresh distribution staging, verifies required assets and account-data exclusions, verifies Microsoft's WebView2 bootstrapper signature, compiles setup and writes SHA256. Share the setup EXE and its checksum, never the working app folder. The release package does not redistribute Microsoft's bibliography stylesheet.

Native app/Word checks ran on the development computer. Missing-runtime installation and a separate clean Windows computer still need a fresh-machine check; this README does not guarantee untested environments.
