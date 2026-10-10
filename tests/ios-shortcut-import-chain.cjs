const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const ctx={URL,window:{}};vm.runInNewContext(fs.readFileSync('js/ios-shortcut-import-chain.js','utf8'),ctx);
const options={on:'https://vpn.tolf.is/a/ON.shortcut',off:'https://vpn.tolf.is/a/OFF.shortcut',
 success:'https://vpn.tolf.is/a/?result=complete',cancel:'https://vpn.tolf.is/a/?result=cancelled',error:'https://vpn.tolf.is/a/?result=error'};
const on=new URL(ctx.window.tolfShortcutImportChain.build(options)),off=new URL(on.searchParams.get('x-success'));
for(const [u,mode]of [[on,'ON'],[off,'OFF']]){
 assert.equal(u.protocol,'shortcuts:');assert.equal(u.hostname,'x-callback-url');assert.equal(u.pathname,'/import-shortcut');
 assert.equal(u.searchParams.get('url'),options[mode.toLowerCase()]);
 assert.equal(u.searchParams.get('name'),'TOLF '+mode);
 assert.equal(u.searchParams.get('x-cancel'),options.cancel);
 assert.equal(u.searchParams.get('x-error'),options.error);
 assert(!u.searchParams.has('silent'));
}
assert.equal(off.searchParams.get('x-success'),options.success);
assert.throws(()=>ctx.window.tolfShortcutImportChain.build({...options,on:'http://example.org/on'}));
console.log('PASS import chain: ON → OFF → success; cancel/error stop chain; no silent import or VPN execution');
