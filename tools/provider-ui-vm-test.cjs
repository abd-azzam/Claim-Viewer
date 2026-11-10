const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const results=[];async function test(name,fn){try{await fn();results.push({name,ok:true})}catch(e){results.push({name,ok:false,error:e.stack})}}
function fixture(){
 let dialog,focusRestored=0,events=0,serial=0;const profiles=new Map,calls=[];
 class El{
  constructor(){this.value='';this.disabled=false;this.textContent='';this.attrs={};this.elements=new Map}
  setAttribute(k,v){this.attrs[k]=v}get innerHTML(){return this.html}set innerHTML(v){this.html=v;for(const [,id]of v.matchAll(/id="([^"]+)"/g)){const e=new El;this.elements.set(id,e)}this.elements.get('ps-provider').value='deepseek';this.elements.get('ps-protocol').value='chat';this.elements.get('ps-delete').disabled=true}
  querySelector(sel){return this.elements.get(sel.slice(1))}append(){}replaceChildren(...options){this.options=options;this.value=options[0]?.value||''}focus(){this.focused=true}showModal(){this.open=true}close(){this.open=false;this.onclose?.()}remove(){this.removed=true}
 }
 const backend=async(action,payload)=>{
  calls.push({action,payload});let id;
  if(action==='save'){const p=JSON.parse(payload);id=p.id||'p'+(++serial);const old=profiles.get(id);profiles.set(id,{...p,id,key:undefined,has_key:!!p.key||!!old?.has_key})}
  if(action==='delete')profiles.delete(payload);
  return {ok:true,id,connections:[...profiles.values()]};
 };
 const context=vm.createContext({window:{pywebview:{api:{ai_connections:backend}},dispatchEvent(){events++}},document:{activeElement:{focus(){focusRestored++}},createElement:tag=>tag==='dialog'?dialog=new El:new El,body:{append(){}}},Option:class{constructor(text,value){this.text=text;this.value=value}},Event:class{constructor(type){this.type=type}},console});
 vm.runInContext(fs.readFileSync('C:/Apps/ClaimViewer/lib/provider-settings.js','utf8'),context);
 return {context,profiles,calls,open:()=>context.providerSettings(),q:id=>dialog.querySelector('#ps-'+id),dialog:()=>dialog,stats:()=>({focusRestored,events})};
}
(async()=>{
 const f=fixture();await f.open();f.q('provider').value='claude';f.q('provider').onchange();f.q('model').value='fixture-claude';f.q('key').value='fixture-secret';
 await test('Preset controls fill name, endpoint and protocol',()=>{assert.equal(f.q('name').value,'Claude (Anthropic)');assert.equal(f.q('base').value,'https://api.anthropic.com/v1');assert.equal(f.q('protocol').value,'anthropic')});
 await f.q('form').onsubmit({preventDefault(){}});
 await test('New Save selects returned id and enables editing/deletion',()=>{assert.equal(f.q('saved').value,'p1');assert.equal(f.q('delete').disabled,false);assert.equal(f.profiles.size,1);assert.equal(f.q('save').disabled,false)});
 await test('Successful Save clears password field',()=>assert.equal(f.q('key').value,''));
 f.q('name').value='Edited Claude';await f.q('form').onsubmit({preventDefault(){}});
 await test('Second Save edits selected profile without duplicate',()=>{assert.equal(f.profiles.size,1);assert.equal(f.profiles.get('p1').name,'Edited Claude');assert.equal(JSON.parse(f.calls.filter(x=>x.action==='save')[1].payload).id,'p1');assert.equal(f.profiles.get('p1').has_key,true)});
 f.q('saved').value='';f.q('saved').onchange();f.q('provider').value='openai';f.q('provider').onchange();f.q('model').value='fixture-openai';await f.q('form').onsubmit({preventDefault(){}});
 await test('Saved profile reload restores provider preset and exact values',()=>{f.q('saved').value='p1';f.q('saved').onchange();assert.equal(f.q('provider').value,'claude');assert.equal(f.q('name').value,'Edited Claude');assert.equal(f.q('model').value,'fixture-claude');assert.equal(f.q('protocol').value,'anthropic');assert.equal(f.q('key').value,'')});
 await f.q('delete').onclick();
 await test('Delete removes selected profile and resets to New connection',()=>{assert.equal(f.profiles.size,1);assert.equal(f.profiles.has('p1'),false);assert.equal(f.q('saved').value,'');assert.equal(f.q('delete').disabled,true);assert.equal(f.q('model').value,'')});
 await test('Dialog close lifecycle removes dialog and restores opener focus',()=>{assert.equal(f.dialog().attrs['aria-label'],'AI settings');f.dialog().close();assert.equal(f.dialog().removed,true);assert.equal(f.stats().focusRestored,1)});
 const broken=fixture();broken.context.window.pywebview.api.ai_connections=async()=>({ok:false,error:'fixture error'});await broken.open();
 await test('Failed initial load reports error',()=>assert.equal(broken.q('status').textContent,'fixture error'));
 await broken.q('form').onsubmit({preventDefault(){}});
 await test('Failed Save restores button and reports error',()=>{assert.equal(broken.q('save').disabled,false);assert.equal(broken.q('status').textContent,'fixture error')});
 console.log(JSON.stringify({passed:results.filter(r=>r.ok).length,total:results.length,results,limitations:['DOM shim only; native Escape default behavior unverified','No real HTTP, crypto or document writes']},null,2));if(results.some(r=>!r.ok))process.exitCode=1;
})().catch(e=>{console.error(e);process.exitCode=1});
