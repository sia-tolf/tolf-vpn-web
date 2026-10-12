const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
class E {
 constructor(){this.events={};this.children=[];this.dataset={};this.value='';this.validity={};this.queries=new Map();const s=new Set();this.classList={add:x=>s.add(x),remove:x=>s.delete(x),contains:x=>s.has(x),toggle:(x,v)=>v?s.add(x):s.delete(x)};}
 addEventListener(n,f){this.events[n]=f;} setAttribute(){} removeAttribute(){}
 append(...x){this.children.push(...x);} prepend(...x){this.children.unshift(...x);} replaceChildren(...x){this.children=x;}
 focus(){} setCustomValidity(){} reportValidity(){} querySelector(q){if(!this.queries.has(q))this.queries.set(q,new E());return this.queries.get(q);} querySelectorAll(){return [];}
}
async function scenario(enabled) {
 const elements=new Map(),el=id=>{if(!elements.has(id))elements.set(id,new E());return elements.get(id);};
 const posts=[], modes={riga:['sr','ru'],moscow:['','sr','ru','lv'],...(enabled?{us:['auto','ru','lv','yt']}:{})};
 const c={console,setTimeout,clearTimeout,URL,crypto:require('node:crypto').webcrypto,
 document:{getElementById:el,createElement:()=>new E(),querySelectorAll:()=>[],addEventListener(){}},
 navigator:{userAgent:'iPad',language:'ru'},window:{confirm:()=>true,location:{href:'https://vpn.tolf.is/?lang=ru'}},
 localStorage:{getItem(){return 'ru'},setItem(){}},
 t:key=>vm.runInContext('I18N.ru',c)[key]||key,setVpnBusy:v=>vm.runInContext('vpnBusy='+Boolean(v),c),
 apiRequest:async(path,opt)=>{if(path.endsWith('capabilities'))return {version:'1.0',servers:Object.keys(modes),routingModes:modes,certificatePackages:true};
 if(opt.method==='GET')return {devices:[]};
 posts.push([path,JSON.parse(opt.body)]);return {device:{id:'fixture',state:'active'},profileUrl:'https://api.tolf.is/windows/p/fixture'};}};
 vm.createContext(c);
 for(const file of ['js/config.js','js/locales/ru.js'])vm.runInContext(fs.readFileSync(file,'utf8'),c);
 vm.runInContext('lastVpnState={configured:true}',c);
 vm.runInContext(fs.readFileSync('js/windows.js','utf8'),c);
 await new Promise(r=>setImmediate(r));
 const us=el('windowsDeviceServer').querySelector('option[value="us"]');
 assert.equal(us.disabled,!enabled);
 assert.match(us.textContent,/Нью-Йорк/);assert.doesNotMatch(us.textContent,/США/);
 assert.equal(vm.runInContext("windowsServers.has('us')",c),enabled);
 assert.equal(vm.runInContext("'us' in SERVERS",c),false,'must not expose unsupported mobile IKEv2');
 if(!enabled)return;
 el('windowsAddButton').events.click();el('windowsDeviceServer').value='us';el('windowsDeviceServer').events.change();
 assert.deepEqual(el('windowsDeviceMode').children.map(x=>x.value),['auto','ru','lv','yt']);
 assert.match(el('windowsDeviceMode').children[0].textContent,/Нью-Йорк/);
 assert.match(el('windowsDeviceMode').children[3].textContent,/YouTube/);
 el('windowsDeviceName').value='Fixture PC';el('windowsDeviceMode').value='auto';
 el('windowsCreateForm').events.submit({preventDefault(){}});
 await new Promise(r=>setImmediate(r));
 assert.equal(posts.length,1);assert.equal(posts[0][0],'/windows/devices');
 assert.equal(posts[0][1].server,'us');assert.equal(posts[0][1].localId,'auto');assert.equal(posts[0][1].packageFormat,'ppkg');
 vm.runInContext("windowsDevices=[{id:'fixture',name:'Fixture PC',server:'us',localId:'auto',state:'active',authentication:'certificate'}];windowsProfileLinks.clear();renderWindowsDevices()",c);
 const texts=[];function walk(e){if(e.textContent)texts.push(e.textContent);for(const x of e.children||[])walk(x);}walk(el('windowsDeviceList'));
 assert.ok(texts.some(x=>x.startsWith('Нью-Йорк ·')),'device must not be labeled Riga');
 assert.ok(texts.some(x=>x.includes('остальные через Нью-Йорк')));
}
(async()=>{await scenario(false);await scenario(true);console.log('PASS: New York capability gate, four routes, PPKG request, device labels and mobile isolation');})().catch(e=>{console.error(e);process.exit(1);});
