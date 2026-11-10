# Claim Viewer

Windows desktop library for PDFs, claims, notes, research chat and Word citations.

## Install

1. Run **ClaimViewer-Setup-2.6.3.exe**. Python is not required.
2. Keep the suggested folder, or choose a writable folder. Upgrades retain the previous installation folder.
3. Setup installs Microsoft Edge WebView2 if missing. That step needs an internet connection.
4. For desktop Word, select **Add Claim Viewer to Microsoft Word's ribbon**. Save documents and close Word before continuing. Approve the Windows administrator prompt for the Word component.
5. Open Claim Viewer from Start and import PDFs in **Library**. Open Word normally to see its **Claim Viewer** tab.

Requirements: Windows 10 x64 (1809 or later) or Windows 11. Word integration is optional and requires desktop Word for Windows, Office 2016 or later, with bibliography styles installed. Both Word bitnesses are packaged. Word for the web and macOS Word are not supported by this installer.

The installer includes an empty library, offline PDF assets, the app and Word component. It excludes the developer's PDFs, claims, conversations, API keys and local Word credentials. This release is unsigned; verify the download source and compare the adjacent SHA256 file before sharing or installing it.

## Changes in 2.6.3

- OpenCode Go has its own provider preset, model catalog, and session header. The OpenCode preset uses the separate pay-as-you-go catalog. To refresh the list, select the saved provider in **Settings > AI**, click **Load available models**, then save. A model listed in one catalog may be unavailable in the other.
- Ask AI keeps passage explanations brief and uses the requested page when one is specified. It omits paragraphs without verified excerpts. Choose Fast or More complete citation checking in the composer.
- Citation jumps preserve PDF zoom when the viewer was hidden behind Ask AI.
- All five graph views offer AI drafting with review before saving.
- If Start shows two Claim Viewer shortcuts, open the one for the updated installation and check **Settings > About** for version 2.6.3. Older Program Files builds may lack OpenCode Go support. Back up or migrate their library before removing an old installation.

## Changes in 2.6.2

- The Word pane indents child folders, shows examples beside both citation forms, and accepts undated sources.

- The note editor leaves room at both sides and groups passage actions below the source title.
- Read Aloud uses the visible page margins, so cropped PDFs keep the opening paragraph.
- The Word citation service starts with its own runtime. The question mark beside Claim Viewer opens the tutorial.

- The Word pane puts source search first. Word uses the document's citation style and updates an existing bibliography after each insertion.
- Word repair restarts the citation service, and **Settings > Tutorial** opens the expanded guide.

- Adding a claim to an existing note opens the selected note, including the first or only match.
- OCR makes scanned text selectable in the reader and keeps word positions when you reopen the PDF. Rescan pages processed by an older build to save their positions.
- OCR shows the page being scanned and when it is writing text into the PDF. The scan options wrap to fit the dialog.
- The left pane toggle sits beside the theme button and the right toggle stays in the upper-right corner.
- AI Settings lists OpenAI and Claude (Anthropic). Each provider uses its own API key.
- About shows the installed version. Check for Updates checks GitHub on startup and downloads verified installers for newer stable releases. An in-app notice opens the update page when an installer is ready.
- Claim Viewer has a new Windows app icon.

## Changes in 2.6.1

- Ask AI citation highlights complete the cited sentence without adding surrounding sentences. Citations that span several sentences remain intact.
- A citation click highlights the verified quotations from its answer paragraph as separate passages on the cited page. Gaps stay unhighlighted. Other pages retain their own citation chips. New answers and citation repair can supply several supporting markers for one point.
- AI citation jumps use filled highlights with a visible border.
- Switching tabs or PDFs keeps the active chat available. Questions save immediately, and completed replies save to the reading that started the request.
- Citation highlights are temporary: clicking anywhere outside the chat clears them, pressing Escape clears them, and pressing another citation chip replaces them.
- Ctrl with `+`, `-` or `0`, and Ctrl with the mouse wheel, zoom the PDF page between 50% and 300%. The shortcuts are ignored while typing, and a zoom keeps your place in the reading.
- Provider connections stream returned reasoning and answer text. The writing state remains visible while citations are checked. Providers must support streaming; models can omit reasoning. Long readings processed in parts still use complete-response calls.

Close Claim Viewer after its active request finishes, then install this update and reopen it. Running requests do not resume after closing the app.

Citation sentence boundaries passed 11 regression tests, including the Voltaire example with quotation marks and a footnote marker. Multiple-passage checks cover three separated supporting sentences, excluded gaps, clearing old highlights, citation clicks and retaining multiple repaired markers. Chat persistence, provider protocol handling, PDF lifecycle and the thinking panel passed regression checks. Live WebView2 rendering passed with the actual Sartori PDF: three supporting sentences remained separately highlighted, with visible fill and outlines inside the page. The setup installed into a fresh folder on the development computer, and its packaged executable opened an empty library. Requests with personal provider credentials and installation on a separate clean Windows computer remain unverified; no clean Windows VM was available. Sentence boundaries use punctuation, so unusual PDF formatting can affect them. Older answers can recover separate exact quotations on the cited page; missing or paraphrased support still requires a new answer with explicit citation markers.

## First use

- **Library:** import PDFs and organize folders. Fill title, author and year for citations. The DOI search icon performs an exact DOI lookup; missing result fields do not erase existing metadata.
- **Reading:** zoom with the toolbar buttons, Ctrl `+` / `-` / `0`, or Ctrl with the wheel. The page position is saved per reading, and a citation chip jumps to the cited page and outlines the verified quotation.
- **Notes:** the notes graph draws an idea map, with each topic's notes grouped inside a labelled box; drag a note to arrange it and the arrangement is kept.
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

Compare the installer hash from `Get-FileHash .\ClaimViewer-Setup-2.6.3.exe -Algorithm SHA256` with `ClaimViewer-Setup-2.6.3.exe.sha256` supplied alongside it.

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
