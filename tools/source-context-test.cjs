const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const ctx=vm.createContext({});
vm.runInContext(fs.readFileSync('C:/Apps/ClaimViewer/lib/source-context.js','utf8'),ctx);
const context=(page,quote)=>ctx.citationContext(page,quote),results=[];
function test(name,fn){try{fn();results.push({name,ok:true})}catch(e){results.push({name,ok:false,error:e.message})}}
test('Completes the cited sentence without adding neighboring sentences',()=>{
 const page='The introductory context sets out the question. This policy changes the incentives facing firms. The author then explains the mechanism and its limits.';
 const anchor='This policy changes the incentives facing firms';const out=context(page,anchor);
 assert.equal(out,anchor+'.');
});
test('Voltaire quote excludes the transition and subsequent commentary',()=>{
 const intro='The transition from faction to party was indeed slow and tortuous – both in the domain of ideas and in fact.';
 const sentence='The second half of the eighteenth century had just begun when Voltaire concisely stated in the Encyclopédie: “The term party is not, in itself, loathsome; the term faction always is.”¹';
 const after='With his versatile genius for synthesis Voltaire epitomised in this sentence a debate opened by Bolingbroke in 1732 and after that pursued for about a century.² The name faction was loathsome was not, from Roman times until the nineteenth century, a statement in want of proof.';
 const anchor='The term party is not, in itself, loathsome; the term faction always is';
 assert.equal(context(intro+' '+sentence+' '+after,anchor),sentence);
});
test('A fragment retains its own sentence and a multi-sentence citation stays complete',()=>{
 const page='Background ends here. Policy changes incentives for firms. This explains the mechanism. Unrelated commentary follows.';
 assert.equal(context(page,'changes incentives for firms'),'Policy changes incentives for firms.');
 assert.equal(context(page,'Policy changes incentives for firms. This explains the mechanism.'),'Policy changes incentives for firms. This explains the mechanism.');
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
