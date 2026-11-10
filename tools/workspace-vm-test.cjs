const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const checks=[];function check(name,fn){fn();checks.push(name)}
class Element {
 constructor(){this.value='';this.textContent='';this.disabled=false;this.fields=[];this._html=''}
 set innerHTML(html){this._html=html;if(this.id==='node-preview'){
  dialog.fields=[...html.matchAll(/data-node="(\d+)" data-field="(title|links)" value="([^"]*)"|data-node="(\d+)" data-field="body">([^<]*)/g)].map(m=>({dataset:{node:m[1]||m[4],field:m[2]||'body'},value:m[3]??m[5]}));
 }}
 get innerHTML(){return this._html}
 querySelector(sel){return get(sel.slice(1))}
 setAttribute(){}
 querySelectorAll(){return this.fields}
 showModal(){this.open=true}close(){this.open=false;this.onclose?.()}remove(){}focus(){}append(){}
}
const elements=new Map;function get(id){if(!elements.has(id)){const e=new Element;e.id=id;elements.set(id,e)}return elements.get(id)}
let dialog;const state=new Map,undo=[];let saves=0,renders=0,draws=0;
const context=vm.createContext({console,document:{createElement:()=>dialog=new Element,querySelector:()=>new Element,getElementById:get,addEventListener(){},body:{append(){}}},localStorage:{getItem:k=>state.get(k)||null,setItem:(k,v)=>state.set(k,v)},esc:s=>String(s).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;'),CMAP:{c:{name:'Collection'}},LIBQ:'',LIBSORT:{k:'title',d:1},meta:id=>({title:id,year:2026,author:'Author'}),META_FIELDS:[['title','Title'],['author','Author']],wireLibBox(){},drawLibTable(){draws++},ZK:{seq:0,notes:{'1':{title:'Existing'}}},zkSel:null,zkFlush(){},pushUndo(){undo.push(JSON.stringify(context.ZK))},zkSave(){saves++},show(){},G:{m:'L'},graph(){renders++},toast(){},window:{},Date});
context.LNK=true;context.zkTags=n=>n.tags||[];context.zkNest=n=>n.subt||[];context.zkPaths=n=>n.subt.map(p=>p.split(' › '));context.zkNote=id=>({title:id==="a"?"Idea <A>":"Idea B",tags:["Topic"],subt:id==="a"?["Methods › Cases","Examples"]:[],links:id==="a"?[{to:"b",kind:"link"}]:[]});
vm.runInContext(fs.readFileSync('C:/Apps/ClaimViewer/lib/idea-layout.js','utf8')+fs.readFileSync('C:/Apps/ClaimViewer/lib/workspace.js','utf8'),context);
check("Idea map renders circular nodes, escaped labels and connections",()=>{const svg=context.ideaMapSVG(["a","b"]);assert.match(svg,/idea-dot/);assert.match(svg,/Idea &lt;A>/);assert.match(svg,/class="idea-edge"/);context.LNK=false;assert.doesNotMatch(context.ideaMapSVG(["a","b"]),/class="idea-edge"/);context.LNK=true});
check("Note graph shows nested sub-tags and keeps notes in distinct groups",()=>{
 const svg=context.ideaMapSVG(["a","b"]);
 assert.match(svg,/<title>Topic<\/title>/);
 assert.match(svg,/class="idea-subtag-hull"/);
 assert.match(svg,/<title>Methods › Cases<\/title>/);
 assert.match(svg,/Methods › Cases; Examples/);
 assert.equal((svg.match(/class="idea-node"/g)||[]).length,2);
 assert(vm.runInContext(`(()=>{
   const tag=JSON.stringify(['','Topic']),sub=JSON.stringify(['','Topic','Methods › Cases']);
   const [x,y,w,h]=ideaGroupBounds(ideaScene,tag),[a,b,c,d]=ideaGroupBounds(ideaScene,sub);
   const [noteX,noteY]=ideaScene.pos.get('b');
   return x<a&&y<b&&w>c&&h>d&&(noteX<a||noteX>c||noteY<b||noteY>d);
 })()`,context),'Tag encloses its sub-tag and untagged sibling stays outside the smaller box');
 assert.doesNotMatch(fs.readFileSync("C:/Apps/ClaimViewer/template/template.html","utf8"),/data-idea-toggle/);
});
check("Library stays in column view",()=>{const html=fs.readFileSync("C:/Apps/ClaimViewer/template/template.html","utf8");assert.doesNotMatch(html,/libraryWorkspace\(box/);assert.doesNotMatch(html,/data-library-view/);assert.match(html,/th data-sort/)});
check('Rejects dangling/self links and empty titles',()=>{for(const v of [[{title:'x',body:'',links:[0]}],[{title:'x',body:'',links:[4]}],[{title:'',body:'',links:[]}]])assert.throws(()=>context.validateNodeDraft(v))});
check('Each claim graph accepts only changes its view can use',()=>{
 const a={src:'a',id:'1',axisA:['Existing'],axisB:[],pathway:[],role:[],links:[],pdf_page:[]};
 const b={...a,src:'b',id:'2',pdf_page:[7]};
 const roles={A:'Argument'},types={supports:{model:'stance'}};
 const draft={claim:1,target:2,type:'supports',axisA:['New'],pathway:['Shared'],axisB:['Outcome'],role:['A','invented'],reason:'Review this.'};
 const make=(mode,v=draft)=>context.claimGraphChanges(mode,[a,b],[v],roles,types)[0]?.patch;
 assert.deepEqual(Array.from(make('L').axisA),['Existing','New']);
 assert.deepEqual(Object.keys(make('C')),['pathway']);
 assert.deepEqual(Array.from(make('R').role),['A']);
 assert.equal(make('K').links[0].p,7);
 assert.equal(make('K',{...draft,target:1}),undefined);
 assert.equal(make('K',{...draft,type:'made-up'}),undefined);
 assert.equal(a.links.length,0);
 assert.equal(a.axisA.length,1);
});
context.nodeStudio();get('node-goal').value='Test goal';get('col').value='c';get('zsrc').value='source-fixture';get('node-manual').onclick();
dialog.fields.find(f=>f.dataset.field==='title').value='Edited title';get('node-manual').onclick();
check('Adding second manual node retains prior edits',()=>assert.equal(dialog.fields.find(f=>f.dataset.node==='0'&&f.dataset.field==='title').value,'Edited title'));
dialog.fields.find(f=>f.dataset.node==='0'&&f.dataset.field==='links').value='2';get('node-apply').onclick();
check('Batch creates unique IDs without overwriting existing note',()=>{assert.equal(Object.keys(context.ZK.notes).length,3);assert.equal(context.ZK.notes['1'].title,'Existing');assert.equal(context.ZK.notes['2'].title,'Edited title')});
check('Connections use graph schema and active collection',()=>{assert.equal(context.ZK.notes['2'].links[0].to,'3');assert.equal(context.ZK.notes['2'].links[0].kind,'link');assert.equal(context.ZK.notes['2'].col,'c');assert.equal(context.ZK.notes['2'].src,'source-fixture');assert.equal(context.G.m,'Z');assert.equal(renders,1)});
check('Batch saves and supplies single undo snapshot',()=>{assert.equal(saves,1);assert.equal(undo.length,1);context.ZK=JSON.parse(undo.pop());assert.equal(Object.keys(context.ZK.notes).length,1)});
(async()=>{
 context.window.pywebview=context.pywebview={api:{ai_chat:async()=>({ok:true,text:'```json\n[{"title":"AI idea","body":"A source explanation","links":[]}]\n```'})}};
 context.nodeStudio();get('node-goal').value='AI goal';get('node-context').value='Source';
 const before=JSON.stringify(context.ZK);await get('node-generate').onclick();
 check('Stubbed AI response renders review without saving',()=>{assert.match(get('node-preview').innerHTML,/AI idea/);assert.equal(JSON.stringify(context.ZK),before);assert.equal(get('node-generate').disabled,false)});
 context.pywebview.api.ai_chat=async()=>({ok:true,text:'not json'});await get('node-generate').onclick();
 check('Malformed AI response surfaces error and keeps data unchanged',()=>{assert.ok(get('node-status').textContent);assert.equal(JSON.stringify(context.ZK),before);assert.equal(get('node-generate').disabled,false)});
 console.log(JSON.stringify({passed:checks.length,checks,limitations:['DOM shim, not browser rendering','API stub only; no live model request']},null,2));
})().catch(e=>{console.error(e);process.exitCode=1});
