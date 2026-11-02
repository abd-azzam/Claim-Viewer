"""Exercise DOI fill and both deletion entry points against a disposable library."""
import json
from pathlib import Path
import shutil
import sys
import tempfile
import webview
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import build
folder=Path(tempfile.mkdtemp(prefix='library-ui-',dir=ROOT/'tools'))
library={'collections':[{'id':'folder','name':'Fixture folder','parent':None}],'items':{key:{'title':key.upper(),'collections':['folder'],'meta':{'type':'article','title':key.upper(),'publisher':'Keep this publisher'}} for key in ('a','b')}}
(folder/'library.json').write_text(json.dumps(library),encoding='utf-8')
shutil.copytree(ROOT/'lib',folder/'lib')
build.HERE=folder;build.TEMPLATE=ROOT/'template/template.html';build.OUT=folder/'index.html';build.main()
class Api:
    def library_version(self):return {'ok':True,'mtime':1}
    def state_put(self,*args):return True
    def state_flush(self):return True
    def save_pages(self,*args):return True
    def load_pages(self):return {}
    def log(self,*args):return True
    def ai_status(self):return {'has_key':False}
    def ai_models(self):return {'ok':True,'models':[]}
    def ai_connections(self,*args):return {'ok':True,'connections':[]}
    def save_library(self,text,*args):
        library.clear();library.update(json.loads(text));return {'ok':True,'mtime':2}
    def lookup_doi(self,doi):return {'ok':True,'source':'DOI fixture','doi':doi,'title':'Exact DOI title','author':'Example, A','year':'2024'}
    def delete_library_item(self,ident):
        del library['items'][ident];return {'ok':True,'library':library,'mtime':3}
    def report(self,value):
        (ROOT/'tools/library-ui-results.json').write_text(value,encoding='utf-8');window.destroy()
window=webview.create_window('Library action verification',(folder/'index.html').as_uri(),js_api=Api(),width=1200,height=800)
script=r'''(async()=>{
 const result=[],q=s=>document.querySelector(s),check=(name,ok)=>{result.push({name,ok:!!ok});if(!ok)throw Error(name)},wait=async f=>{for(let i=0;i<120;i++){if(f())return;await new Promise(r=>setTimeout(r,40))}throw Error('Timed out: '+f)};
 try{
  await wait(()=>window.pywebview?.api?.lookup_doi);show('lib');drawLibTable();
  check('Initial PDF count is two',Object.keys(LIB.items).length===2&&q('#libtbl tbody').children.length===2);
  const input=q('tr[data-id=a] input[data-k=doi]');input.value='10.1234/example';q('tr[data-id=a] .doi-search').click();
  await wait(()=>q('tr[data-id=a] input[data-k=title]').value==='Exact DOI title');
  check('DOI button fills author, title and year',meta('a').author==='Example, A'&&meta('a').year==='2024');
  check('DOI fill preserves fields absent from response',meta('a').publisher==='Keep this publisher');
  q('tr[data-id=a]').dispatchEvent(new MouseEvent('contextmenu',{bubbles:true,clientX:200,clientY:200}));
  check('Library context menu offers deletion',!!q('[data-a=delete]'));q('[data-a=delete]').click();await wait(()=>q('#nask'));q('#nask button[value="0"]').click();
  await wait(()=>!q('#nask'));check('Cancel leaves the library unchanged',Object.keys(LIB.items).length===2);
  q('tr[data-id=a]').dispatchEvent(new MouseEvent('contextmenu',{bubbles:true,clientX:200,clientY:200}));q('[data-a=delete]').click();await wait(()=>q('#nask'));q('#nask button[value="1"]').click();
  await wait(()=>Object.keys(LIB.items).length===1&&DATA.sources.length===1&&!q('tr[data-id=a]'));check('Context deletion reduces library and reader counts',DATA.sources.length===1&&!q('tr[data-id=a]'));
  q('#pdfsel').value='b';q('#lr').click();await wait(()=>q('#nask'));q('#nask button[value="1"]').click();
  await wait(()=>Object.keys(LIB.items).length===0&&DATA.sources.length===0&&q('#libtbl').textContent.includes('The library is empty'));check('Right-pane deletion reduces both counts to zero',DATA.sources.length===0);check('Library renders the empty state',q('#libtbl').textContent.includes('The library is empty'));
 }catch(error){result.push({name:error.message,ok:false})}
 await pywebview.api.report(JSON.stringify(result));
})()'''
def loaded():window.evaluate_js(script)
window.events.loaded+=loaded
with tempfile.TemporaryDirectory(prefix='cv-library-profile-',ignore_cleanup_errors=True) as profile:webview.start(storage_path=profile,private_mode=True)
results=json.loads((ROOT/'tools/library-ui-results.json').read_text(encoding='utf-8'))
print(json.dumps(results,indent=2));sys.exit(0 if all(r['ok'] for r in results) else 1)
