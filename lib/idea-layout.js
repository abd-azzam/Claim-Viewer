// Bounded spring/collision layout. No simulation runs while the graph is idle.
function layoutIdeas(groups,links,saved,aspect=1.5){
 const pos=new Map(),centers=new Map();let area=0;
 groups.forEach(ids=>area+=Math.pow(Math.max(240,Math.sqrt(ids.length)*155),2));
 const wrap=Math.max(500,Math.sqrt(area*Math.max(.6,Math.min(2,aspect))));let x=80,y=80,rowH=0;
 groups.forEach((ids,key)=>{const size=Math.max(240,Math.sqrt(ids.length)*155);
  if(x>80&&x+size>wrap+80){x=80;y+=rowH+70;rowH=0}
  const cx=x+size/2,cy=y+size/2;centers.set(key,[cx,cy]);
  ids.forEach((id,i)=>{const p=saved[id],r=55*Math.sqrt(i),a=i*2.399963;
   pos.set(id,p&&Number.isFinite(p[0])&&Number.isFinite(p[1])?[...p]:[cx+Math.cos(a)*r,cy+Math.sin(a)*r])});
  x+=size+70;rowH=Math.max(rowH,size);
 });
 if([...pos.keys()].every(id=>saved[id]))return pos;
 const anchors=new Map();groups.forEach((ids,key)=>ids.forEach(id=>anchors.set(id,centers.get(key))));
 for(let tick=0;tick<36;tick++){
  const delta=new Map(),grid=new Map();
  pos.forEach((p,id)=>{delta.set(id,[0,0]);const key=Math.floor(p[0]/130)+','+Math.floor(p[1]/130);if(!grid.has(key))grid.set(key,[]);grid.get(key).push(id)});
  pos.forEach((p,id)=>{const d=delta.get(id),gx=Math.floor(p[0]/130),gy=Math.floor(p[1]/130);
   for(let a=-1;a<=1;a++)for(let b=-1;b<=1;b++)for(const other of grid.get((gx+a)+','+(gy+b))||[]){
    if(other===id)continue;const q=pos.get(other),dx=p[0]-q[0],dy=p[1]-q[1],len=Math.hypot(dx,dy)||1;
    if(len<120){d[0]+=dx/len*(120-len)*.16;d[1]+=dy/len*(120-len)*.16}
   }
   const c=anchors.get(id);d[0]+=(c[0]-p[0])*.008;d[1]+=(c[1]-p[1])*.008;
  });
  links.forEach(([a,b])=>{if(!pos.has(a)||!pos.has(b))return;const p=pos.get(a),q=pos.get(b),dx=q[0]-p[0],dy=q[1]-p[1],len=Math.hypot(dx,dy)||1;
   const f=(len-150)*.012;delta.get(a)[0]+=dx/len*f;delta.get(a)[1]+=dy/len*f;delta.get(b)[0]-=dx/len*f;delta.get(b)[1]-=dy/len*f});
  pos.forEach((p,id)=>{if(saved[id])return;const d=delta.get(id);p[0]+=Math.max(-15,Math.min(15,d[0]));p[1]+=Math.max(-15,Math.min(15,d[1]))});
 }return pos;
}
let ideaScene=null;
function layoutSourceTopics(groups,sourceTopics,links,saved,aspect){
 const plans=[],pos=new Map();let area=0;
 sourceTopics.forEach(keys=>{
  const localGroups=new Map(keys.map(key=>[key,groups.get(key)])),members=new Set(keys.flatMap(key=>groups.get(key)));
  const local=layoutIdeas(localGroups,links.filter(([a,b])=>members.has(a)&&members.has(b)),{},aspect);
  const bounds=ideaBounds(local,[...members]),w=bounds[2]-bounds[0]+100,h=bounds[3]-bounds[1]+120;
  plans.push({local,bounds,w,h});area+=w*h;
 });
 const wrap=Math.max(600,Math.sqrt(area*Math.max(.6,Math.min(2,aspect))));let x=80,y=80,rowH=0;
 plans.forEach(({local,bounds,w,h})=>{
  if(x>80&&x+w>wrap+80){x=80;y+=rowH+100;rowH=0}
  local.forEach((p,id)=>pos.set(id,saved[id]&&saved[id].every(Number.isFinite)?[...saved[id]]:[p[0]-bounds[0]+x+50,p[1]-bounds[1]+y+70]));
  x+=w+100;rowH=Math.max(rowH,h);
 });return pos;
}
function ideaBounds(pos,ids){const points=ids.map(id=>pos.get(id));return [Math.min(...points.map(p=>p[0]))-90,Math.min(...points.map(p=>p[1]))-65,Math.max(...points.map(p=>p[0]))+90,Math.max(...points.map(p=>p[1]))+65]}
function ideaGroupBounds(scene,key){const b=ideaBounds(scene.pos,scene.groups.get(key));return scene.parents?.has(key)?[b[0]-35,b[1]-45,b[2]+35,b[3]+35]:b}
function wireIdeaDrag(pane){
 let drag=null,frame=0,suppress=false;
 const point=e=>{const p=drag.svg.createSVGPoint();p.x=e.clientX;p.y=e.clientY;return p.matrixTransform(drag.svg.getScreenCTM().inverse())};
 function paint(){frame=0;if(!drag)return;const scene=drag.scene;
  drag.nodes.forEach(el=>{const p=scene.pos.get(el.dataset.ideaId);el.setAttribute('transform',`translate(${p[0]},${p[1]})`)});
  drag.edges.forEach(el=>{const a=scene.pos.get(el.dataset.from),b=scene.pos.get(el.dataset.to);el.setAttribute('d',`M${a[0]},${a[1]} L${b[0]},${b[1]}`)});
  drag.hulls.forEach(el=>{const b=ideaGroupBounds(scene,el.dataset.ideaGroup);el.setAttribute('x',b[0]);el.setAttribute('y',b[1]);el.setAttribute('width',b[2]-b[0]);el.setAttribute('height',b[3]-b[1])});
  drag.labels.forEach(el=>{const b=ideaGroupBounds(scene,el.dataset.ideaGroup);el.setAttribute('x',b[0]+20);el.setAttribute('y',b[1]+25)});
 }
 function end(cancel=false){if(!drag)return;if(frame){cancelAnimationFrame(frame);frame=0}paint();const d=drag;drag=null;
  try{pane.releasePointerCapture(d.pid)}catch(e){}if(!d.moved)return;suppress=true;setTimeout(()=>{suppress=false},0);
  let saved={};try{saved=JSON.parse(localStorage.getItem(d.scene.key)||'{}')||{}}catch(e){}d.ids.forEach(id=>saved[id]=d.scene.pos.get(id));store.set(d.scene.key,JSON.stringify(saved));
  if(!cancel)graph();
 }
 pane.addEventListener('pointerdown',e=>{if(e.button!==0||!ideaScene)return;const node=e.target.closest('[data-idea-id]'),group=e.target.closest('[data-idea-group]');if(!node&&!group)return;
  const svg=e.target.closest('svg.idea-map');if(!svg)return;const ids=node?[node.dataset.ideaId]:ideaScene.groups.get(group.dataset.ideaGroup);
  drag={scene:ideaScene,svg,pid:e.pointerId,nodeId:node?.dataset.ideaId,ids,start:null,moved:false,initial:new Map(ids.map(id=>[id,[...ideaScene.pos.get(id)]])),nodes:[...svg.querySelectorAll('[data-idea-id]')],edges:[...svg.querySelectorAll('[data-from]')],hulls:[...svg.querySelectorAll('rect[data-idea-group]')],labels:[...svg.querySelectorAll('text[data-idea-group]')]};
  drag.start=point(e);e.preventDefault();e.stopPropagation();pane.setPointerCapture(e.pointerId);
 });
 pane.addEventListener('pointermove',e=>{if(!drag||e.pointerId!==drag.pid)return;if(!(e.buttons&1)){end();return}const p=point(e),dx=p.x-drag.start.x,dy=p.y-drag.start.y;
  if(!drag.moved&&Math.hypot(dx,dy)<4)return;drag.moved=true;drag.ids.forEach(id=>{const a=drag.initial.get(id);drag.scene.pos.set(id,[a[0]+dx,a[1]+dy])});if(!frame)frame=requestAnimationFrame(paint);
 });
 pane.addEventListener('pointerup',e=>{if(!drag||e.pointerId!==drag.pid)return;
  const id=drag.nodeId,moved=drag.moved;end();
  if(!moved&&id){suppress=true;setTimeout(()=>{suppress=false},0);openIdeaNote(id)}
 });
 pane.addEventListener('pointercancel',()=>end(true));pane.addEventListener('lostpointercapture',()=>end(true));window.addEventListener('blur',()=>end(true));
 pane.addEventListener('click',e=>{if(suppress){e.preventDefault();e.stopImmediatePropagation()}},true);
}
