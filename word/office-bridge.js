// Word hosts this task pane. All local API access uses a per-install session token.
document.addEventListener('DOMContentLoaded',()=>Office.onReady(info=>{
 if(info.host!==Office.HostType.Word){document.getElementById('document').textContent='Open this add-in from Microsoft Word.';return}
 let token=new URLSearchParams(location.hash.slice(1)).get('token')||'';
 try{if(token)sessionStorage.setItem('cv:word-session',token);else token=sessionStorage.getItem('cv:word-session')||''}catch{}
 const replaceState=window.cvReplaceState||history.replaceState;
 if(typeof replaceState==='function'){try{replaceState.call(history,null,'',location.pathname+(location.search||''))}catch{}}
 const methods=['word_action','word_sources','ai_models','ai_status','ai_connections','ai_chat'];
 const normalize=value=>(/^(file|https?):/i.test(value)?decodeURIComponent(value):value).replace(/^file:\/+/i,'').replaceAll('\\','/').toLowerCase();
 const hostUrl=()=>typeof Office.context.document.getFilePropertiesAsync==='function'?new Promise((resolve,reject)=>Office.context.document.getFilePropertiesAsync(r=>r.status==='succeeded'?resolve(r.value.url||''):reject(Error(r.error?.message||'Could not read the current Word document.')))):Promise.resolve(Office.context.document.url||'');
 const api={};methods.forEach(method=>api[method]=async(...args)=>{
  let host='';
  if(method==='word_action'){
   host=await hostUrl();if(!host)throw Error('Save this Word document once, then refresh the connection.');
   const payload=JSON.parse(args[1]||'{}');payload.host_document=host;args[1]=JSON.stringify(payload);
  }
  const response=await fetch('/api',{method:'POST',headers:{'Content-Type':'application/json',Authorization:'Bearer '+token},body:JSON.stringify({method,args})});
  const data=await response.json();if(!response.ok)throw Error(data.error||'The local citation service is unavailable.');
  const result=data.result;
  if(method==='word_action'&&args[0]==='state'&&result.ok&&normalize(host)!==normalize(result.document))throw Error('Word connected to a different document. Activate this document and refresh the connection.');
  return result;
 });
 window.pywebview={api};window.dispatchEvent(new Event('pywebviewready'));
}));
