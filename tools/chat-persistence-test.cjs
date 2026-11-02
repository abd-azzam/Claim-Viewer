const fs=require('fs'),vm=require('vm'),assert=require('assert');
const source=fs.readFileSync('C:/Apps/ClaimViewer/template/template.html','utf8');
class Element{
 constructor(){this.children=[];this.textContent='';this.style={};this.classList={remove(){}};this.isConnected=false;}
 append(...nodes){for(const n of nodes){n.parent=this;this.children.push(n);n.isConnected=this.isConnected;}}
 appendChild(n){this.append(n);}
 replaceChildren(...nodes){for(const n of this.children){n.parent=null;n.isConnected=false;}this.children=[];this.append(...nodes);}
 remove(){if(this.parent)this.parent.children=this.parent.children.filter(n=>n!==this);this.parent=null;this.isConnected=false;}
 querySelector(sel){if(sel==='.aithink')return this.children.find(n=>n.className==='aithink');if(sel==='summary')return this.children[0];if(sel==='summary span')return this.children[0]?.children[0]?.children[0];return null;}
}
const elements={ailog:new Element(),aisend:new Element(),aimodel:{options:[{value:'mock'}],value:'mock'}};elements.ailog.isConnected=true;
let id='A',release;const held=new Promise(r=>release=r);let polls=0;
const ctx={AI:{hist:{},logs:{},busy:false},document:{createElement:()=>new Element()},$:key=>elements[key],aiId:()=>id,
 aiClearBtn(){},aiSave(){},histOf:key=>ctx.AI.hist[key]||(ctx.AI.hist[key]=[]),aiLoad:async()=>({text:'[p.1] A passage.',pages:['A passage.']}),
 aiTitle:()=>id,aiPin(){},aiTrace:async text=>text,aiCite:(box,text)=>{box.answer=text},aiStrong(){},progShow(){},
 performance,setTimeout,clearTimeout,setInterval,clearInterval,
 pywebview:{api:{ai_chat:async()=>{throw Error('Unexpected fallback')},ai_stream:async()=>({ok:true,token:'t'}),ai_stream_poll:async()=>{
 if(++polls===1)return {ok:true,r:'Visible reasoning',c:'Partial answer',done:false};await held;return {ok:true,r:'Visible reasoning',c:'Complete answer',done:true};}}}};
ctx.window=ctx;vm.createContext(ctx);
for(const [start,end] of [['const aiLine=','// Follow the newest'],['const aiThinkNew=','const aiStatus='],['const aiLogSync=','const rtab='],['const aiSend=','const aiAsk=']])vm.runInContext(source.slice(source.indexOf(start),source.indexOf(end)),ctx);
(async()=>{
 const pending=vm.runInContext('aiSend("Explain this")',ctx);
 await new Promise(r=>setTimeout(r,20));
 const live=ctx.AI.logs.A.find(n=>n.className==='aim bot'&&!n._removed);
 assert(live.children.some(n=>n.textContent==='Partial answer'),'Answer must be visible before completion');
 assert.equal(ctx.AI.hist.A[0].content,'Explain this','Question must be saved immediately');
 id='B';await vm.runInContext('aiLogSync()',ctx);assert.equal(elements.ailog.children.length,0);
 id='A';await vm.runInContext('aiLogSync()',ctx);assert(elements.ailog.children.includes(live),'Switching back must restore same live reply');
 id='B';await vm.runInContext('aiLogSync()',ctx);release();await pending;
 assert.equal(ctx.AI.hist.A[1].content,'Complete answer','Background reply must be saved to original reading');
 assert.equal(elements.ailog.children.length,0,'Background reply must not appear in another reading');
 id='A';await vm.runInContext('aiLogSync()',ctx);assert.equal(live.answer,'Complete answer');
 assert(!elements.ailog.children.some(n=>n.textContent.startsWith('Preparing PDF')),'Removed indicators must stay removed');
 console.log('PASS: live answer, immediate save, tab restoration, background completion and reading isolation');
})().catch(e=>{console.error(e);process.exitCode=1});
