// Complete a verified citation's sentence using only its own PDF page.
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
 const boundary=/[.!?]["'”’)\]0-9⁰¹²³⁴⁵⁶⁷⁸⁹]*$/;
 // Stop at the nearest sentence boundary, including closing quotes and footnote markers.
 for(let i=first-1;i>=lo;i--)if(boundary.test(words[i][0])){lo=i+1;break}
 for(let i=last;i<=hi;i++)if(boundary.test(words[i][0])){hi=i;break}
 return text.slice(words[lo].index,words[hi].index+words[hi][0].length).trim();
}
// Keep separated quotations separate; only add text verified on the cited page.
function citationPassages(page,answer,anchor){
 const passages=[citationContext(page,anchor)||anchor];
 for(const m of String(answer||'').matchAll(/["“]([^"”\n]+)["”]/g)){
  const passage=citationContext(page,m[1]);if(passage)passages.push(passage);
 }
 return [...new Set(passages.filter(Boolean))];
}
