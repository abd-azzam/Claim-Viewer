"""Build index.html from sources.json, vocab.json and claims/<id>.verified.json (all next to this script).

Needs: pip install -r requirements.txt
Serve this folder (PDFs cannot load from file://):
    python -m http.server 8000      then open http://localhost:8000
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
sources = json.loads((HERE / "sources.json").read_text(encoding="utf-8"))
vocab = json.loads((HERE / "vocab.json").read_text(encoding="utf-8"))
vocab.pop("TODO(human)", None)
over = json.loads((HERE / "overrides.json").read_text(encoding="utf-8")) if (HERE / "overrides.json").exists() else {}  # optional: {claim id: fields to change}

data = {"vocab": vocab, "sources": []}
for s in sources:
    p = HERE / "claims" / f"{s['id']}.verified.json"
    d = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"claims": []}  # keep the source (and its PDF) even with no claims yet
    for c in d["claims"]:
        c.update(over.get(c["id"], {}))
        off = s.get("cite_offset")  # printed page = PDF page - offset (WIDER paper: front matter unnumbered)
        if off and c.get("pdf_page"):
            c["cite_page"] = str(c["pdf_page"] - off) if c["pdf_page"] > off else "front"
    name = Path(s["pdf"]).stem
    data["sources"].append({"id": s["id"], "kind": s["kind"], "title": name, "claims": d["claims"]})

# Related claims by TF-IDF cosine (word overlap, not meaning; zero model cost). Index j = position in the flat list = JS `all`.
import re
import numpy as np
from scipy import sparse
flat = [c for s in data["sources"] for c in s["claims"]]
sid = np.array([i for i, s in enumerate(data["sources"]) for _ in s["claims"]])
docs = [re.findall(r"[a-z]{3,}", (c["quote"] + " " + c.get("gist", "")).lower()) for c in flat]
df = {}
for d in docs:
    for w in set(d):
        df[w] = df.get(w, 0) + 1
voc = {w: i for i, w in enumerate(w for w, n in df.items() if 2 <= n <= 0.2 * len(docs))}
idf = np.zeros(len(voc))
for w, i in voc.items():
    idf[i] = np.log(len(docs) / df[w])
r_, c_, v_ = [], [], []
for r, d in enumerate(docs):
    tf = {}
    for w in d:
        if w in voc:
            tf[voc[w]] = tf.get(voc[w], 0) + 1
    for j, n in tf.items():
        r_.append(r); c_.append(j); v_.append((1 + np.log(n)) * idf[j])
X = sparse.csr_matrix((v_, (r_, c_)), shape=(len(docs), len(voc)))
X = sparse.diags(1 / np.maximum(np.sqrt(X.multiply(X).sum(1)).A1, 1e-9)) @ X
sign = {"+": 1, "-": -1}
outs = np.array([c.get("outcome") or "" for c in flat])
sgn = np.array([sign.get(c.get("direction"), 0) for c in flat])
SIM, TOPK, TOPO = 0.15, 5, 3
for a in range(0, len(flat), 500):
    S = (X[a:a + 500] @ X.T).toarray()
    for k in range(S.shape[0]):
        i, row = a + k, S[k]
        row[sid == sid[i]] = -1  # other papers only
        c = flat[i]
        top = [j for j in np.argsort(-row)[:TOPK] if row[j] >= SIM]
        if top:
            c["rel"] = [[int(j), round(float(row[j]), 2)] for j in top]
        if c.get("outcome") and c.get("direction") in sign:
            row = np.where((outs == c["outcome"]) & (sgn == -sign[c["direction"]]), row, -1)
            top = [j for j in np.argsort(-row)[:TOPO] if row[j] >= 0.2]
            if top:
                c["opp"] = [[int(j), round(float(row[j]), 2)] for j in top]

blob = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
(HERE / "index.html").write_text((HERE / "template.html").read_text(encoding="utf-8").replace("/*DATA*/null", blob), encoding="utf-8")
print("index.html:", sum(len(s["claims"]) for s in data["sources"]), "claims,", len(data["sources"]), "sources")
