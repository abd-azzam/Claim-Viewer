setTimeout(async()=>{
 const results=[];const check=(name,ok,detail='')=>results.push({name,ok,detail});
 try{
  check('workspace loaded',typeof libraryWorkspace==='function'&&typeof nodeStudio==='function');
  localStorage.setItem('cv:library-view','cards');show('lib');drawLibTable();
  check('cards render',document.querySelectorAll('.library-card').length>0);
  document.querySelector('[data-library-view="table"]').click();
  check('table renders',!!document.querySelector('#libtbl table'));
  const cardsButton=document.querySelector('[data-library-view="cards"]');
  check('cards toggle exists',!!cardsButton);cardsButton?.click();
  check('cards restored',document.querySelectorAll('.library-card').length>0);
  ZK={seq:0,notes:{}};zkSel=null;
  nodeStudio();document.getElementById('node-goal').value='Fixture ideas';
  document.getElementById('node-manual').click();
  document.querySelector('[data-node="0"][data-field="title"]').value='Edited first idea';
  document.getElementById('node-manual').click();
  check('manual add preserves edits',document.querySelector('[data-node="0"][data-field="title"]').value==='Edited first idea');
  document.querySelector('[data-node="0"][data-field="title"]').value='First idea';
  document.querySelector('[data-node="1"][data-field="title"]').value='Second idea';
  document.querySelector('[data-node="0"][data-field="links"]').value='2';
  document.getElementById('node-apply').click();
  check('manual adds two nodes',Object.keys(ZK.notes).length===2,JSON.stringify(ZK.notes));
  check('links use note schema',Object.values(ZK.notes)[0]?.links?.[0]?.to===Object.keys(ZK.notes)[1]);
  check('graph appears',document.querySelectorAll('#gout .node').length===2,document.getElementById('node-status')?.textContent||'');
  doUndo();check('undo removes batch',Object.keys(ZK.notes).length===0);
  window.pywebview={api:{ai_chat:async()=>({ok:true,text:JSON.stringify([{title:'Draft A',body:'Source grounded A',links:[1]},{title:'Draft B',body:'Source grounded B',links:[]}])})}};
  nodeStudio();document.getElementById('node-goal').value='Fixture AI';document.getElementById('node-context').value='Fixture source text';
  document.getElementById('node-generate').click();await new Promise(r=>setTimeout(r,100));
  check('AI preview renders',document.querySelectorAll('#node-preview fieldset').length===2,document.getElementById('node-status').textContent);
  check('AI preview does not save',Object.keys(ZK.notes).length===0);
 }catch(e){check('uncaught probe error',false,e.stack)}
 const out=document.createElement('pre');out.id='probe-results';out.textContent=JSON.stringify(results);document.body.append(out);
},1000);
