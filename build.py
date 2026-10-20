"""Build index.html from library.json + data/claims/*.verified.json.

    python -I -X utf8 build.py                  inputs beside this script
    python -I -X utf8 build.py --from <dir>     another folder's library.json + data/

The template holds the whole app; this script only fills its DATA payload:
schema (the two renameable axes), the connection models, the library (collections)
and the claims of every reading.
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
# Two layouts exist: the app folder keeps the template in template/, this repo keeps it at the root.
TEMPLATE = next((p for p in (HERE / "template" / "template.html", HERE / "template.html") if p.exists()),
                HERE / "template.html")
OUT = HERE / "index.html"

SCHEMA = {
    "a": {"name": "Determinant", "hint": "a cause of the variation"},
    "b": {"name": "Effect", "hint": "what the variation does"},
    "p": {"name": "Pathway", "hint": "a strand of the literature"},
}

# Four connection models, each with its own type set and colour. A link keeps both.
MODELS = {
    "stance": {"name": "Stance", "types": {
        "supports": {"label": "supports", "color": "#0e7c86"},
        "challenges": {"label": "challenges", "color": "#c2410c"},
        "qualifies": {"label": "qualifies", "color": "#7c3aed"}}},
    "causal": {"name": "Causal", "types": {
        "causes": {"label": "causes", "color": "#1f5fbf"},
        "mediates": {"label": "mediates", "color": "#5f6ad1"},
        "moderates": {"label": "moderates", "color": "#8a63c9"},
        "prevents": {"label": "prevents", "color": "#5d6672"}}},
    "argument": {"name": "Argument", "types": {
        "premise": {"label": "premise", "color": "#17713f"},
        "rebuttal": {"label": "rebuttal", "color": "#9a5b00"},
        "counterexample": {"label": "counterexample", "color": "#b3261e"},
        "extension": {"label": "extension", "color": "#0c8599"}}},
    "biblio": {"name": "Bibliographic", "types": {
        "cites": {"label": "cites", "color": "#4c6ef5"},
        "extends": {"label": "extends", "color": "#3b5bdb"},
        "replicates": {"label": "replicates", "color": "#748ffc"},
        "supersedes": {"label": "supersedes", "color": "#9775fa"}}},
}

ROLES = {
    "A": "Names a Determinant",
    "B": "Names an Effect",
    "TYPOLOGY": "Defines or classifies, without a cause or effect",
    "OTHER": "Context that fits none of the above",
}
DIRECTION = ["+", "-", "mixed", "none"]
EVIDENCE = ["theory", "case-study", "cross-country-quantitative", "firm-level-quantitative",
            "historical", "review-of-literature", "author-assertion"]


def load(p, default=None):
    p = Path(p)
    if not p.exists():
        return default
    return json.loads(p.read_text(encoding="utf-8"))


def main(src=None):
    src = Path(src).resolve() if src else HERE
    lib = load(src / "library.json", {"collections": [], "items": {}})
    vocab = load(src / "data" / "vocab.json", {})
    overrides = load(src / "data" / "overrides.json", {})

    sources = []
    for sid, item in lib["items"].items():
        claims = []
        p = src / "data" / "claims" / f"{sid}.verified.json"
        if p.exists():
            claims = load(p)["claims"]
        for c in claims:
            c.update(overrides.get(c["id"], {}))
            _pw = vocab.get("pathways", {})  # store pathways by name, never by number
            _v = c.get("pathway")
            if isinstance(_v, list):
                c["pathway"] = [_pw.get(str(x), str(x)) for x in _v]
            elif _v not in (None, ""):
                c["pathway"] = [_pw.get(str(_v), str(_v))]
            for k in ("cite_page", "scope", "section"):  # a BOM from the extractor leaks into page labels
                if isinstance(c.get(k), str):
                    c[k] = c[k].replace("\ufeff", "")
            off = item.get("cite_offset")
            if off and c.get("pdf_page"):
                c["cite_page"] = str(c["pdf_page"] - off) if c["pdf_page"] > off else "front"
        title = re.sub(r"\.pdf$", "", item.get("title") or sid, flags=re.I)
        sources.append({"id": sid, "kind": "paper", "title": title, "claims": claims})

    data = {
        "schema": SCHEMA,
        "models": MODELS,
        "vocab": {
            "pathways": vocab.get("pathways", {}),
            "axisA_list": vocab.get("q1_factors", []),
            "axisB_list": vocab.get("q2_outcomes", []),
            "roles": ROLES,
            "direction": DIRECTION,
            "evidence": EVIDENCE,
        },
        "library": lib,
        "sources": sources,
    }

    flat = [c for s in sources for c in s["claims"]]
    add_related(sources, flat)

    tpl = TEMPLATE.read_text(encoding="utf-8")
    if tpl.count("/*DATA*/null") != 1:
        sys.exit("template.html: expected exactly one /*DATA*/null marker")
    blob = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    OUT.write_text(tpl.replace("/*DATA*/null", blob), encoding="utf-8")
    print(f"index.html: {len(flat)} claims, {len(sources)} sources, "
          f"{len(lib['collections'])} collections")


def add_related(sources, flat):
    """rel/opp per claim: TF-IDF cosine on quote+gist, word overlap only. Zero model cost."""
    import numpy as np
    from scipy import sparse

    sid = np.array([i for i, s in enumerate(sources) for _ in s["claims"]])
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
    if not voc:
        return
    X = sparse.csr_matrix((v_, (r_, c_)), shape=(len(docs), len(voc)))
    X = sparse.diags(1 / np.maximum(np.sqrt(X.multiply(X).sum(1)).A1, 1e-9)) @ X
    sign = {"+": 1, "-": -1}
    outs = np.array([(c.get("outcome") or c.get("axisB") or [""])[0] if isinstance(c.get("outcome") or c.get("axisB"), list)
                     else (c.get("outcome") or c.get("axisB") or "") for c in flat])
    sgn = np.array([sign.get((c.get("direction") or [None])[0] if isinstance(c.get("direction"), list)
                             else c.get("direction"), 0) for c in flat])
    SIM, TOPK, TOPO = 0.15, 5, 3
    for a in range(0, len(flat), 500):
        S = (X[a:a + 500] @ X.T).toarray()
        for k in range(S.shape[0]):
            i, row = a + k, S[k]
            row[sid == sid[i]] = -1
            c = flat[i]
            top = [j for j in np.argsort(-row)[:TOPK] if row[j] >= SIM]
            if top:
                c["rel"] = [[int(j), round(float(row[j]), 2)] for j in top]
            if outs[i] and sgn[i]:
                row = np.where((outs == outs[i]) & (sgn == -sgn[i]), row, -1)
                top = [j for j in np.argsort(-row)[:TOPO] if row[j] >= 0.2]
                if top:
                    c["opp"] = [[int(j), round(float(row[j]), 2)] for j in top]


if __name__ == "__main__":
    # python build.py                 build from the inputs beside this file
    # python build.py --from <dir>     build from another folder's library.json + data/
    args = sys.argv[1:]
    main(args[args.index("--from") + 1] if "--from" in args else None)
