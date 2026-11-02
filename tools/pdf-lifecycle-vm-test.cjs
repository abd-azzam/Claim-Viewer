const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const template=fs.readFileSync('C:/Apps/ClaimViewer/template/template.html','utf8');
const lifecycle=template.slice(template.indexOf('let pageObserver=null,pdfLoad=null;'),template.indexOf('const zoom=async'));
const show=template.slice(template.indexOf('window.showPdf=async(id,pg)=>'),template.indexOf('const toast=(m,top,ms)=>'));
const deferred=()=>{let resolve,reject;const promise=new Promise((a,b)=>{resolve=a;reject=b});return {promise,resolve,reject}};
const tick=async()=>{for(let i=0;i<12;i++)await Promise.resolve()};
class Element{
 constructor(tag='div'){this.tag=tag;this.children=[];this.dataset={};this.style={setProperty(){}};this.hidden=false;this.isConnected=false;this.width=1;this.height=1;this.clientWidth=1020;this.options=[];this.value='';this._html=''}
 set innerHTML(v){this._html=v;this.children.forEach(c=>c.isConnected=false);this.children=[]}get innerHTML(){return this._html}
 append(c){c.parent=this;c.isConnected=true;this.children.push(c)}
 querySelectorAll(sel){return this.children.flatMap(c=>[...(sel==='canvas'&&c.tag==='canvas'||sel==='.textLayer'&&c.className==='textLayer'?[c]:[]),...c.querySelectorAll(sel)])}
 querySelector(sel){return this.querySelectorAll(sel)[0]||null}
 remove(){if(this.parent)this.parent.children=this.parent.children.filter(c=>c!==this);this.isConnected=false}
 getContext(){return {}}removeAttribute(){}insertAdjacentHTML(){}
}
function fixture(){
 const elements={},observers=[],loads=[];const get=id=>elements[id]||(elements[id]=new Element());
 const ctx=vm.createContext({console,Uint8Array,Math,JSON,Set,devicePixelRatio:4,rd:get('rd'),s:get('pdfsel'),f:get('pdf'),lpn:get('lpn'),rt:get('rt'),zv:get('zv'),document:{createElement:t=>new Element(t),body:{classList:{contains:()=>false}}},window:{pdfjsLib:{}},localStorage:{getItem:()=>null},store:{set(){}},$:get,HL:()=>({}),mkHL:()=>new Element,scroll(){},savePage(){},drawLib(){},fallback(){},forgetPage(){},ready:async()=>true,bytes:async()=>new Uint8Array([1,2]),ocrHydrate:async()=>{},showPage(){},aiLoad(){},readingTabs:[],paintReadingTabs(){},DATA:{sources:[]},esc:String,pdfjsLib:{renderTextLayer:()=>({promise:Promise.resolve()}),getDocument(){const d=deferred(),task={promise:d.promise,destroyed:0,destroy:async()=>{task.destroyed++}};loads.push({task,...d});return task}},IntersectionObserver:class{constructor(callback){this.callback=callback;this.observed=[];this.disconnected=false;observers.push(this)}observe(d){this.observed.push(d)}unobserve(d){this.observed=this.observed.filter(x=>x!==d)}disconnect(){this.disconnected=true}},});
 vm.runInContext('let Z=1,docC=null,curBuf=null,bt=0,cur="",tok=0,lastPg=1,lastPgId="";'+lifecycle+show,ctx);
 return {ctx,get,observers,loads,run:code=>vm.runInContext(code,ctx)};
}
function page(width=1000,height=1500){const renders=[];return {renders,cleanupCount:0,getViewport:({scale})=>({width:width*scale,height:height*scale,scale}),render(){const d=deferred(),t={promise:d.promise,cancelled:0,cancel(){this.cancelled++}};renders.push({...d,task:t});return t},getTextContent:async()=>({items:[]}),cleanup(){this.cleanupCount++}}}
const tests=[];async function test(name,fn){try{await fn();tests.push({name,ok:true})}catch(e){tests.push({name,ok:false,error:e.message})}}
(async()=>{
 await test('clearPages cancels tasks, disconnects observer and zeroes canvases',async()=>{const f=fixture(),c=new Element('canvas');f.get('rd').append(c);f.ctx.t={cancelled:0,cancel(){this.cancelled++}};f.run('renderTasks.add(t);pageObserver=new IntersectionObserver(()=>{});clearPages()');assert.equal(f.ctx.t.cancelled,1);assert.equal(f.observers[0].disconnected,true);assert.equal(c.width,0);assert.equal(c.height,0);assert.equal(f.run('renderTasks.size'),0);assert.equal(f.get('rd').children.length,0)});
 await test('releaseReader destroys active document and clears references',async()=>{const f=fixture();f.ctx.d={n:0,destroy:async function(){this.n++}};f.run('docC=d;curBuf=new Uint8Array([1])');await f.run('releaseReader()');assert.equal(f.ctx.d.n,1);assert.equal(f.run('docC===null&&curBuf===null'),true)});
 await test('releaseReader destroys pending loading task',async()=>{const f=fixture();f.ctx.t={n:0,destroy:async function(){this.n++}};f.run('pdfLoad=t');await f.run('releaseReader()');assert.equal(f.ctx.t.n,1);assert.equal(f.run('pdfLoad===null'),true)});
 await test('visible canvas raster stays within four million pixels and evicts offscreen',async()=>{const f=fixture(),p=page(1000,2000);f.ctx.d={numPages:1,getPage:async()=>p};f.run('docC=d');await f.run('build(1)');const node=f.get('rd').children[0],io=f.observers[0];io.callback([{target:node,isIntersecting:true}]);const c=node.querySelector('canvas');assert.ok(c.width*c.height<=4000000);io.callback([{target:node,isIntersecting:false}]);assert.equal(c.width,0);assert.equal(c.height,0);assert.equal(node.querySelector('canvas'),null);assert.equal(p.renders[0].task.cancelled,1);p.renders[0].reject({name:'RenderingCancelledException'});await tick();assert.equal(p.cleanupCount,1)});
 await test('stale builds stop adding pages after awaited getPage',async()=>{const f=fixture(),d=deferred();f.ctx.d={numPages:2,getPage:()=>d.promise};f.run('docC=d');const b=f.run('build(1)');f.run('clearPages()');d.resolve(page());await b;assert.equal(f.get('rd').children.length,0)});
 await test('queued stale observer callbacks cannot restart old rendering',async()=>{const f=fixture(),p=page();f.ctx.d={numPages:1,getPage:async()=>p};f.run('docC=d');await f.run('build(1)');const node=f.get('rd').children[0],io=f.observers[0];f.run('clearPages()');io.callback([{target:node,isIntersecting:true}]);assert.equal(p.renders.length,0)});
 await test('stale PDF load is disposed without replacing newer document',async()=>{const f=fixture(),p=page();const a=f.ctx.window.showPdf('a',1);await tick();assert.equal(f.loads.length,1);const b=f.ctx.window.showPdf('b',1);await tick();assert.equal(f.loads.length,2);const old={destroyed:0,destroy:async function(){this.destroyed++}},latest={numPages:1,getPage:async()=>p,destroy:async()=>{}};f.loads[1].resolve(latest);await b;f.loads[0].resolve(old);await a;assert.equal(old.destroyed,1);assert.equal(f.run('docC'),latest);assert.equal(f.loads[0].task.destroyed,1)});
 console.log(JSON.stringify({passed:tests.filter(t=>t.ok).length,total:tests.length,tests},null,2));if(tests.some(t=>!t.ok))process.exitCode=1;
})().catch(e=>{console.error(e);process.exitCode=1});
