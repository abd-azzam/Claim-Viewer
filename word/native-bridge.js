// Native Word host keeps the local session credential outside the web page.
const cvPending=new Map();let cvRequest=0;
chrome.webview.addEventListener('message',event=>{const reply=event.data,p=cvPending.get(reply.id);if(!p)return;cvPending.delete(reply.id);clearTimeout(p.timer);reply.error?p.reject(Error(reply.error)):p.resolve(reply.result)});
window.pywebview={api:Object.fromEntries(['word_sources','word_action'].map(method=>[method,(...args)=>new Promise((resolve,reject)=>{const id=++cvRequest,timer=setTimeout(()=>{cvPending.delete(id);reject(Error('The citation service took too long. Try Refresh.'))},35000);cvPending.set(id,{resolve,reject,timer});chrome.webview.postMessage({id,method,args})})]))};
