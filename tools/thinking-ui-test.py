"""Rendered chat request checks without real PDFs, API keys or provider calls."""
import json
from pathlib import Path
import tempfile
import threading
import webview

root=Path(__file__).resolve().parents[1]
source=(root/'template/template.html').read_text(encoding='utf-8')
thinking=source[source.index('const aiThinkNew='):source.index('const aiStatus=')]
send=source[source.index('const aiSend='):source.index('const aiAsk=')]
fixture='''<html><body><div id="ailog"></div><button id="aisend">Send</button><select id="aimodel"><option value="profile:fixture">Fixture</option></select><script>
const $=id=>document.getElementById(id),AI={busy:false};let history=[],mode='reasoning';
const aiId=()=> 'fixture',aiLoad=async()=>({text:'[p.1] Disposable fixture.'}),aiTitle=()=> 'Fixture';
const histOf=()=>history,aiSave=()=>{},aiClearBtn=()=>{},aiPin=()=>{},aiStrong=()=>{},progShow=()=>{};
const aiTrace=async(text)=>text;
const aiLine=(cls,text)=>{const node=document.createElement('div');node.className=cls;node.textContent=text;$('ailog').append(node);return node};
const aiCite=(node,text)=>node.append(document.createTextNode(text));
</script><script>'''+thinking+send+'''</script><script>
async function checkChat(){const results=[];const check=(name,ok)=>{results.push({name,ok:!!ok});if(!ok)throw Error(name)};
try{
 const pending=aiSend('Fixture question');await new Promise(r=>setTimeout(r,100));
 check('Thinking is visible while a complete-response provider works',document.querySelector('.aithink')?.open);
 await pending;let det=document.querySelector('.aithink');
 check('Reasoning stays separate and collapsed after the answer',!det.open&&det.textContent.includes('Provider explanation <script>')&&det.parentElement.textContent.includes('Fixture answer'));
 check('Provider text cannot execute markup',!window.injected&&det.querySelector('script')===null);
 check('Reasoning is retained in local conversation',history[1].reasoning.includes('Provider explanation'));
 check('Request duration is not labelled model thinking time',!det.querySelector('summary').textContent.includes('Thought for'));
 await pywebview.api.set_mode('plain');await aiSend('No reasoning');
 const all=document.querySelectorAll('.aithink');det=all[all.length-1];
 check('Missing reasoning is stated explicitly',det.textContent.includes('did not return a reasoning summary'));
 await pywebview.api.set_mode('error');await aiSend('Failure');
 check('Provider failure shows error and re-enables Send',!AI.busy&&!$('aisend').disabled&&[...document.querySelectorAll('.err')].some(n=>n.textContent.includes('Fixture failure')));
}catch(e){results.push({name:String(e),ok:false})}await pywebview.api.report(JSON.stringify(results))}
window.addEventListener('pywebviewready',checkChat);
</script></body></html>'''

class Api:
    mode='reasoning'
    def set_mode(self,mode):self.mode=mode
    def ai_chat(self,messages,model):
        import time
        time.sleep(.3)
        if self.mode=='error':raise ValueError('Fixture failure')
        return {'ok':True,'text':'Fixture answer','reasoning':'Provider explanation <script>window.injected=true</script>' if self.mode=='reasoning' else ''}
    def report(self,text):
        self.results=json.loads(text)
        threading.Timer(.2,window.destroy).start()

api=Api()
window=webview.create_window('Thinking panel checks',html=fixture,js_api=api,width=600,height=460)
with tempfile.TemporaryDirectory(prefix='cv-thinking-',dir=root/'tools',ignore_cleanup_errors=True) as storage:
    webview.start(storage_path=storage,private_mode=True)
print(json.dumps(api.results,indent=2))
assert all(item['ok'] for item in api.results)
