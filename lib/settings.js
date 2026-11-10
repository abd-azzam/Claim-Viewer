// One settings surface for every workspace mode, with the same bottom-left entry.
const cvSettingGet=(key,fallback)=>{try{return store.get('cv:'+key)??fallback}catch(e){return localStorage.getItem('cv:'+key)??fallback}};
function cvSettingSet(key,value){if(typeof store!=='undefined')store.set('cv:'+key,String(value));else localStorage.setItem('cv:'+key,String(value))}
function cvApplyAppearance(){
 const theme=cvSettingGet('theme','system'),dark=theme==='dark'||theme==='system'&&matchMedia('(prefers-color-scheme:dark)').matches;
 document.documentElement.dataset.theme=dark?'dark':'light';
 const fonts={default:'',sans:'"Segoe UI",sans-serif',serif:'Georgia,serif',mono:'Consolas,monospace'};
 document.body.style.fontFamily=fonts[cvSettingGet('font','default')]||'';
 const scale=Math.min(125,Math.max(80,Number(cvSettingGet('ui-scale','100'))||100))/100;
 document.documentElement.style.setProperty('--cv-ui-scale',scale);document.documentElement.style.zoom=scale;document.body.style.width=100/scale+'vw';document.body.style.height=100/scale+'vh';
 const palette=cvSettingGet(dark?'dark-palette':'light-palette',dark?'graphite':'default');
 const colors={graphite:[],carbon:['#111111','#1a1a1a'],midnight:['#101523','#182033'],void:['#17191b','#202426'],default:[],latte:['#eff1f5','#e6e9ef'],classic:['#ffffff','#f3f3f3'],parchment:['#faf8f1','#f0ede3']}[palette]||[];
 ['--bg','--panel'].forEach((k,i)=>colors[i]?document.documentElement.style.setProperty(k,colors[i]):document.documentElement.style.removeProperty(k));
 const accent=cvSettingGet(dark?'accent-dark':'accent-light','');
 if(/^#[a-f\d]{6}$/i.test(accent))document.documentElement.style.setProperty('--acc',accent);else document.documentElement.style.removeProperty('--acc');
 document.getElementById('th')?.setAttribute('aria-pressed',String(dark));
}
async function cvSettingsCall(action){
 if(!window.pywebview?.api?.app_settings)throw Error('Restart the updated Claim Viewer desktop app to use this action.');
 const r=await pywebview.api.app_settings(action);if(!r.ok)throw Error(r.error);return r;
}
let cvUpdateCheck,cvUpdateMessage='';
function cvCheckForUpdate(){
 if(!cvUpdateCheck)cvUpdateCheck=cvSettingsCall('check-update').then(result=>{
  cvUpdateMessage=result.message;
  if(result.version&&!document.getElementById('cv-update-notice')){
   const notice=document.createElement('button');notice.type='button';notice.id='cv-update-notice';
   notice.textContent='Claim Viewer '+result.version+' is ready to install';
   notice.onclick=()=>{notice.remove();claimSettings('updates')};
   document.body.append(notice);
  }
  return result;
 }).finally(()=>{cvUpdateCheck=null});
 return cvUpdateCheck;
}
window.addEventListener('pywebviewready',()=>{cvCheckForUpdate().catch(()=>{})},{once:true});
window.claimSettings=async function(page='general'){
 const existing=document.querySelector('.cv-settings');if(existing){existing.querySelector(`[data-settings-page="${page}"]`)?.click();return}
 const opener=document.activeElement,d=document.createElement('dialog');d.className='cv-settings';d.setAttribute('aria-labelledby','settings-heading');
 const groups=[['GENERAL',[['general','General'],['appearance','Appearance']]],['INTELLIGENCE',[['ai','AI']]],['INTEGRATIONS',[['references','Reference Managers'],['word','Word Add-in'],['sync','Backup']]],['APP',[['advanced','Advanced'],['tutorial','Tutorial'],['new',"What’s New"],['updates','Check for Updates'],['feedback','Feedback'],['about','About']]]];
 d.innerHTML=`<h1 id="settings-heading" class="sr-only">Settings</h1><nav aria-label="Settings sections">${groups.map(([label,items])=>`<small>${label}</small>${items.map(([id,title])=>`<button type="button" data-settings-page="${id}">${title}</button>`).join('')}`).join('')}</nav><button type="button" class="settings-close" aria-label="Close settings">×</button><div class="settings-content provider-settings" id="settings-content"></div>`;
 const content=d.querySelector('.settings-content');let current='';
const syncLang=()=>{const sl=document.getElementById('settings-lang');if(sl)sl.value=cvLang()};
 const row=(title,description,control)=>`<div class="setting-row"><div><strong>${title}</strong>${description?`<small>${description}</small>`:''}</div>${control}</div>`;
 const select=(id,options,key,value)=>`<select id="${id}" data-pref="${key}">${options.map(([v,l])=>`<option value="${v}"${String(v)===String(value)?' selected':''}>${l}</option>`).join('')}</select>`;
 const toggle=(key)=>`<input type="checkbox" role="switch" aria-label="${key==='reopen'?'Reopen tabs from last time':'Show '+key}" data-pref="${key}"${cvSettingGet(key,'true')==='true'?' checked':''}>`;
 const action=(id,label)=>`<button type="button" data-settings-action="${id}">${label}</button>`;
 const status='<p class="settings-status" role="status" aria-live="polite"></p>';
 async function render(id){
  current=id;d.querySelectorAll('[data-settings-page]').forEach(b=>{b.setAttribute('aria-current',b.dataset.settingsPage===id?'page':'false')});content.replaceChildren();
  if(id==='ai'){await mountProviderSettings(content);return}
  if(id==='general')content.innerHTML=`<h2>General</h2><div class="settings-card">${row('Language','Applies to the whole window.','<select id="settings-lang">'+['en','id'].map(v=>'<option value="'+v+'"'+(cvLang()===v?' selected':'')+'>'+(v==='id'?'Bahasa Indonesia':'English')+'</option>').join('')+'</select>')}${row('Startup','Reopen your reading tabs and last workspace.',toggle('reopen'))}${row('Library view','How readings appear in your library.',select('settings-library',[['cards','Cards'],['table','Table']],'library-view',cvSettingGet('library-view','table')))}</div><h3>Sidebar sections</h3><div class="settings-card">${row('Graph','Claim pathways and connected ideas.',toggle('show-graph'))}${row('Notes','Notes beside claims.',toggle('show-notes'))}</div><p>Settings stay at the bottom of the left pane in every workspace.</p>`;
  if(id==='appearance'){
   const dark=document.documentElement.dataset.theme==='dark';
   content.innerHTML=`<h2>Appearance</h2><h3>Theme</h3><div class="settings-card">${row('Colour scheme','System follows your device setting.',select('settings-theme',[['system','System'],['dark','Dark'],['light','Light']],'theme',cvSettingGet('theme','system')))}<h4>Dark theme</h4><div class="theme-grid">${[['graphite','Graphite','#1c2027'],['carbon','Carbon','#111111'],['midnight','Midnight','#101523'],['void','Void','#17191b']].map(([v,l,c])=>`<button type="button" data-palette="${v}" data-scheme="dark" aria-pressed="${cvSettingGet('dark-palette','graphite')===v}"><span style="background:${c}"><i></i></span>${l}</button>`).join('')}</div><h4>Light theme</h4><div class="theme-grid">${[['default','Default Light','#ffffff'],['latte','Catppuccin Latte','#eff1f5'],['classic','Classic Light','#ffffff'],['parchment','Parchment','#faf8f1']].map(([v,l,c])=>`<button type="button" data-palette="${v}" data-scheme="light" aria-pressed="${cvSettingGet('light-palette','default')===v}"><span style="background:${c}"><i></i></span>${l}</button>`).join('')}</div></div><h3>Accent & font</h3><div class="settings-card">${row('Accent colour','Used for links, buttons and focus.','<input id="settings-accent" type="color" aria-label="Accent colour" value="'+(cvSettingGet(dark?'accent-dark':'accent-light','')||(dark?'#7aa7ff':'#1f5fbf'))+'">')}${row('Font style','Choose the interface font.',select('settings-font',[['default','Default'],['sans','Sans'],['serif','Serif'],['mono','Mono']],'font',cvSettingGet('font','default')))}${row('Interface size','Scales text and controls together.',select('settings-scale',[['80','80%'],['90','90%'],['100','100%'],['110','110%'],['125','125%']],'ui-scale',cvSettingGet('ui-scale','100')))}</div>`;
  }
  if(id==='references')content.innerHTML=`<h2>Reference Managers</h2><div class="settings-card">${row('Zotero · Mendeley · EndNote','Export your Claim Viewer references in RIS format.',action('export-ris','Export references'))}${row('Add readings','Import PDFs through the Library. Metadata stays editable there.',action('library','Open library'))}</div><p>Automatic reference-manager sync is not available in Claim Viewer. RIS export transfers source metadata; PDFs and notes stay in this library.</p>${status}`;
  if(id==='word'){
   content.innerHTML=`<h2>Microsoft Word add-in</h2><p id="settings-word-state" role="status">Checking installation…</p><div class="settings-card">${row('Citations in Word','Browse library folders, insert citations and choose a bibliography style.','')}<div class="ps-actions">${action('word-install','Install Word add-in')}${action('word-uninstall','Uninstall')}</div></div><p>After installation, restart Word and choose <strong>Claim Viewer → Insert citation</strong> on the ribbon.</p><p>Requires Word for Windows. Windows approval installs the ribbon; your library stays on this computer.</p>${status}`;
   try{const r=await cvSettingsCall('word-status');if(current==='word')showWord(r)}catch(e){if(current==='word')content.querySelector('#settings-word-state').textContent=e.message}
  }
  if(id==='sync')content.innerHTML=`<h2>Backup</h2><div class="settings-card">${row('Local backup','Save your library, PDFs, claims, notes and reading positions. API keys are excluded.',action('backup','Create backup'))}${row('Library folder','Open the files used by this installation.',action('open-data','Open folder'))}</div><p>Claim Viewer currently stores your library on this computer. Automatic cloud sync is not connected. You can keep a backup archive in your preferred cloud drive.</p>${status}`;
  if(id==='advanced')content.innerHTML=`<h2>Advanced</h2><div class="settings-card">${row('Library data','View this installation’s saved files.',action('open-data','Open folder'))}${row('Export edits','Save claims and edits with the existing export tool.',action('export-edits','Export edits'))}${row('Import edits','Restore an edits file with the existing import tool.',action('import-edits','Import edits'))}${row('Display preferences','Restore theme, font and interface size.',action('reset-display','Restore defaults'))}</div>${status}`;
  if(id==='tutorial')content.innerHTML=`<h2>Tutorial</h2><p>Walk through the library, PDF tools, claims, notes, graph, Ask AI, Word citations and backups.</p>${action('start-tutorial','Start tutorial')}`;
  if(id==='new')content.innerHTML='<h2>What’s New</h2><div class="settings-card"><h3>Claim Viewer 2.6.2</h3><ul><li>Adding a claim to an existing note opens the note you pick, including the first or only choice.</li><li>OCR reports progress page by page and keeps scanned text selectable when you reopen the PDF.</li><li>Compact icons show or hide the panes. The left toggle sits beside the theme control.</li><li>AI Settings includes OpenAI and Claude (Anthropic) connections.</li><li>New releases download in the background, with an in-app notice when the installer is ready.</li><li>The Word pane puts source search first. Insert a bibliography once, then add citations to update it.</li><li>Settings includes a guided tour of Claim Viewer.</li></ul></div>';
  if(id==='updates'){
   content.innerHTML=`<h2>Check for Updates</h2><div class="settings-card"><p>Claim Viewer checks GitHub when it opens and downloads verified Windows installers for newer releases. Install the update when you’re ready.</p><div class="ps-actions">${action('check-update','Check now')}${action('open-updates','Open update folder')}</div></div>${status}`;
   content.querySelector('.settings-status').textContent=cvUpdateMessage;
  }
  if(id==='feedback')content.innerHTML=`<h2>Feedback</h2><p>Send a bug report, a request or a question to <a href="mailto:abdazzam@protonmail.com">abdazzam@protonmail.com</a>, or open an issue at <a href="https://github.com/abd-azzam/Claim-Viewer/issues">github.com/abd-azzam/Claim-Viewer</a>.</p><p>Copy a diagnostic summary to include when reporting an issue. It excludes API keys and document text.</p>${action('diagnostics','Copy diagnostics')}${status}`;
  if(id==='about'){
   content.innerHTML='<h2>About Claim Viewer</h2><div class="settings-card"><h3>Claim Viewer for Windows</h3><p id="settings-version">Checking installed version…</p><p>Created by Azzam Abdullah. Read and annotate PDFs, organise claims and notes, map connections and cite sources in Microsoft Word.</p><p>Your library lives on this computer. Ask AI sends the relevant text to the provider you select.</p><p><a href="https://github.com/abd-azzam/Claim-Viewer">Project on GitHub</a></p></div>';
   const version=content.querySelector('#settings-version');
   try{const r=await cvSettingsCall('version');version.textContent=r.version?'Version '+r.version:'Version unavailable'}catch(e){version.textContent='Version unavailable'}
  }
 }
 function showWord(r){content.querySelector('#settings-word-state').textContent=r.registered?(r.running?'Installed · local service ready':'Registered · local service not reachable'):'Not installed';content.querySelector('[data-settings-action="word-install"]').textContent=r.registered?'Repair installation':'Install Word add-in';content.querySelector('[data-settings-action="word-uninstall"]').disabled=!r.registered}
 d.addEventListener("change",e=>{if(e.target.id==="settings-lang"){cvSetLang(e.target.value);const t=d.querySelector("#settings-lang");if(t)t.value=cvLang()}});
d.onclick=async e=>{
  const page=e.target.closest('[data-settings-page]');if(page){render(page.dataset.settingsPage);return}
  if(e.target.closest('.settings-close')){d.close();return}
  const palette=e.target.closest('[data-palette]');if(palette){cvSettingSet(palette.dataset.scheme+'-palette',palette.dataset.palette);cvSettingSet('theme',palette.dataset.scheme);cvApplyAppearance();render('appearance');return}
  if(e.target.id==='settings-lang'){cvSetLang(e.target.value);return}
const button=e.target.closest('[data-settings-action]');if(!button)return;const action=button.dataset.settingsAction,s=content.querySelector('.settings-status');button.disabled=true;
  try{
   if(action==='start-tutorial'){d.close();setTimeout(()=>cvTourStart(0),0)}
   else if(action==='library'){d.close();show('lib')}
   else if(action==='export-edits'||action==='import-edits'){d.close();document.getElementById(action==='export-edits'?'ex':'im').click()}
   else if(action==='reset-display'){['theme','font','ui-scale','dark-palette','light-palette','accent-dark','accent-light'].forEach(k=>cvSettingSet(k,''));cvApplyAppearance();s.textContent='Display defaults restored.'}
   else if(action==='diagnostics'){const r=await cvSettingsCall('info');await navigator.clipboard.writeText(JSON.stringify({app:'Claim Viewer',sources:r.sources,theme:document.documentElement.dataset.theme,interfaceSize:cvSettingGet('ui-scale','100'),platform:navigator.platform},null,2));s.textContent='Diagnostic summary copied.'}
   else if(action==='check-update'){s.textContent='Checking for updates and downloading any newer installer…';const r=await cvCheckForUpdate();s.textContent=r.message}
   else{if(action==='backup'&&window.pywebview?.api?.state_flush)await pywebview.api.state_flush();s.textContent=action==='word-install'?'Installing the Word add-in…':'Working…';const r=await cvSettingsCall(action);if(current==='word')showWord(r);s.textContent=r.cancelled?'Cancelled.':r.message||'Complete.'}
  }catch(error){if(s)s.textContent=error.message}finally{button.disabled=false}
 };
 d.onchange=e=>{const el=e.target;if(el.dataset.pref){cvSettingSet(el.dataset.pref,el.type==='checkbox'?el.checked:el.value);cvApplyAppearance();cvApplySidebar();if(el.dataset.pref==='library-view'&&document.body.classList.contains('library'))drawLibTable()}if(el.id==='settings-accent'){cvSettingSet(document.documentElement.dataset.theme==='dark'?'accent-dark':'accent-light',el.value);cvApplyAppearance()}};
 d.onclose=()=>{d.remove();opener?.focus()};document.body.append(d);d.showModal();await render(page);d.querySelector(`[data-settings-page="${page}"]`)?.focus();
};
function cvApplySidebar(){['graph','notes'].forEach(k=>{const b=document.getElementById(k==='graph'?'tg':'vn');if(b)b.hidden=cvSettingGet('show-'+k,'true')==='false'})}
document.addEventListener('DOMContentLoaded',()=>{cvApplyAppearance();cvApplySidebar();document.getElementById('th')?.addEventListener('click',()=>cvApplyAppearance());document.getElementById('cv-settings-button')?.addEventListener('click',()=>claimSettings());if(cvSettingGet('reopen','true')==='true'){const mode=cvSettingGet('workspace','list');if(['lib','graph','notes'].includes(mode))show(mode)}});
matchMedia('(prefers-color-scheme:dark)').addEventListener('change',()=>{if(cvSettingGet('theme','system')==='system')cvApplyAppearance()});
