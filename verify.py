"""Verify extracted quotes against the source PDF, then write a highlighted copy.

Usage: python ClaimViewer/verify.py [source-id ...]   (default: all in sources.json)
In : ClaimViewer/claims/<id>.json   {"claims": [{"id","quote",...}]}
Out: ClaimViewer/claims/<id>.verified.json   (adds status/pdf_page/cite_page)
     ClaimViewer/pdf/<id>.pdf                (copy with highlights; original untouched)
status: exact | anchored | ambiguous | failed.  A failed quote is never rewritten.
"""
import json, re, sys, unicodedata
from pathlib import Path
import pymupdf

ROOT = Path(__file__).resolve().parent.parent
HERE = ROOT / "ClaimViewer"
ANCHOR = 8  # words used at each end of a quote when the full quote does not match


def key(s):
    # lowercase letters/digits only: immune to hyphens, spacing, curly quotes, ligatures
    # U+0180-024F also dropped: some PDF fonts map the "ti" ligature there (e.g. "idenƟfy"), the md loses it
    return re.sub(r"[\W_ƀ-ɏɐ-ʯ]+", "", unicodedata.normalize("NFKC", s).lower())


def build_stream(doc):
    """One char stream over the whole PDF, plus char -> (page, word rect)."""
    chars, owner, words = [], [], []
    for pno, page in enumerate(doc):
        for w in page.get_text("words"):
            k = key(w[4])
            if not k:
                continue
            words.append((pno, pymupdf.Rect(w[:4]), w[5], w[6]))  # page, rect, block, line
            chars.append(k)
            owner.extend([len(words) - 1] * len(k))
    return "".join(chars), owner, words


def locate(stream, quote):
    q = key(quote)
    if len(q) < 25:
        return None, "failed"
    n = stream.count(q)
    if n:
        i = stream.find(q)
        return (i, i + len(q)), ("exact" if n == 1 else "ambiguous")
    toks = quote.split()
    head, tail = key("".join(toks[:ANCHOR])), key("".join(toks[-ANCHOR:]))
    if len(toks) >= 2 * ANCHOR and head and tail:
        i = stream.find(head)
        while i != -1:
            j = stream.find(tail, i + len(head))
            if j != -1 and j + len(tail) - i <= 1.4 * len(q) + 300:
                return (i, j + len(tail)), "anchored"
            i = stream.find(head, i + 1)
    return None, "failed"


def highlight(doc, owner, words, span):
    a, b = owner[span[0]], owner[span[1] - 1]
    lines = {}
    for w in words[a:b + 1]:
        lines.setdefault((w[0], w[2], w[3]), pymupdf.Rect(w[1])).include_rect(w[1])
    return lines


def run(src):
    sid = src["id"]
    claims_path = HERE / "claims" / f"{sid}.json"
    if not claims_path.exists():
        print(f"{sid}: no claims file, skipped")
        return
    data = json.loads(claims_path.read_text(encoding="utf-8"))
    doc = pymupdf.open(ROOT / src["pdf"])
    stream, owner, words = build_stream(doc)
    stats = {}
    for c in data["claims"]:
        span, status = locate(stream, c["quote"])
        c["status"] = status
        stats[status] = stats.get(status, 0) + 1
        if not span:
            c["pdf_page"] = c["cite_page"] = None
            continue
        lines = highlight(doc, owner, words, (span[0], span[1]))
        c["pdf_page"] = min(k[0] for k in lines) + 1
        c["cite_page"] = doc[c["pdf_page"] - 1].get_label() or None
        for (pno, _, _), r in lines.items():
            page = doc[pno]  # keep a reference: the annot dies with a temporary page
            page.add_highlight_annot(r).set_info(content=c["id"])
    (HERE / "pdf").mkdir(exist_ok=True)
    doc.save(HERE / "pdf" / f"{sid}.pdf", garbage=3, deflate=True)
    (HERE / "claims" / f"{sid}.verified.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    n = len(data["claims"])
    ok = stats.get("exact", 0) + stats.get("anchored", 0) + stats.get("ambiguous", 0)
    print(f"{sid}: {n} claims, found {ok}/{n} ({100 * ok // max(n, 1)}%) {stats}")
    bad = [c["id"] for c in data["claims"] if c["status"] == "failed"]
    if bad:
        print("  FAILED:", " ".join(bad))


if __name__ == "__main__":
    srcs = json.loads((HERE / "sources.json").read_text(encoding="utf-8"))
    want = set(sys.argv[1:])
    for s in srcs:
        if not want or s["id"] in want:
            run(s)
