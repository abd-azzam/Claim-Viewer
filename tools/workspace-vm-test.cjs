const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const checks=[];function check(name,fn){fn();checks.push(name)}
class Element {
 constructor(){this.value='';this.textContent='';this.disabled=false;this.fields=[];this._html=''}
 set innerHTML(html){this._html=html;if(this.id==='node-preview'){
  dialog.fields=[...html.matchAll(/data-node="(\d+)" data-field="(title|links|tags)" value="([^"]*)"|data-node="(\d+)" data-field="body">([^<]*)/g)].map(m=>({dataset:{node:m[1]||m[4],field:m[2]||'body'},value:m[3]??m[5]}));
 }}
 get innerHTML(){return this._html}
 querySelector(sel){return get(sel==='h2'?'studio-heading':sel==='p'?'studio-description':sel.slice(1))}
 setAttribute(){}
 querySelectorAll(){return this.fields}
 showModal(){this.open=true}close(){this.open=false;this.onclose?.()}remove(){}focus(){}append(){}
}
const elements=new Map;function get(id){if(!elements.has(id)){const e=new Element;e.id=id;elements.set(id,e)}return elements.get(id)}
let dialog;const state=new Map,undo=[];let saves=0,renders=0,draws=0;
const context=vm.createContext({console,document:{createElement:()=>dialog=new Element,querySelector:()=>new Element,getElementById:get,addEventListener(){},body:{append(){}}},localStorage:{getItem:k=>state.get(k)||null,setItem:(k,v)=>state.set(k,v)},esc:s=>String(s).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;'),CMAP:{c:{name:'Collection'}},LIBQ:'',LIBSORT:{k:'title',d:1},meta:id=>({title:id,year:2026,author:'Author'}),META_FIELDS:[['title','Title'],['author','Author']],wireLibBox(){},drawLibTable(){draws++},ZK:{seq:0,notes:{'1':{title:'Existing'}}},zkSel:null,zkFlush(){},pushUndo(){undo.push(JSON.stringify(context.ZK))},zkSave(){saves++},show(){},G:{m:'L'},graph(){renders++},toast(){},window:{},Date});
check('All notes graph includes both note types',()=>{
 const html=fs.readFileSync('C:/Apps/ClaimViewer/template/template.html','utf8');
 assert.equal((html.match(/data-note-graph aria-haspopup="dialog"/g)||[]).length,2);
 const start=html.indexOf('const zkGraphSVG='),end=html.indexOf('$("zq").addEventListener',start);
 const workspace=fs.readFileSync('C:/Apps/ClaimViewer/lib/workspace.js','utf8');
 const graph=vm.runInNewContext(workspace.slice(0,workspace.indexOf('function openIdeaNote'))+html.slice(start,end)+'\nzkGraphSVG',{ZKCM:null,document:{body:{classList:{add(){}}}},G:context.G,
   zkIdsF:()=>['free','question','section','legacy'],zkNote:id=>id==='legacy'?{question:'Why?'}:{kind:id,question:'Why?'},ideaMapSVG:ids=>ids.join(',')});
 context.G.m='Z';assert.equal(graph(),'free,question,section,legacy');
 context.G.m='S';assert.equal(graph(),'section');
 context.G.m='L';
});
context.LNK=true;context.zkTags=n=>n.tags||[];context.zkNest=n=>n.subt||[];context.zkPaths=n=>n.subt.map(p=>p.split(' › '));context.zkNote=id=>({title:id==="a"?"Idea <A>":"Idea B",tags:["Topic"],subt:id==="a"?["Methods › Cases","Examples"]:[],links:id==="a"?[{to:"b",kind:"link"}]:[]});
vm.runInContext(fs.readFileSync('C:/Apps/ClaimViewer/lib/idea-layout.js','utf8')+fs.readFileSync('C:/Apps/ClaimViewer/lib/workspace.js','utf8'),context);
check('A link from a free-form note to a section note is drawn when both are visible',()=>{
 const original=context.zkNote;
 context.zkNote=id=>({...original(id),kind:id==='a'?'free':'section'});
 try {
  assert.match(context.ideaMapSVG(['a','b']),/class="idea-edge" data-from="a" data-to="b"/);
  assert.doesNotMatch(context.ideaMapSVG(['b']),/class="idea-edge"/);
 } finally {context.zkNote=original}
});
check('Note graph pop-up opens from a button and applies the selected mode',()=>{
 let focused=false;
 context.gset=()=>{};
 context.openNoteGraphPicker({focus(){focused=true}});
 assert.equal(dialog.open,true);
 assert.match(dialog.innerHTML,/All notes.*Section notes/);
 dialog.returnValue='S';dialog.close();
 assert.equal(context.G.m,'S');
 context.openNoteGraphPicker({focus(){focused=true}});
 dialog.returnValue='cancel';dialog.close();
 assert.equal(context.G.m,'S');
 assert.equal(focused,true);
 context.G.m='L';
});
check("Idea map renders circular nodes, escaped labels and connections",()=>{const svg=context.ideaMapSVG(["a","b"]);assert.match(svg,/idea-dot/);assert.match(svg,/Idea &lt;A>/);assert.match(svg,/class="idea-edge"/);context.LNK=false;assert.doesNotMatch(context.ideaMapSVG(["a","b"]),/class="idea-edge"/);context.LNK=true});
check('Question groups show linked claims and keep unassigned claims visible',()=>{
 const original=context.zkNote;
 context.zkNote=id=>({...original(id),question:id==='a'?'How does it work?':'',claims:['s:1']});
 context.zkIds=()=>['a'];
 context.kc=c=>c.src+':'+c.id;
 state.set('cv:idea-group','question');
 assert.match(context.ideaMapSVG(['a','b']),/<title>How does it work\?<\/title>/);
 const svg=context.claimQuestionMap([{src:'s',id:'1',quote:'Evidence'},{src:'s',id:'2',quote:'Other claim'}]);
 assert.match(svg,/<title>How does it work\?<\/title>/);
 assert.match(svg,/<title>No question<\/title>/);
 assert.equal((svg.match(/data-question-claim/g)||[]).length,2);
 context.DATA={sources:[{id:'s',title:'Source PDF'}]};
 state.set('cv:idea-group','all');
 const combined=context.claimQuestionMap([{src:'s',id:'1',quote:'Evidence',tags:['Theory'],pathway:['Mechanism']}]);
 for(const label of ['How does it work?','Source PDF','Theory','Mechanism']) assert.ok(combined.includes('<title>'+label+'</title>'));
 assert.ok(vm.runInContext(`(()=>{
   const keys=[...ideaScene.groups.keys()];
   const outer=ideaGroupBounds(ideaScene,keys.at(-1));
   const leaf=ideaGroupBounds(ideaScene,keys[0]);
   return outer[0]<leaf[0]&&outer[1]<leaf[1]&&outer[2]>leaf[2]&&outer[3]>leaf[3];
 })()`,context));
 state.delete('cv:idea-group');
 context.zkNote=original;
});
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
check('Section notes accept inclusive PDF ranges and reject invalid or out-of-bounds pages',()=>{
 assert.deepEqual(Array.from(context.sectionPages('2–6',6)),[2,6]);
 assert.deepEqual(Array.from(context.sectionPages('4',6)),[4,4]);
 for(const range of ['0','6-2','1-7','1,2','1.5'])assert.equal(context.sectionPages(range,6),null);
});
check('Question drafts reject a second request within one sentence',()=>{
 assert.equal(context.singleDraftQuestion('How did the conception of party shift from a synonym for faction into a legitimate constitutional agent, and what changed in the relationship between parties and constitutional government?'),false);
 assert.equal(context.singleDraftQuestion('How did party legitimacy change? Why?'),false);
 assert.equal(context.singleDraftQuestion('How does Sartori explain the changing place of parties and factions in constitutional government?'),true);
});
check('Guide note creation opens the free-form editor with the reading and page',()=>{
 let opened,seed;
 context.show=mode=>{opened=mode};
 context.zkNew=(parent,value)=>{assert.equal(parent,null);seed=value};
 context.openNewNote({src:'reading',page:9});
 assert.equal(opened,'notes');
 assert.deepEqual({...seed},{src:'reading',page:9,kind:'free'});
});
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
 let destination;
 context.show=(...args)=>{destination=args};
 get('zcol').value='note-collection';
 Object.assign(context.window,{curSrc:()=> 'source-fixture',currentPdfPage:()=>2,currentPdfPageCount:()=>3,pageText:async (_,page)=>page===2?'The author explains the mechanism.':'The evidence supports it.'});
 get('node-context').previousSibling={};
 context.nodeStudio(true);get('node-goal').value='Explain the argument';get('node-context').value='2-3';
 context.pywebview.api.ai_chat=async messages=>{
  assert.match(JSON.parse(messages)[0].content,/one substantive claim per note/);
  assert.deepEqual(JSON.parse(JSON.parse(messages)[1].content).source,{2:'The author explains the mechanism.',3:'The evidence supports it.'});
  return {ok:true,text:'[{"title":"Main argument","body":"The author explains the mechanism and its limits.","page":2,"quote":"The author explains the mechanism.","tags":["Causal mechanisms"]}]'};
 };
 await get('node-generate').onclick();
 check('AI list drafts include content and stay in review until saved',()=>{
  assert.equal(JSON.stringify(context.ZK),before);
  assert.match(get('node-preview').innerHTML,/mechanism and its limits/);
  assert.doesNotMatch(get('node-preview').innerHTML,/data-field="links"/);
  const tags=dialog.fields.find(f=>f.dataset.field==="tags");
  assert.equal(tags.value,"Causal mechanisms");
  tags.value="Causal mechanisms, Evidence";
 });
 context.ZK.notes['9']={id:'9',src:'source-fixture',title:'Saved claim',body:'Already in the notes list.'};
 context.ZK.notes['10']={id:'10',src:'another-pdf',title:'Other reading',body:'Unrelated note.'};
 const beforeMore=JSON.stringify(context.ZK);
 context.pywebview.api.ai_chat=async messages=>{
  const payload=JSON.parse(JSON.parse(messages)[1].content);
  assert.deepEqual(payload.existingClaims.map(note=>note.title),['Main argument','Saved claim']);
  return {ok:true,text:JSON.stringify([
   {title:'Main argument!',body:'Repeated claim',page:2,quote:'The author explains the mechanism.'},
   {title:'Saved claim!',body:'Repeating a saved note',page:2,quote:'The author explains the mechanism.'},
   {title:'Evidence',body:'The evidence supports the mechanism.',page:3,quote:'The evidence supports it.'}
  ])};
 };
 await get('node-more').onclick();
 check('Add more keeps edits and skips drafts and saved claims from the source PDF',()=>{
  assert.equal(JSON.stringify(context.ZK),beforeMore);
  assert.equal(dialog.fields.filter(f=>f.dataset.field==='title').length,2);
  assert.match(get('node-preview').innerHTML,/Causal mechanisms, Evidence/);
  assert.doesNotMatch(get('node-preview').innerHTML,/Repeated claim|Repeating a saved note/);
 });
 get('node-apply').onclick();
 check('AI notes save into the list with content and the chosen collection',()=>{
  const n=Object.values(context.ZK.notes).find(n=>n.title==='Main argument');
  assert.equal(n.body,'The author explains the mechanism and its limits.');
  assert.equal(n.col,'note-collection');
  assert.equal(n.page,2);
  assert.deepEqual(Array.from(n.tags),["Causal mechanisms","Evidence"]);
  assert.equal(n.quote,'The author explains the mechanism.');
  assert.equal(destination[0],'notes');
  assert.equal(destination[1],n.id);
  assert.equal(n.links.length,0);
 });
 console.log(JSON.stringify({passed:checks.length,checks,limitations:['DOM shim, not browser rendering','API stub only; no live model request']},null,2));
})().catch(e=>{console.error(e);process.exitCode=1});
