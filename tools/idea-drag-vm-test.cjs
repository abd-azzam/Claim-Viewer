const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
class Target{
 constructor(dataset={}){this.dataset=dataset;this.listeners={};this.attrs={}}
 addEventListener(type,fn){(this.listeners[type]??=[]).push(fn)}
 emit(type,extra={}){const e={button:0,buttons:1,pointerId:1,clientX:0,clientY:0,target:this,prevented:false,stopped:false,immediate:false,preventDefault(){this.prevented=true},stopPropagation(){this.stopped=true},stopImmediatePropagation(){this.immediate=true},...extra};for(const fn of this.listeners[type]||[]){fn(e);if(e.immediate)break}return e}
 setAttribute(k,v){this.attrs[k]=String(v)}
}
function fixture(){
 const pane=new Target,win=new Target,frames=new Map,timers=[],saved=new Map;let rafId=0,rafRequests=0,graphs=0,fits=0,notes=[];
 const a=new Target({ideaId:'a'}),b=new Target({ideaId:'b'}),edge=new Target({from:'a',to:'b'}),hull=new Target({ideaGroup:'g'}),label=new Target({ideaGroup:'g'});
 const svg={createSVGPoint:()=>({x:0,y:0,matrixTransform(){return {x:this.x,y:this.y}}}),getScreenCTM:()=>({inverse:()=>({})}),querySelectorAll:s=>s==='[data-idea-id]'?[a,b]:s==='[data-from]'?[edge]:s==='rect[data-idea-group]'?[hull]:s==='text[data-idea-group]'?[label]:[]};
 for(const el of [a,b,edge,hull,label])el.closest=s=>s==='svg.idea-map'?svg:s==='[data-idea-id]'&&el.dataset.ideaId?el:s==='[data-idea-group]'&&el.dataset.ideaGroup?el:null;
 pane.setPointerCapture=id=>pane.captured=id;pane.releasePointerCapture=id=>{assert.equal(id,pane.captured);pane.captured=null;pane.emit('lostpointercapture')};
 const ctx=vm.createContext({window:win,localStorage:{getItem:k=>saved.get(k)||null},store:{set:(k,v)=>saved.set(k,v)},requestAnimationFrame:fn=>{rafRequests++;frames.set(++rafId,fn);return rafId},cancelAnimationFrame:id=>frames.delete(id),setTimeout:fn=>timers.push(fn),graph:()=>graphs++,graphZoomSet:v=>{assert.equal(v,'fit');fits++},openIdeaNote:id=>notes.push(id),console});
 vm.runInContext(fs.readFileSync('C:/Apps/ClaimViewer/lib/idea-layout.js','utf8'),ctx);ctx.pane=pane;
 vm.runInContext("ideaScene={key:'fixture',pos:new Map([['a',[100,100]],['b',[200,200]]]),groups:new Map([['g',['a','b']]])};wireIdeaDrag(pane)",ctx);
 const positions=()=>JSON.parse(vm.runInContext('JSON.stringify([...ideaScene.pos])',ctx));
 return {pane,win,a,b,edge,hull,label,frames,saved,positions,stats:()=>({rafRequests,graphs,fits,notes}),tick:()=>{const f=[...frames.values()];frames.clear();f.forEach(fn=>fn())},timers:()=>{while(timers.length)timers.shift()()}};
}
const results=[];function test(name,fn){try{fn();results.push({name,ok:true})}catch(e){results.push({name,ok:false,error:e.stack})}}
test('Node drag moves only node; paints edges/hull/label and saves position',()=>{
 const f=fixture();f.pane.emit('pointerdown',{target:f.a,clientX:10,clientY:10});f.pane.emit('pointermove',{clientX:35,clientY:45});f.tick();
 assert.deepEqual(f.positions(),[['a',[125,135]],['b',[200,200]]]);assert.equal(f.a.attrs.transform,'translate(125,135)');assert.equal(f.edge.attrs.d,'M125,135 L200,200');assert.equal(f.hull.attrs.x,'35');assert.equal(f.hull.attrs.y,'70');assert.equal(f.hull.attrs.width,'255');assert.equal(f.label.attrs.x,'55');
 f.pane.emit('pointerup');assert.deepEqual(JSON.parse(f.saved.get('fixture')),{a:[125,135]});assert.equal(f.stats().graphs,1);assert.equal(f.stats().fits,0,"Dragging preserves the current zoom");assert.equal(f.pane.captured,null);
});
test('Group drag moves and saves all members by the same delta',()=>{
 const f=fixture();f.pane.emit('pointerdown',{target:f.hull});f.pane.emit('pointermove',{clientX:50,clientY:-25});f.pane.emit('pointerup');assert.deepEqual(f.positions(),[['a',[150,75]],['b',[250,175]]]);assert.deepEqual(JSON.parse(f.saved.get('fixture')),{a:[150,75],b:[250,175]});assert.equal(f.edge.attrs.d,'M150,75 L250,175');
});
test('Multiple moves schedule one animation frame and paint latest position',()=>{
 const f=fixture();f.pane.emit('pointerdown',{target:f.a});for(let n=5;n<=20;n++)f.pane.emit('pointermove',{clientX:n,clientY:n});assert.equal(f.frames.size,1);assert.equal(f.stats().rafRequests,1);f.tick();assert.equal(f.a.attrs.transform,'translate(120,120)');f.pane.emit('pointermove',{clientX:25,clientY:25});assert.equal(f.stats().rafRequests,2);assert.equal(f.frames.size,1);
});
for(const event of ['pointerup','pointercancel','lostpointercapture','blur','buttons-released'])test(`${event} ends drag; queued and later movement cannot move nodes`,()=>{
 const f=fixture();f.pane.emit('pointerdown',{target:f.a});f.pane.emit('pointermove',{clientX:20,clientY:30});
 if(event==='blur')f.win.emit('blur');else if(event==='buttons-released')f.pane.emit('pointermove',{buttons:0,clientX:25,clientY:35});else f.pane.emit(event);
 const p=f.positions();assert.equal(f.frames.size,0);f.pane.emit('pointermove',{clientX:500,clientY:500});f.tick();assert.deepEqual(f.positions(),p);assert.equal(f.pane.captured,null);assert.equal(f.stats().notes.length,0);
});
test('A click opens once and suppresses following synthetic click; drag never navigates',()=>{
 const f=fixture();f.pane.emit('pointerdown',{target:f.a});f.pane.emit('pointermove',{clientX:2,clientY:1});assert.equal(f.frames.size,0);f.pane.emit('pointerup');assert.deepEqual(f.stats().notes,['a']);assert.equal(f.saved.size,0);assert.equal(f.pane.emit('click',{target:f.a}).immediate,true);f.timers();assert.equal(f.pane.emit('click',{target:f.a}).prevented,false);
 f.pane.emit('pointerdown',{target:f.b});f.pane.emit('pointermove',{clientX:10,clientY:10});f.pane.emit('pointerup');assert.deepEqual(f.stats().notes,['a']);assert.equal(f.pane.emit('click',{target:f.b}).prevented,true);
});
test('Wrong pointer and non-primary button cannot move graph',()=>{
 const f=fixture();f.pane.emit('pointerdown',{target:f.a,button:2});f.pane.emit('pointermove',{clientX:50,clientY:50});assert.deepEqual(f.positions(),[['a',[100,100]],['b',[200,200]]]);f.pane.emit('pointerdown',{target:f.a});f.pane.emit('pointermove',{pointerId:2,clientX:50,clientY:50});f.pane.emit('pointerup',{pointerId:2});assert.deepEqual(f.positions(),[['a',[100,100]],['b',[200,200]]]);f.pane.emit('pointerup');assert.deepEqual(f.stats().notes,['a']);
});
console.log(JSON.stringify({passed:results.filter(r=>r.ok).length,total:results.length,results},null,2));if(results.some(r=>!r.ok))process.exitCode=1;
