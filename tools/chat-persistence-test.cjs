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
 pywebview:{api:{ai_chat:async()=>{throw Error('Unexpected fallback')},ai_stream:async(...args)=>{
 assert.equal(args.length,2,'Older desktop executables accept only messages and model');
 return {ok:true,token:'t'}},ai_stream_poll:async()=>{
 if(++polls===1)return {ok:true,r:'Visible reasoning',c:'Partial answer',done:false};await held;return {ok:true,r:'Visible reasoning',c:'Complete answer',done:true};}}}};
ctx.window=ctx;vm.createContext(ctx);
for(const [start,end] of [['const aiLine=','// Follow the newest'],['const aiThinkNew=','const aiStatus='],['const aiLogSync=','const rtab='],['const aiScope=','const aiAsk=']])vm.runInContext(source.slice(source.indexOf(start),source.indexOf(end)),ctx);
(async()=>{
 const pending=vm.runInContext('aiSend("Explain this")',ctx);
 await new Promise(r=>setTimeout(r,20));
 const live=ctx.AI.logs.A.find(n=>n.className==='aim bot'&&!n._removed);
 assert(!live.children.some(n=>n.textContent==='Partial answer'),'Draft must wait for evidence checks');
 assert.equal(ctx.AI.hist.A[0].content,'Explain this','Question must be saved immediately');
 id='B';await vm.runInContext('aiLogSync()',ctx);assert.equal(elements.ailog.children.length,0);
 id='A';await vm.runInContext('aiLogSync()',ctx);assert(elements.ailog.children.includes(live),'Switching back must restore same live reply');
 id='B';await vm.runInContext('aiLogSync()',ctx);release();await pending;
 assert.equal(ctx.AI.hist.A[1].content,'Complete answer','Background reply must be saved to original reading');
 assert.equal(elements.ailog.children.length,0,'Background reply must not appear in another reading');
 id='A';await vm.runInContext('aiLogSync()',ctx);assert.equal(live.answer,'Complete answer');
 assert(!elements.ailog.children.some(n=>n.textContent.startsWith('Preparing PDF')),'Removed indicators must stay removed');
 console.log('PASS: live answer, immediate save, tab restoration, background completion and reading isolation');
 const pages=['[p.1] '+ 'x'.repeat(110000),'[p.2] '+ 'y'.repeat(60000)];
 ctx.aiLoad=async()=>({text:pages.join('\n'),pages});
 let calls=[];
 ctx.pywebview.api.ai_chat=async input=>{
   const prompt=JSON.parse(input).at(-1).content;
   calls.push(prompt);
   if(calls.length===1)return {ok:true,text:'Early finding [p.1: "initial effect"]'};
   if(calls.length===2)return {ok:true,text:'Late caveat [p.2: "no effect after adjustment"]'};
   assert(prompt.includes('initial effect')&&prompt.includes('no effect after adjustment'));
   return {ok:true,text:'The initial effect disappeared after adjustment.'};
 };
 await vm.runInContext('aiSend("Summarize the PDF")',ctx);
 assert.equal(calls.length,3);
 assert(calls[0].includes('[p.1]')&&!calls[0].includes('[p.2]'));
 assert(calls[1].includes('[p.2]'));
 assert.equal(ctx.AI.hist.A.at(-1).content,'The initial effect disappeared after adjustment.');
 let attempts=0;
 ctx.pywebview.api.ai_chat=async()=>++attempts===1?{ok:true,text:'Partial evidence'}:{ok:false,error:'provider offline'};
 await vm.runInContext('aiSend("Try again")',ctx);
 assert.equal(attempts,2);
 assert.equal(ctx.AI.hist.A.at(-1).role,'user','An incomplete reading must not save a partial answer');
 assert(ctx.AI.logs.A.some(n=>n.textContent.includes('Could not read part 2 of 2')));
 console.log('PASS: long PDF uses early and late evidence in one synthesis and reports failed parts');
 const book=['Chapter 1 opening','Chapter 1 conclusion','Chapter 2 opening','Chapter 3 opening'];
 ctx.aiLoad=async()=>({pages:book,text:book.map((p,i)=>'[p.'+(i+1)+'] '+p).join('\n'),
   doc:{getOutline:async()=>[{title:'Chapter 1: Introduction',dest:[0]},{title:'Chapter 2: Methods',dest:[2]}]}});
 ctx.pywebview.api.ai_stream=async input=>{
   const messages=JSON.parse(input),prompt=messages.at(-1).content;
   assert(prompt.includes('Chapter 1 opening')&&prompt.includes('Chapter 1 conclusion'));
   assert(!prompt.includes('Chapter 2 opening')&&!prompt.includes('Chapter 3 opening'));
   assert.equal(messages.length,2,'Prior chat must not supply unrelated chapters');
   return {ok:true,token:'scoped'};
 };
 await vm.runInContext('aiSend("Explain the first chapter, page by page")',ctx);
 assert.equal(ctx.AI.hist.A.at(-1).role,'assistant');
 await vm.runInContext('aiSend("Explain the third chapter")',ctx);
 assert.equal(ctx.AI.hist.A.at(-1).role,'user');
 assert(ctx.AI.logs.A.some(n=>n.textContent.includes('Specify the range shown in the PDF viewer')));
 console.log('PASS: chapter bookmarks limit input and missing boundaries request a PDF page range');
 ctx.pywebview.api.ai_stream=async input=>{
   const messages=JSON.parse(input);
   assert(messages[0].content.includes('one short paragraph'));
   assert(messages.at(-1).content.includes('Chapter 1 conclusion'));
   assert(!messages.at(-1).content.includes('Chapter 1 opening'));
   return {ok:true,token:'passage'};
 };
 await vm.runInContext('aiSend("Explain this passage from page 2: An excerpt.")',ctx);
 assert.equal(ctx.AI.hist.A.at(-1).role,'assistant');
 console.log('PASS: passage explanations request one short paragraph and use only the requested page');
 vm.runInContext(source.slice(source.indexOf('const aiTrace='),source.indexOf('window.__aiTrace=')),ctx);
 ctx.aiModelPick=()=>'mock';
 ctx.pdf={pages:['The estimate fell after adjustment.','The sample included twelve cases.'],text:'[p.1] The estimate fell after adjustment.\n[p.2] The sample included twelve cases.'};
 ctx.pywebview.api.ai_chat=async()=>({ok:true,text:'1. [p.1: "The estimate fell after adjustment and became zero."]\n2. [p.2: "The sample included twelve cases."]'});
 const checked=await vm.runInContext(`aiTrace('The estimate fell. [p.1: "The estimate fell after adjustment."]\\n\\nIt became zero. [p.2: "The estimate fell after adjustment."]\\n\\nThe sample had twelve cases.',pdf)`,ctx);
 assert(checked.includes('The estimate fell. [p.1: "The estimate fell after adjustment."]'));
 assert(!checked.includes('It became zero'));
 assert(!checked.includes('Detail withheld'));
 assert(checked.includes('The sample had twelve cases. [p.2: "The sample included twelve cases."]'));
 console.log('PASS: exact citations survive, wrong-page and fabricated quotes do not, and exact repairs are retained');
 let repairs=0;
 ctx.pywebview.api.ai_chat=()=>{repairs++;return new Promise(()=>{})};
 const cited='The estimate fell. [p.1: "The estimate fell after adjustment."]';
 const trace=vm.runInContext('aiTrace',ctx);
 assert.equal(await trace(cited,ctx.pdf),cited);
 assert.equal(repairs,0,'Exact citations require no provider call');
 ctx.setTimeout=(fn,ms)=>{assert.equal(ms,12000);return setTimeout(fn,0)};
 const slow=await trace(cited+'\n\n'+Array(12).fill('An unsupported detail.').join('\n\n'),ctx.pdf);
 assert.equal(repairs,1,'A slow provider must not trigger retries or extra batches');
 assert.equal(slow,cited);
 console.log('PASS: citation repair times out without delaying verified evidence or exposing unsupported details');
 let completeCalls=0;
 ctx.setTimeout=(fn,ms)=>{assert.equal(ms,15000);return setTimeout(fn,100)};
 ctx.pywebview.api.ai_chat=async()=>{
   completeCalls++;
   return {ok:true,text:'1. [p.2: "The sample included twelve cases."]'};
 };
 const points=Array.from({length:25},(_,i)=>'Detail '+(i+1)+'.').join('\n\n');
 const complete=await trace(points,ctx.pdf,true);
 assert.equal(completeCalls,4,'More complete runs at most four repair batches');
 assert(complete.includes('Detail 19. [p.2: "The sample included twelve cases."]'));
 assert(!complete.includes('Detail 25.'));
 console.log('PASS: More complete repairs later details within its request budget');
})().catch(e=>{console.error(e);process.exitCode=1});
