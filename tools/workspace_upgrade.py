from pathlib import Path
import shutil

root = Path(__file__).resolve().parents[1]
p = root / 'template/template.html'
s = p.read_text(encoding='utf-8')
shutil.copy2(p, p.with_suffix('.before-tabs.html'))
s = s.replace('</style>', '''
#reading-tabs{display:flex;gap:4px;overflow-x:auto;padding:6px 10px;border-bottom:1px solid var(--line)}
#reading-tabs .reading-tab{display:flex;flex:none;max-width:230px;border:1px solid var(--line);border-radius:7px;background:var(--bg)}
#reading-tabs .reading-tab.active{border-color:var(--accent,#3976cc)}
#reading-tabs button{border:0;background:transparent;color:var(--ink);padding:6px 9px}
#reading-tabs button:first-child{overflow:hidden;white-space:nowrap;text-overflow:ellipsis}
#ailog{padding:20px;line-height:1.75}
#ailog .aim.bot{max-width:72ch;margin:0 auto 24px;padding:12px 0;background:transparent;border:0}
</style>''', 1)
s = s.replace('<div class="rtop">', '<div id="reading-tabs" aria-label="Open readings"></div><div class="rtop">', 1)
needle = 'window.showPdf=async(id,pg)=>{if(!id)return;'
assert needle in s
s = s.replace(needle, '''const readingTabs=[];
function paintReadingTabs(active){
 const bar=$("reading-tabs");bar.replaceChildren();
 readingTabs.forEach(id=>{
  const wrap=document.createElement("div"),pick=document.createElement("button"),close=document.createElement("button");
  const title=(DATA.sources.find(x=>x.id===id)||{}).title||id;
  wrap.className="reading-tab"+(active===id?" active":"");
  pick.type=close.type="button";pick.textContent=title;pick.title=title;
  pick.setAttribute("aria-pressed",String(active===id));
  pick.onclick=()=>openInReader(id);
  close.textContent="×";close.setAttribute("aria-label","Close "+title);
  close.onclick=()=>{const i=readingTabs.indexOf(id);readingTabs.splice(i,1);
   if(active===id){const next=readingTabs[Math.min(i,readingTabs.length-1)];
    if(next)return openInReader(next);s.value="";window.cvIdle();}
   paintReadingTabs(active===id?"":active);};
  wrap.append(pick,close);bar.append(wrap);
 });
}
window.showPdf=async(id,pg)=>{if(!id)return;
 if(!readingTabs.includes(id))readingTabs.push(id);paintReadingTabs(id);''', 1)
start=s.index('    const sys="You help a political science researcher')
end=s.index(';\n',start)
s=s[:start]+'''    const sys="You help a researcher understand the PDF supplied in <pdf> tags, with [p.N] page blocks. Answer the question directly in the first paragraph. Then explain the reasoning in short connected paragraphs, using a few descriptive headings only when helpful. Use lists for parallel examples or steps. Distinguish the author's argument from your interpretation. Explain unfamiliar terms and identify limitations or counterarguments supported by the text. Do not invent missing evidence. Cite each substantive source-based point immediately with [p.N: \\\"an exact excerpt from that page\\\"], at most 30 words. Use PDF page numbers starting at 1. Cite only pages supplied to you. Say when the supplied text cannot answer the question. Do not claim to have read pages absent from the context. Avoid repetitive summaries and artificial labels on every sentence."'''+s[end:]
p.write_text(s,encoding='utf-8')

p=root/'launch.py'
s=p.read_text(encoding='utf-8')
shutil.copy2(p,p.with_suffix('.before-programfiles.py'))
needle='os.chdir(ROOT)'
s=s.replace(needle,'''# An installed binary can use an existing writable library without moving its profile.
_data_pointer = pathlib.Path(ROOT, "data-root.txt")
if _data_pointer.exists():
    ROOT = str(pathlib.Path(_data_pointer.read_text(encoding="utf-8").strip()).resolve(strict=True))
os.chdir(ROOT)''',1)
p.write_text(s,encoding='utf-8')
