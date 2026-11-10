const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const prefs=new Map(),svg={style:{},dataset:{},getAttribute:()=> '0 0 2000 1000'};
const pane={clientWidth:800,clientHeight:500,scrollLeft:300,scrollTop:100,querySelector:()=>svg};
const label={},group={};let rebuilds=0,checks=0;
const notes={a:{id:'a',title:'A',src:'pdf-a',tags:['Topic'],links:[{to:'b'}]},b:{id:'b',title:'B',src:'pdf-b',tags:['Topic'],links:[]},c:{id:'c',title:'Child',tags:[],links:[]},d:{id:'d',title:'Unfiled',tags:[],links:[]}};
const ctx=vm.createContext({console,Math,Number,Map,Set,Date,document:{addEventListener(){},getElementById:id=>id==='gout'?pane:id==='idea-group'?group:label},localStorage:{getItem:k=>prefs.get(k)||null},G:{m:'Z'},syncGX(){},graph(){rebuilds++},DATA:{sources:[{id:'pdf-a',title:'Same title'},{id:'pdf-b',title:'Same title'}]},zkNote:id=>notes[id],zkTags:n=>n.tags,zkNest:()=>[],zkPaths:()=>[],zkHome:n=>n.id==='c'?notes.a:n,LNK:true,esc:s=>String(s).replaceAll('<','&lt;').replaceAll('&','&amp;')});
vm.runInContext(fs.readFileSync('C:/Apps/ClaimViewer/lib/idea-layout.js','utf8')+fs.readFileSync('C:/Apps/ClaimViewer/lib/workspace.js','utf8'),ctx);
for(const mode of ['L','C','K','R','Z']){
 ctx.G.m=mode;pane.scrollLeft=300;pane.scrollTop=100;ctx.graphZoomApply();const w=parseFloat(svg.style.width),h=parseFloat(svg.style.height);
 ctx.graphZoomSet(2);assert.equal(parseFloat(svg.style.width),w*2);assert.equal(parseFloat(svg.style.height),h*2);assert.equal(pane.scrollLeft,1000);assert.equal(pane.scrollTop,450);
 ctx.graphZoomSet('fit');assert.ok(parseFloat(svg.style.width)<=pane.clientWidth);assert.ok(parseFloat(svg.style.height)<=pane.clientHeight);
 ctx.graphZoomSet(1);assert.equal(parseFloat(svg.style.width),w);checks++;
}
assert.equal(rebuilds,0);checks++;
ctx.graphZoomSet(99);assert.equal(label.textContent,'400%');ctx.graphZoomSet(.00001);assert.equal(label.textContent,'0.1%');checks++;
prefs.set('cv:idea-group','source');let out=ctx.ideaMapSVG(Object.keys(notes));assert.equal((out.match(/class="idea-hull"/g)||[]).length,3);assert.match(out,/No PDF source/);assert.match(out,/grouped by PDF source/);checks++;
prefs.set('cv:idea-group','topic');out=ctx.ideaMapSVG(Object.keys(notes));assert.match(out,/grouped by topic/);assert.equal((out.match(/class="idea-hull"/g)||[]).length,2);checks++;
// Same tag in two PDFs must stay two topic hulls, each nested in its own source hull.
// A source id that looks like "source|tag" must not swallow that topic group.
notes.e={id:'e',title:'E',src:'pdf-a|Topic',tags:['Other'],links:[]};
prefs.set('cv:idea-group','source-topic');out=ctx.ideaMapSVG(Object.keys(notes));assert.match(out,/grouped by PDF source and topic/);
assert.equal((out.match(/class="idea-source-hull"/g)||[]).length,4);assert.equal((out.match(/class="idea-hull"/g)||[]).length,5);
assert.ok(vm.runInContext('[...ideaScene.groups].some(([k,v])=>ideaScene.parents.has(k)&&!ideaScene.outer.has(k)&&v.includes("a"))',ctx),'Note a keeps its topic hull');assert.deepEqual([...vm.runInContext('ideaScene.groups.get("pdf-a|Topic")',ctx)],['e']);
assert.deepEqual([...vm.runInContext('ideaScene.groups.get("pdf-a")',ctx)].sort(),['a','c']);assert.equal(vm.runInContext('ideaScene.key',ctx),'cv:idea-pos:source-topic:nested');
group.value='';ctx.graphZoomApply();assert.equal(group.value,'source-topic','Dropdown keeps the nested mode on redraw');checks++;
console.log(`${checks} source-grouping and zoom checks passed (all five graph modes).`);
