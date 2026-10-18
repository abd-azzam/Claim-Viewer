"""Write reader/index.html: template.html with an empty library and the starter vocab.

reader/ is the ready-to-copy empty viewer (and what the Windows installer ships).
Re-run after editing template.html or vocab.starter.json:  python make_reader.py
An existing reader/sources.js is never overwritten.
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "reader"
SOURCES_JS = """// List your PDFs here. id = the file name in the pdf folder, without ".pdf". title is optional.
window.SOURCES = [
  // { id: "smith-2020", title: "Smith 2020" },
];
"""

vocab = json.loads((HERE / "vocab.starter.json").read_text(encoding="utf-8"))
blob = json.dumps({"vocab": vocab, "sources": []}, ensure_ascii=False).replace("</", "<\\/")
(OUT / "pdf").mkdir(parents=True, exist_ok=True)
(OUT / "index.html").write_text((HERE / "template.html").read_text(encoding="utf-8").replace("/*DATA*/null", blob), encoding="utf-8")
if not (OUT / "sources.js").exists():
    (OUT / "sources.js").write_text(SOURCES_JS, encoding="utf-8")
print("reader/index.html written")
