"""Rendered regression checks for chat formatting and the citation-only Word pane."""
import json
from pathlib import Path
import re
import shutil
import sys
import tempfile
import threading
import webview
APP=Path(__file__).resolve().parents[1]
folder=Path(tempfile.mkdtemp(prefix='word-ui-',dir=APP/'tools'))
for name in ('word.css','word.js'):shutil.copyfile(APP/'word'/name,folder/name)
html=(APP/'word/addin.html').read_text(encoding='utf-8')
html=re.sub(r'<script src="https://appsforoffice[^>]+></script>','',html)
html=html.replace('<script src="office-bridge.js" defer></script>','')
template=(APP/'template/template.html').read_text(encoding='utf-8')
render=template[template.index('const aiDeSlop='):template.index('// Every point must be traceable.')]
normalize=re.search(r'const nk=.*?;',template).group()
html=html.replace('</body>',f'<div id="chat-fixture" hidden></div><script>{normalize}\n{render}\nwindow.aiTestRender=aiCite;</script></body>')
(folder/'index.html').write_text(html,encoding='utf-8')
class Api:
    def __init__(self):self.ready=False;self.calls=[]
    def word_sources(self,details=False):
        return {'collections':[{'id':'parent','name':'Thesis','parent':None},{'id':'child','name':'Industry','parent':'parent'},{'id':'other','name':'Other','parent':None}],
                'sources':[{'id':'a','title':'One source','author':'Author A','year':'2025','collections':['child']},{'id':'b','title':'<img src=x onerror=alert(1)>','author':'Author B','year':'2024','collections':['other']}],
                'styles':['APA','Chicago','MLA']}
    def word_action(self,action,payload='{}'):
        self.calls.append((action,json.loads(payload)))
        if action=='state':return {'ok':self.ready,'error':'Save document first','document':r'C:\Fixture.docx','name':'Fixture.docx','styles':['APA','Chicago','MLA'],'style':'APA'}
        return {'ok':True}
    def enable(self):self.ready=True
    def report(self,text):
        (APP/'tools/revision-ui-results.json').write_text(text,encoding='utf-8');threading.Timer(.2,window.destroy).start()
api=Api();window=webview.create_window('Citation pane regression checks',(folder/'index.html').as_uri(),js_api=api,width=360,height=780)
def loaded():window.evaluate_js((APP/'tools/revision-ui-test.js').read_text(encoding='utf-8'))
window.events.loaded+=loaded
with tempfile.TemporaryDirectory(prefix='cv-word-ui-',ignore_cleanup_errors=True) as storage:webview.start(storage_path=storage,private_mode=True)
results=json.loads((APP/'tools/revision-ui-results.json').read_text(encoding='utf-8'))
print(json.dumps(results,indent=2))
# The temporary fixture is retained for inspection and never contains user data.
sys.exit(0 if all(r['ok'] for r in results) else 1)
