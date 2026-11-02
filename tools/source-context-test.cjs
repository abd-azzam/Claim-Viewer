const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const ctx=vm.createContext({});
vm.runInContext(fs.readFileSync('C:/Apps/ClaimViewer/lib/source-context.js','utf8'),ctx);
const context=(page,quote)=>ctx.citationContext(page,quote),results=[];
function test(name,fn){try{fn();results.push({name,ok:true})}catch(e){results.push({name,ok:false,error:e.message})}}
test('Expands a verified anchor with exact surrounding text from its page',()=>{
 const page='The introductory context sets out the question. This policy changes the incentives facing firms. The author then explains the mechanism and its limits.';
 const anchor='This policy changes the incentives facing firms';const out=context(page,anchor);
 assert.ok(out.includes(anchor));assert.ok(out.length>anchor.length);assert.ok(page.includes(out));assert.ok(out.includes('mechanism and its limits'));
});
test('Preserves original punctuation, whitespace and capitalisation',()=>{
 const page='Prior sentence. The STATE—rather than firms—sets\n  the direction of investment. Following sentence.';
 const out=context(page,'the state rather than firms sets the direction of investment');
 assert.ok(out.includes('The STATE—rather than firms—sets\n  the direction of investment.'));assert.ok(page.includes(out));
});
test('Beginning-of-page anchor never reads beyond the supplied page',()=>{
 const page='A policy argument begins here. This is the only page supplied.';const out=context(page,'A policy argument begins here');assert.ok(out.startsWith('A policy argument begins here'));assert.ok(page.includes(out));
});
test('End-of-page anchor is retained completely',()=>{
 const page='Background from the same page. The final passage states the crucial boundary condition';const out=context(page,'The final passage states the crucial boundary condition');assert.ok(out.endsWith('The final passage states the crucial boundary condition'));assert.ok(page.includes(out));
});
test('Context has bounded nearby words and preserves long exact anchor',()=>{
 const before=Array.from({length:180},(_,i)=>'before'+i).join(' '),after=Array.from({length:180},(_,i)=>'after'+i).join(' ');
 const anchor='Verified source passage states the mechanism clearly';const page=before+' '+anchor+' '+after,out=context(page,anchor);
 assert.ok(out.includes(anchor));assert.ok(!out.includes('before0 '));assert.ok(!out.includes('after179'));assert.ok(out.split(/\s+/).length<=anchor.split(' ').length+130);assert.ok(page.includes(out));
});
test('Wrong anchor returns empty rather than fabricated or unrelated source text',()=>{
 const page='The actual page discusses manufacturing and industrial policy.';assert.equal(context(page,'An absent passage about electoral incentives'),'');assert.equal(context('',page),'');assert.equal(context(page,''),'');
});
test('Short ambiguous anchors do not become fabricated context',()=>{
 assert.equal(context('Short words repeat throughout this page.','short words'),'');assert.equal(context('Short words repeat throughout this page.','---'),'');
});
test('A quote on another page cannot be used to expand this page',()=>{
 const first='The first page discusses a theory of structural change.';const second='The second page identifies the historical turning point.';assert.equal(context(first,second),'');assert.ok(second.includes(context(second,second)));
});
test('Repeated exact anchor still returns an unchanged substring of supplied page',()=>{
 const anchor='The same policy mechanism appears';const page=anchor+' in the first example. Another context follows. '+anchor+' in the final example.';const out=context(page,anchor);assert.ok(out.includes(anchor));assert.ok(page.includes(out));
});
console.log(JSON.stringify({passed:results.filter(r=>r.ok).length,total:results.length,results},null,2));if(results.some(r=>!r.ok))process.exitCode=1;
