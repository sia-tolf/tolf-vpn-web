const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
class E{
 constructor(){this.events={};this.children=[];this.dataset={};this.value='';this.validity={};const s=new Set();this.classList={add:x=>s.add(x),remove:x=>s.delete(x),contains:x=>s.has(x),toggle:(x,v)=>v?s.add(x):s.delete(x)};}
 addEventListener(n,f){this.events[n]=f;} setAttribute(){} removeAttribute(){}
 append(...x){this.children.push(...x);} replaceChildren(...x){this.children=x;}
 focus(){} setCustomValidity(){} reportValidity(){} querySelector(){return new E();} querySelectorAll(){return [];}
 after(){} before(){}
}
async function manual(){
 const elements=new Map(),el=id=>{if(!elements.has(id))elements.set(id,new E());return elements.get(id);};
 const posts=[];
 const c={document:{getElementById:el,createElement:()=>new E(),querySelectorAll:()=>[],addEventListener(){}},
 navigator:{userAgent:'Mozilla iPad',platform:'MacIntel',maxTouchPoints:5},window:{confirm:()=>true},
 currentLanguage:'ru',currentPlatform:'windows',lastVpnState:{configured:true},vpnBusy:false,
 crypto:require('node:crypto').webcrypto,LOCAL_ID_OPTIONS:{riga:{sr:'Split'},moscow:{}},
 t:k=>k,setVpnBusy:v=>c.vpnBusy=v,setTimeout,clearTimeout,
 apiRequest:async(path,opt)=>{if(path.endsWith('capabilities'))return {version:'1.0',servers:['riga'],routingModes:{riga:['sr']}};
 if(opt.method==='GET')return {devices:[]};posts.push([path,JSON.parse(opt.body)]);
 return {device:{id:'device',state:'active'},profileUrl:'https://api.tolf.is/windows/p/test'};}};
 vm.createContext(c);vm.runInContext(fs.readFileSync('js/windows.js','utf8'),c);
 await new Promise(r=>setImmediate(r));
 el('windowsAddButton').events.click();assert.equal(el('windowsCreateForm').classList.contains('hidden'),false);
 el('windowsDeviceName').value='Office PC';el('windowsCreateForm').events.submit({preventDefault(){}});
 await new Promise(r=>setImmediate(r));
 assert.equal(posts.length,1);assert.equal(posts[0][0],'/windows/devices');assert.equal(posts[0][1].name,'Office PC');
}
async function quick(hash=''){
 const elements=new Map(),el=id=>{if(!elements.has(id))elements.set(id,new E());return elements.get(id);};
 const created=[];const windowEvents={};
 const link=el('quickSetupLink');link.href='https://vpn.tolf.is/quick/?protocol=ikev2';link.parentElement=new E();
 let protocol='ikev2';
 const c={document:{getElementById:el,createElement:()=>{const e=new E();created.push(e);return e;},documentElement:{lang:'ru'},body:{classList:{add(){}}}},
 currentPlatform:'windows',navigator:{userAgent:'iPad',platform:'MacIntel',maxTouchPoints:5},
 window:{addEventListener:(n,f)=>{windowEvents[n]=f;},getVpnTransport:()=>protocol},location:{href:'https://vpn.tolf.is/',hash},
 MutationObserver:class{observe(){}},URL,fetch:async()=>({ok:true,json:async()=>({version:1})})};
 vm.createContext(c);vm.runInContext(fs.readFileSync('js/quick-entry.js','utf8'),c);
 let prevented=false;link.events.click({preventDefault(){prevented=true;}});
 assert.equal(prevented,true,'Windows IKEv2 quick setup must stay on iPad and show instructions');
 const notice=created.find(e=>e.id==='quickWindowsNotice');
 assert.equal(notice.classList.contains('hidden'),false,'Quick instructions are visible');
 el('manualSetupLink').events.click();
 assert.equal(notice.classList.contains('hidden'),true,'Manual setup hides quick instructions');
 link.events.click({preventDefault(){}});
 assert.equal(notice.classList.contains('hidden'),false,'Quick instructions can be reopened');
 c.location.hash='#vpnCard';windowEvents.hashchange();
 assert.equal(notice.classList.contains('hidden'),true,'Manual hash navigation hides quick instructions');
 protocol='anyconnect';prevented=false;link.events.click({preventDefault(){prevented=true;}});
 assert.equal(prevented,false,'AnyConnect retains its own scenario');
}
(async()=>{await manual();await quick();await quick('#vpnCard');console.log('PASS: iPad manual device creation and Windows quick guidance are separate');})().catch(e=>{console.error(e);process.exit(1);});
