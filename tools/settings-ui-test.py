"""Rendered WebView2 integration tests with isolated storage and fake external actions."""
import json
import pathlib
import sys
import tempfile
import webview
ROOT=pathlib.Path(__file__).resolve().parents[1]
RESULT=ROOT/'tools/settings-ui-results.json'
class Fixture:
    def __init__(self):
        self.profiles=[]
    def report(self,text):
        RESULT.write_text(text,encoding='utf-8')
        window.destroy()
    def state_put(self,*args): return True
    def state_flush(self): return True
    def save_pages(self,*args): return True
    def load_pages(self): return {}
    def ai_status(self): return {'has_key':bool(self.profiles),'model':''}
    def ai_models(self): return {'ok':True,'models':['profile:fixture-provider'],'labels':{'profile:fixture-provider':'OpenCode / model/0'}}
    def library_version(self): return 0
    def log(self,*args): return True
    def ai_connections(self,action='list',payload=''):
        if action=='models': return {'ok':True,'models':['model/'+str(i) for i in range(75)]}
        if action=='save':
            p=json.loads(payload)
            p.pop('key',None)
            self.profiles=[dict(p,id='fixture-provider',has_key=True)]
        return {'ok':True,'connections':self.profiles,'id':'fixture-provider'}
    def app_settings(self,action):
        return {'ok':True,'registered':action=='word-install','running':action=='word-install','message':'Fixture action completed.'}
api=Fixture()
window=webview.create_window('Claim Viewer settings verification', (ROOT/'index.html').as_uri(),js_api=api,width=1200,height=800)
def loaded():
    window.evaluate_js((ROOT/'tools/settings-ui-test.js').read_text(encoding='utf-8'))
window.events.loaded += loaded
with tempfile.TemporaryDirectory(prefix='cv-settings-ui-', ignore_cleanup_errors=True) as profile:
    webview.start(storage_path=profile,private_mode=True)
results=json.loads(RESULT.read_text(encoding='utf-8'))
print(json.dumps(results,indent=2))
sys.exit(0 if all(r['ok'] for r in results) else 1)
