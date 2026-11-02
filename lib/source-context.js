// Expand a verified citation anchor using only the text of its own PDF page.
function citationContext(page,quote){
 const text=String(page||''),key=String(quote||'').toLowerCase().replace(/[^a-z0-9]/g,'');
 if(key.length<12)return '';
 let normalized='';const offsets=[];
 for(let i=0;i<text.length;i++){const ch=text[i].toLowerCase();if(/^[a-z0-9]$/.test(ch)){normalized+=ch;offsets.push(i)}}
 const hit=normalized.indexOf(key);if(hit<0)return '';
 const start=offsets[hit],end=offsets[hit+key.length-1]+1,words=[...text.matchAll(/\S+/g)];
 const first=words.findIndex(w=>w.index+w[0].length>start),last=words.findIndex(w=>w.index+w[0].length>=end);
 if(first<0||last<0)return '';
 let lo=Math.max(0,first-65),hi=Math.min(words.length-1,last+65);
 // Keep complete nearby sentences when their boundaries are within the context window.
 for(let i=lo;i<first;i++)if(/[.!?]["'”’)]*$/.test(words[i][0])){lo=i+1;break}
 for(let i=hi;i>last;i--)if(/[.!?]["'”’)]*$/.test(words[i][0])){hi=i;break}
 return text.slice(words[lo].index,words[hi].index+words[hi][0].length).trim();
}
