const cvProviderPresets={
 deepseek:['DeepSeek','https://api.deepseek.com','chat'],
 openai:['OpenAI','https://api.openai.com/v1','responses'],
 claude:['Claude (Anthropic)','https://api.anthropic.com/v1','anthropic'],
 opencode:['OpenCode','https://opencode.ai/inference/openai/v1','chat'],
 'opencode-go':['OpenCode Go','https://opencode.ai/inference/go/openai/v1','chat'],
 custom:['Custom / local','','chat']
};
async function providerSettings(){
 if(window.claimSettings)return claimSettings('ai');
 const opener=document.activeElement,d=document.createElement('dialog');d.className='provider-settings';d.setAttribute('aria-label','AI settings');
 document.body.append(d);d.showModal();d.onclose=()=>{d.remove();opener?.focus()};
 await mountProviderSettings(d);const close=document.createElement('button');close.textContent='Close';close.onclick=()=>d.close();d.append(close);
}
async function mountProviderSettings(d){
 d.innerHTML=`<h2>AI</h2><p>Connect a provider once, then choose any of its models in chat.</p><label>Saved providers<select id="ps-saved"><option value="">Add provider</option></select></label><form id="ps-form"><label>Provider<select id="ps-provider">${Object.entries(cvProviderPresets).map(([k,v])=>`<option value="${k}">${v[0]}</option>`).join('')}</select></label><label>API key<input id="ps-key" type="password" autocomplete="off" placeholder="Paste your API key"></label><small>Keys are encrypted for your Windows account. Leave blank to keep an existing key.</small><label>Default model<input id="ps-model" list="ps-models" required placeholder="Load models, or enter a model ID"></label><datalist id="ps-models"></datalist><button type="button" id="ps-refresh">Load available models</button><p id="ps-model-note"></p><details id="ps-advanced"><summary>Advanced</summary><label>Connection name<input id="ps-name" required></label><label>Base URL<input id="ps-base" type="url" required></label><label>API protocol<select id="ps-protocol"><option value="chat">Chat Completions</option><option value="responses">OpenAI Responses</option><option value="anthropic">Anthropic Messages</option></select></label></details><p id="ps-status" role="status" aria-live="polite"></p><div class="ps-actions"><button type="button" id="ps-delete" disabled>Remove provider</button><button type="submit" id="ps-save">Save provider</button></div></form>`;
 const q=id=>d.querySelector('#ps-'+id);let profiles=[],revision=0;
 function note(){const provider=q('provider').value;q('model-note').textContent=provider==='opencode'?'This connection uses the OpenCode pay-as-you-go catalog and credits.':provider==='opencode-go'?'This connection lists models from the Go catalog only. Models outside Go require a separate provider connection. Use a key from the workspace with the Go subscription.':'The model list is loaded from this provider. You can also enter a model ID.'}
 function preset(){revision++;const p=cvProviderPresets[q('provider').value];['name','base','protocol'].forEach((k,i)=>q(k).value=p[i]);q('model').value='';q('models').replaceChildren();q('key').value='';q('advanced').open=q('provider').value==='custom';note()}
 function payload(){const p={id:q('saved').value,key:q('key').value,all_models:true};['name','base','model','protocol','provider'].forEach(k=>p[k]=q(k).value);return p}
 async function call(action,p=''){if(!window.pywebview?.api?.ai_connections)throw Error('Open the updated Claim Viewer desktop app to manage providers.');const r=await window.pywebview.api.ai_connections(action,p);if(!r.ok)throw Error(r.error);return r}
 function fillList(selected=''){q('saved').replaceChildren(new Option('Add provider',''),...profiles.map(p=>new Option(p.name,p.id)));q('saved').value=selected}
 function load(){revision++;const p=profiles.find(p=>p.id===q('saved').value);q('delete').disabled=!p;q('models').replaceChildren();q('key').value='';if(p){q('provider').value=p.provider||'custom';['name','base','model','protocol'].forEach(k=>q(k).value=p[k]);q('status').textContent=p.has_key?'API key saved.':'No API key saved.';q('advanced').open=p.provider==='custom';note()}else{preset();q('status').textContent='Choose a provider and paste its API key.'}}
 q('provider').onchange=()=>{preset();q('status').textContent='Enter the key for this provider.'};q('saved').onchange=load;
 q('refresh').onclick=async()=>{const version=revision;q('refresh').disabled=true;q('status').textContent='Loading models…';try{const r=await call('models',JSON.stringify(payload()));if(version!==revision)return;q('models').replaceChildren(...r.models.map(id=>new Option(id,id)));if(!q('model').value)q('model').value=r.models[0]||'';q('status').textContent=r.models.length?`${r.models.length} models available. Choose a default or type a model ID.`:'No models returned. Enter a model ID.'}catch(e){if(version===revision)q('status').textContent=e.message+' You can enter a model ID manually.'}finally{q('refresh').disabled=false}};
 q('form').onsubmit=async e=>{e.preventDefault();q('save').disabled=true;try{const r=await call('save',JSON.stringify(payload()));profiles=r.connections;fillList(r.id);load();q('status').textContent='Provider saved. Its models are available in chat.';window.dispatchEvent(new Event('cv-models-changed'))}catch(e){q('status').textContent=e.message}finally{q('save').disabled=false}};
 q('delete').onclick=async()=>{q('delete').disabled=true;try{const r=await call('delete',q('saved').value);profiles=r.connections;fillList();load();window.dispatchEvent(new Event('cv-models-changed'))}catch(e){q('status').textContent=e.message;q('delete').disabled=false}};
 preset();try{const r=await call('list');profiles=r.connections;fillList(profiles[0]?.id);load()}catch(e){q('status').textContent=e.message}
}
