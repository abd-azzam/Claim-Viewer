// UI layer of bughunt.py. Drives a COPY of the app over CDP.  node bughunt_ui.mjs PORT APPDIR [--quick]
// Prints one "CHK\t{json}" line per check. bughunt.py turns failures into findings.
import fs from "node:fs";
import path from "node:path";
const [PORT, DIR] = process.argv.slice(2), QUICK = process.argv.includes("--quick");
const sleep = ms => new Promise(r => setTimeout(r, ms));
const out = (name, ok, detail = "", sev = "MED", skip = false) =>
  console.log("CHK\t" + JSON.stringify({ name, ok, detail: String(detail).slice(0, 700), sev, skip }));
const SKIP = (name, why) => out(name, true, why, "", true);

const page = (await (await fetch(`http://127.0.0.1:${PORT}/json`)).json()).find(t => t.type === "page" && t.url.startsWith("file:"));
const ws = new WebSocket(page.webSocketDebuggerUrl);
await new Promise(r => (ws.onopen = r));
let id = 0, errs = [];
const pend = new Map(), reqs = new Map();
ws.onmessage = m => {
  const d = JSON.parse(m.data), p = d.params;
  if (d.id) { pend.get(d.id)?.(d); pend.delete(d.id); return; }
  if (d.method === "Runtime.exceptionThrown") errs.push("exception: " + (p.exceptionDetails.exception?.description || p.exceptionDetails.text).split("\n").slice(0, 2).join(" "));
  else if (d.method === "Runtime.consoleAPICalled" && p.type === "error") errs.push("console.error: " + p.args.map(a => a.value ?? a.description).join(" ").slice(0, 200));
  else if (d.method === "Network.requestWillBeSent") reqs.set(p.requestId, p.request.url);
  else if (d.method === "Network.loadingFailed" && !p.canceled) errs.push("request failed: " + p.errorText + " " + decodeURIComponent(reqs.get(p.requestId) || "?").slice(-80));
};
const send = (method, params = {}) => new Promise(r => { const i = ++id; pend.set(i, r); ws.send(JSON.stringify({ id: i, method, params })); });
// run a real function inside the page; args are JSON
const ev = async (fn, ...a) => {
  const r = await send("Runtime.evaluate", { expression: `(${fn})(...${JSON.stringify(a)})`, returnByValue: true, awaitPromise: true });
  if (r.error) throw new Error(r.error.message);
  const x = r.result.exceptionDetails;
  if (x) throw new Error((x.exception?.description || x.text).slice(0, 200));
  return r.result.result.value;
};
const take = () => { const e = [...new Set(errs)]; errs = []; return e; };
const nCards = () => ev(() => document.querySelectorAll(".card").length);
// reload and wait until the NEW document has cards (or is complete when cards are not expected)
const reload = async (needCards = true, ms = 20000) => {
  await ev(() => { window.__stale = 1; }).catch(() => {});
  await send("Page.reload");
  const t = Date.now();
  while (Date.now() - t < ms) {
    try {
      if (await ev(nc => !window.__stale && (nc ? document.querySelectorAll(".card").length > 0 : document.readyState === "complete"), needCards)) { if (!needCards) await sleep(1200); return Date.now() - t; }
    } catch {}
    await sleep(150);
  }
  return -1;
};
const domCheck = async label => {
  const d = await ev(() => {
    const c = {};
    document.querySelectorAll("[id]").forEach(e => (c[e.id] = (c[e.id] || 0) + 1));
    return { dup: Object.keys(c).filter(k => c[k] > 1), bad: document.body.innerText.split("\n").filter(l => /^\s*(undefined|NaN)\s*$|[:(\[]\s*(undefined|NaN)\b|\b(undefined|NaN)\s*[%)\]]|\[object Object\]/.test(l)).slice(0, 3).map(s => s.trim().slice(0, 80)) };
  });
  out(`no duplicate ids in the live DOM (${label})`, !d.dup.length, d.dup.join(", "));
  out(`no undefined / NaN / [object Object] on screen (${label})`, !d.bad.length, d.bad.join(", "), "LOW");
};
const has = sel => ev(s => !!document.querySelector(s), sel);

await Promise.all(["Runtime", "Log", "Network", "Page", "Performance"].map(d => send(d + ".enable")));
const orig = fs.readFileSync(path.join(DIR, "library.json"), "utf8");

// ---- load
const t0 = await reload();
out("page shows claim cards and raises no errors on load", t0 > 0 && !take().length || false, t0 < 0 ? "no .card within 20 s" : "see below", t0 < 0 ? "HIGH" : "MED");
if (t0 < 0) { ws.close(); process.exit(0); }
// the line above drained errs; re-run load once more to report their text
{ const t = await reload(); const e = take(); if (e.length) out("load errors (text)", false, e.join(" | ")); out("first card within 5 s", t <= 5000, `${t} ms`, "MED"); }
const heap = (await send("Performance.getMetrics")).result.metrics.find(m => m.name === "JSHeapUsedSize").value / 1e6;
out("JS heap under 500 MB after load", heap < 500, `${heap.toFixed(0)} MB`);
const n0 = await nCards();
await domCheck("list");

// ---- search box
if (await has("#q")) {
  const typ = q => ev(q => { const e = document.getElementById("q"); e.value = q; e.dispatchEvent(new Event("input", { bubbles: true })); }, q).then(() => sleep(600));
  const res = {};
  for (const q of ["zzzqqq-nonsense", "( [ \\ * + ?", "a|b", "<img src=x onerror=alert(1)>"]) { await typ(q); res[q] = await nCards(); }
  await domCheck("after search");
  await typ("");
  const back = await nCards();
  out("search: errors on odd input", !take().length, JSON.stringify(res));
  out("search: clearing the box restores the full list", back === n0, `${n0} before, ${back} after`);
} else SKIP("search box", "#q not found");

// ---- theme
if (await has("#th")) {
  const snap = () => ev(() => document.documentElement.className + "|" + document.body.className + "|" + document.documentElement.dataset.theme + "|" + getComputedStyle(document.body).backgroundColor);
  const a = await snap();
  await ev(() => document.getElementById("th").click()); await sleep(300);
  const b = await snap();
  await ev(() => document.getElementById("th").click()); await sleep(300);
  out("theme button changes the look and returns", a !== b && a === (await snap()) && !take().length, `${a} -> ${b}`);
} else SKIP("theme button", "#th not found");

// ---- every option of every left-bar select
const sels = await ev(() => ["col", "src", "role", "pw", "fa", "oc", "dir", "ev", "own", "grp", "rl", "lt"].filter(i => document.getElementById(i)?.tagName === "SELECT"));
const selBad = [];
const snap0 = await ev(ids => Object.fromEntries(ids.map(i => [i, document.getElementById(i).value])), sels);
for (const s of sels) {
  const r = await ev(async s => {
    const e = document.getElementById(s), o0 = e.value, vals = [...e.options].map(o => o.value).slice(0, 40), seen = [];
    for (const v of vals) { e.value = v; e.dispatchEvent(new Event("change", { bubbles: true })); await new Promise(r => setTimeout(r, 60)); seen.push(document.querySelectorAll(".card").length); }
    e.value = o0; e.dispatchEvent(new Event("change", { bubbles: true })); await new Promise(r => setTimeout(r, 100));
    return { n: vals.length };
  }, s);
  const e = take();
  if (e.length) selBad.push(`${s}: ${e[0]}`);
}
out(`all options of ${sels.length} filters work without errors`, !selBad.length, selBad.join(" | "));
// the loop above restores each select alone, but one filter can reset another (collection -> source): put them all back, twice
await ev(async snap => { for (let pass = 0; pass < 2; pass++) for (const [i, v] of Object.entries(snap)) { const e = document.getElementById(i); e.value = v; e.dispatchEvent(new Event("change", { bubbles: true })); await new Promise(r => setTimeout(r, 120)); } }, snap0);
// ponytail: the card count in the DOM is not a stable restore signal (488 at load, all 7181 after the loop), so start the click test from a fresh load
await reload(true);

// ---- click cards as a reader does: scroll into view, click the card that is on screen, check the selection
const keys = [], bad = [];
let paneOk = null;
for (let i = 0; i < 25; i++) {
  const r = await ev(async () => {
    let S = document.getElementById("list");
    while (S && S.scrollHeight <= S.clientHeight + 4) S = S.parentElement;
    S = S || document.scrollingElement;
    S.scrollTop += Math.max(250, S.clientHeight * .5);
    await new Promise(r => setTimeout(r, 220));
    const cs = [...document.querySelectorAll(".card")].filter(c => { const b = c.getBoundingClientRect(); return b.top > 90 && b.bottom < innerHeight - 30; });
    const c = cs[Math.floor(cs.length / 2)];
    if (!c) return null;
    const k = c.dataset.k;
    c.scrollIntoView({ block: "center" }); c.click();
    let sel = [];
    for (let w = 0; w < 20; w++) {  // the click re-renders the list in chunks; give it up to 2 s
      await new Promise(r => setTimeout(r, 100));
      sel = [...document.querySelectorAll(".card.sel")];
      if (sel.length && sel.every(x => x.dataset.k === k)) break;
    }
    return { k, ok: sel.length >= 1 && sel.every(x => x.dataset.k === k) };  // the same claim can appear in two boxes; every copy lights up
  });
  if (!r) break;
  keys.push(r.k);
  if (!r.ok) bad.push(`${String(r.k).slice(0, 24)} -> not exactly that card selected`);
  if (i === 0 && await has("#rd")) { for (let w = 0; w < 25 && !paneOk; w++) { paneOk = await has("#rd .pg"); await sleep(200); } }
}
out(`click ${keys.length} cards: one selected each, no errors`, keys.length >= 15 && !bad.length && !take().length, bad.join("; "));
if (paneOk !== null) out("PDF pane builds page boxes after a card click", !!paneOk, "#rd .pg never appeared in 5 s");
else SKIP("PDF pane", "#rd not found");
await ev(async ks => { for (const k of ks.slice(0, 15)) { const c = [...document.querySelectorAll(".card")].find(c => c.dataset.k === k); c?.click(); } }, keys); // no waits: stress the load-token logic
await sleep(2500);
out("15 rapid card clicks: one selected, no errors", (await ev(() => document.querySelectorAll(".card.sel").length)) === 1 && !take().length, "");
await domCheck("card selected");

// ---- Edit panel
await pick(keys[0]); await sleep(300);
if (await has(".card.sel [data-ed]")) {
  const ls = () => ev(() => localStorage.getItem("cv:edits"));
  const before = await ls();
  await ev(() => document.querySelector(".card.sel [data-ed]").click()); await sleep(400);
  const open = await has("dialog[open]");
  await domCheck("edit panel open");
  await ev(() => document.querySelectorAll("dialog[open]").forEach(d => d.close())); await sleep(200);
  out("Edit panel opens; open + close does not change saved edits", open && (await ls()) === before && !take().length, `open=${open}`);
} else SKIP("Edit panel", "no [data-ed] on a selected card");

// ---- graph
if (await has(".card.sel [data-g]")) {
  await ev(() => document.querySelector(".card.sel [data-g]").click()); await sleep(800);
  const g = await ev(() => ({ on: document.body.classList.contains("graph"), sz: [...document.querySelectorAll("#gv svg, #gv canvas, svg")].map(e => e.getBoundingClientRect().width * e.getBoundingClientRect().height).sort((a, b) => b - a)[0] || 0 }));
  await domCheck("graph");
  out("graph view opens and draws", g.on && g.sz > 1000 && !take().length, JSON.stringify(g), "HIGH");
  if (await has("#gb")) { await ev(() => document.getElementById("gb").click()); await sleep(500); out("Back to list leaves the graph", !(await ev(() => document.body.classList.contains("graph"))), ""); }
  else out("Back to list button exists in graph view", false, "#gb missing");
} else SKIP("graph", "no [data-g] on a selected card");

// ---- widths
const ov = [];
for (const [w, h] of [[700, 800], [900, 600], [1500, 920]]) {
  await send("Emulation.setDeviceMetricsOverride", { width: w, height: h, deviceScaleFactor: 1, mobile: false }); await sleep(400);
  const o = await ev(() => document.documentElement.scrollWidth - innerWidth);
  if (o > 2) ov.push(`${w}px wide: page is ${o}px too wide`);
}
await send("Emulation.clearDeviceMetricsOverride");
out("no sideways scrolling at 700, 900 and 1500 px", !ov.length, ov.join("; "), "LOW");

// ---- Python bridge (real pywebview)
let bridge = false;
for (let i = 0; i < 40 && !bridge; i++) { bridge = await ev(() => !!(window.pywebview && pywebview.api && pywebview.api.import_pdfs)); if (!bridge) await sleep(250); }
if (!bridge) SKIP("Python bridge", "window.pywebview.api never appeared");
else {
  const call = (m, ...a) => ev(async (m, a) => { try { return { v: await pywebview.api[m](...a) }; } catch (e) { return { err: String(e) }; } }, m, a);
  for (const m of ["load_pages", "log"]) { const r = await call(m, ...(m === "log" ? ["bughunt"] : [])); out(`bridge: ${m}() answers`, !r.err, r.err || ""); }
  const dir = path.join(DIR, "in"); fs.mkdirSync(dir, { recursive: true });
  const names = ["100% sure #1.pdf", "a#b.pdf", "Ünï ç.pdf"], files = names.map(n => path.join(dir, n));
  const pdf = "%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 72 72]>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF\n";
  files.forEach(f => fs.writeFileSync(f, pdf));
  const imp = await call("import_pdfs", "", files);
  const added = imp.v?.added || [];
  out("bridge: import_pdfs adds all 3 awkward file names", added.length === 3, imp.err || JSON.stringify(added));
  const sizes = await ev(async ids => Promise.all(ids.map(i => new Promise(r => { const x = new XMLHttpRequest(); x.open("GET", "pdf/" + encodeURIComponent(i) + ".pdf"); x.responseType = "arraybuffer"; x.onload = () => r(x.response.byteLength); x.onerror = () => r(-1); x.send(); }))), added);
  out("imported PDFs load the way the viewer requests them (pdf/<encodeURIComponent(id)>.pdf)", sizes.length === 3 && sizes.every(s => s > 0), added.map((a, i) => `${a}: ${sizes[i]}`).join("; "), "HIGH");

  // garbage-but-legal libraries: must render, not blank
  const base = JSON.parse(orig), it = Object.keys(base.items)[0], c0 = base.collections[0] || { id: "c0", name: "c0" };
  const mk = f => { const l = JSON.parse(orig); f(l); return l; };
  const variants = {
    "item without collections": mk(l => { delete l.items[it].collections; }),
    "item in an unknown collection": mk(l => { l.items[it].collections = ["no-such"]; }),
    "collection with an unknown parent": mk(l => { l.collections.push({ id: "x1", name: "x", parent: "ghost" }); }),
    "collection parent cycle": mk(l => { l.collections.push({ id: "cy1", name: "a", parent: "cy2" }, { id: "cy2", name: "b", parent: "cy1" }); }),
    "collection without a name": mk(l => { l.collections.push({ id: "nn" }); }),
    "two collections with one id": mk(l => { l.collections.push({ ...c0 }); }),
    "item with no title": mk(l => { delete l.items[it].title; }),
    "item with tags null": mk(l => { l.items[it].tags = null; }),
    "empty library": { version: 1, collections: [], items: {} },
  };
  for (const [name, lib] of Object.entries(variants)) {
    const sv = await call("save_library", JSON.stringify(lib));
    const empty = name === "empty library";
    const t = await reload(!empty);
    const e = take(), blank = !(await ev(() => document.body.innerText.trim().length > 50).catch(() => false));
    out(`library with ${name} still renders`, t >= 0 && !e.length && !blank, `${sv.err || ""} ${t < 0 ? "no render" : ""} ${blank ? "blank page" : ""} ${e.join(" | ")}`, t < 0 || blank ? "HIGH" : "MED");
  }
  await call("save_library", orig); // put the copy back for the fuzz below
  await reload();
}

// ---- localStorage fuzz
if (QUICK) SKIP("localStorage fuzz", "--quick");
else {
  const keysLS = ["theme", "src", "hide", "perf", "edits", "zk", "zkundo", "zkmerge", "dict", "hl", "lastpg", "graph", "lists", "zexp"].map(k => "cv:" + k);
  for (const k of keysLS) {
    const fails = [];
    for (const v of ["{{{", "[]", "null"]) {
      await ev((k, v) => { localStorage.clear(); localStorage.setItem(k, v); }, k, v);
      const t = await reload(); const e = take();
      if (t < 0) fails.push(`${v}: BLANK (no cards)`); else if (e.length) fails.push(`${v}: ${e[0].slice(0, 90)}`);
    }
    out(`${k} holding bad text survives a restart`, !fails.length, fails.join(" | "), fails.some(f => f.includes("BLANK")) ? "HIGH" : "MED");
  }
  await ev(() => localStorage.clear());
}
ws.close();
process.exit(0);
