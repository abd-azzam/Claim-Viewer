# Claim Viewer bug hunt

Run 2026-10-23 09:30 on `C:\Apps\ClaimViewer` in 145 s. HIGH 0, MED 0, LOW 0, INFO 4.

## INFO (4)

- **[claims] 14 reading(s) have no claims file**
  ezrow-2010-ch4-6; gallagher-1991; laakso-taagepera-1979; norris-1997; norris-2004-ch8-9; shugart-wattenberg-2001-ch1-2 ... +8 more
- **[claims] status counts {'exact': 7084, 'failed': 43, 'anchored': 39, 'ambiguous': 12}; roles {'OTHER': 875, 'TYPOLOGY': 591, 'Q1': 3272, 'Q2': 2227, 'A': 131, 'B': 82}**
- **[pdf] pypdf rejects these but the viewer opens them (cyclic page tree, not a defect)**
  ezrow-2010-ch4-6 (PdfReadError: Detected cyclic page references.); norris-2004-ch8-9 (PdfReadError: Detected cyclic page references.)
- **[template] Api methods the page never calls**
  open_library_folder

## Not tested (UNTESTED, not passed)

- Whether each quote really sits on its pdf_page (verify.py's job; this script checks page ranges only).
- The native Open/Save dialogs, the Inno installer, and the first-run experience on a clean PC.
- Right-click highlights and text selection inside the PDF canvas.
- Anything that needs network (the Wiktionary lookup).
- Visual layout quality: this finds overflow and runtime errors, not ugly spacing.
