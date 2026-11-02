const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const html=fs.readFileSync('C:/Apps/ClaimViewer/template/template.html','utf8');
class Target{
 constructor(){this.handlers={};this.scrollLeft=100;this.scrollTop=100;this.classList={add(){},remove(){}};this.captures=0}
 addEventListener(k,f){(this.handlers[k]??=[]).push(f)}
 fire(k,props={}){const e={button:0,buttons:1,pointerId:7,clientX:0,clientY:0,target:{closest:()=>null},preventDefault(){this.prevented=true},stopPropagation(){this.stopped=true},...props};(this.handlers[k]||[]).forEach(f=>f(e));return e}
 setPointerCapture(){this.captures++}releasePointerCapture(){this.captures--}
}
const document=new Target,window=new Target,ctx=vm.createContext({document,window,Math});
vm.runInContext(html.slice(html.indexOf('const panInit=el=>'),html.indexOf('panInit($("gout"))'))+'\nthis.initPan=panInit;',ctx);
let checks=0;
for(const [button,buttons] of [[0,1],[1,4],[2,2]]){
 const el=new Target;ctx.initPan(el);el.fire('pointerdown',{button,buttons});el.fire('pointermove',{buttons,clientX:20});assert.equal(el.scrollLeft,80);
 el.fire('pointerup',{button,buttons:0});el.fire('pointermove',{buttons:0,clientX:90});assert.equal(el.scrollLeft,80);assert.equal(el.captures,0);checks++;
}
for(const stop of ['missing-button','outside-release','cancel','lost-capture','blur']){
 const el=new Target;ctx.initPan(el);el.fire('pointerdown',{button:2,buttons:2});el.fire('pointermove',{buttons:2,clientX:20});
 if(stop==='missing-button')el.fire('pointermove',{buttons:0,clientX:25});
 if(stop==='outside-release')document.fire('pointerup',{buttons:0});
 if(stop==='cancel')el.fire('pointercancel');if(stop==='lost-capture')el.fire('lostpointercapture');if(stop==='blur')window.fire('blur');
 el.fire('pointermove',{buttons:2,clientX:90});assert.equal(el.scrollLeft,80,stop);assert.equal(el.captures,0);checks++;
}
const el=new Target;ctx.initPan(el);el.fire('pointerdown',{target:{closest:()=>({})}});assert.equal(el.captures,0);checks++;
assert.equal(el.fire('mousedown',{button:1}).prevented,true);checks++;
let opened,scrolled=0;ctx.zkNote=id=>({id});ctx.show=(...args)=>opened=args;document.querySelectorAll=()=>[{dataset:{zk:'chosen'},scrollIntoView(){scrolled++}}];
const js=fs.readFileSync('C:/Apps/ClaimViewer/lib/workspace.js','utf8');vm.runInContext(js.slice(0,js.indexOf('function ideaMapSVG')),ctx);ctx.openIdeaNote('chosen');assert.deepEqual(opened,['notes','chosen']);assert.equal(scrolled,1);checks++;
console.log(`${checks} graph interaction checks passed (simulated events; native UI unverified).`);
