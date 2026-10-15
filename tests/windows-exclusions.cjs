const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const ctx={window:{},TextEncoder,URL,btoa:s=>Buffer.from(s,'binary').toString('base64')};vm.createContext(ctx);
vm.runInContext(fs.readFileSync('js/openconnect-windows-setup.js','utf8'),ctx);
const parse=ctx.window.TolfWindowsSetup.parseExclusions;
assert.equal(JSON.stringify(parse('192.168.200.118/24\n10.0.21.10,10.0.21.10/32')),'["192.168.200.0/24","10.0.21.10/32"]');
for(const bad of ['0.0.0.0/0','256.2.3.4','10.1.2.3/33','10.1.2.3;calc','::1',Array.from({length:33},(_,i)=>'10.0.0.'+i).join('\n')])assert.throws(()=>parse(bad));
assert.equal(parse('').length,0);
const wrapper=fs.readFileSync(require('node:os').tmpdir()+'/tolf-test-route-wrapper.js','utf8');
function run(reason,hookCode=0,defaultCode=0){
 const calls=[],env=name=>env[name]||'';env.reason=reason;
 const shell={Environment:()=>env,Run(cmd){calls.push([env.reason,cmd]);return cmd.startsWith('powershell.exe')?hookCode:defaultCode;}};
 let exit;const c={ActiveXObject:function(){return shell},WScript:{Echo(){},Quit(code){exit=code;throw Error('exit')}}};
 // WSH Environment supports indexed assignment; the test checks action sequencing.
 try{vm.runInNewContext(wrapper.replace(/environment\("reason"\) = ([^;]+);/g,'environment.reason = $1;'),c);}catch(e){if(e.message!=='exit')throw e}
 return {calls,exit};
}
let r=run('connect');assert.equal(r.exit,0);assert(r.calls[0][1].startsWith('powershell.exe'));assert(r.calls[1][1].startsWith('cscript.exe'));
r=run('connect',1);assert.equal(r.exit,1);assert.equal(r.calls.length,1);
r=run('disconnect');assert(r.calls[0][1].startsWith('cscript.exe'));assert(r.calls[1][1].startsWith('powershell.exe'));
r=run('connect',0,1);assert.equal(r.calls.length,3);assert.equal(r.calls[2][0],'disconnect');assert.equal(r.exit,1);
console.log('PASS: browser exclusions and generated Windows hook sequencing');
