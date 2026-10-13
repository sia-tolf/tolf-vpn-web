const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const nodes=new Map();
class E{
 constructor(){this.children=[];this.events={};this.dataset={};this.disabled=false;this.value='';this.textContent='';const c=new Set();this.classList={add:x=>c.add(x),remove:x=>c.delete(x),contains:x=>c.has(x),toggle:(x,on)=>on?c.add(x):c.delete(x)};}
 set id(v){this._id=v;nodes.set(v,this);}get id(){return this._id;}
 append(...xs){this.children.push(...xs);}replaceChildren(...xs){this.children=xs;}insertAdjacentElement(_,x){this.children.push(x);}
 setAttribute(){}addEventListener(n,f){(this.events[n]??=[]).push(f);}dispatchEvent(e){for(const f of this.events[e.type]||[])f(e);}
 click(){this.dispatchEvent({type:'click',stopPropagation(){}});}contains(){return false;}
}
const el=id=>{if(!nodes.has(id)){const e=new E();e.id=id;}return nodes.get(id);};
let transport='ikev2',ingress='moscow';
const win=el('windowsDeviceServer');win.options=['riga','moscow','us'].map(value=>({value,disabled:false}));win.value='riga';
const radio=new E();radio.value='riga';
const wevents={};
const ctx={console,currentPlatform:'ios',document:{documentElement:{lang:'ru'},getElementById:el,createElement:()=>new E(),querySelector:q=>q.includes(':checked')?radio:null,querySelectorAll:()=>[],addEventListener(){}},
 window:{getVpnTransport:()=>transport,ocAccess:{ingress:()=>({id:ingress}),ingresses:()=>['riga','moscow','us'].map(id=>({id})),selectIngress:id=>{ingress=id;}},addEventListener:(n,f)=>{wevents[n]=f;}},
 setTimeout:f=>f(),setInterval(){},MutationObserver:class{observe(){}},Event:class{constructor(type){this.type=type;}}};
vm.createContext(ctx);vm.runInContext(fs.readFileSync('js/vpn-compact-selectors.js','utf8'),ctx);
const options=()=>el('vpnEntryDropdown').children[1].children;
const option=id=>options().find(x=>x.dataset.value===id);
assert.deepEqual(options().map(x=>x.dataset.value),['riga','moscow','us']);
assert.equal(option('us').disabled,true,'mobile IKEv2 must not issue an unsupported profile');
assert(option('us').children.some(x=>x.textContent.includes('AnyConnect')));
ctx.window.tolfMobileIkev2Ready=true;wevents.vpncapabilitieschange();
assert.equal(option('us').disabled,false,'mobile New York must follow enabled API capability');
ctx.window.tolfMobileIkev2Ready=false;wevents.vpncapabilitieschange();
assert.equal(option('us').disabled,true,'mobile capability rollback must disable New York');
ctx.currentPlatform='windows';wevents.vpnplatformchange();
assert.equal(option('us').disabled,false);
option('us').click();assert.equal(win.value,'us','top entry selector must update Windows location');
win.options[2].disabled=true;win.value='riga';wevents.vpnplatformchange();
assert.equal(option('us').disabled,true,'Windows availability gate must be respected');
transport='anyconnect';wevents.vpntransportchange();
assert.equal(option('us').disabled,false);
option('us').click();assert.equal(ingress,'us');
assert.equal(el('quickSetupLink').href,'/quick/?protocol=anyconnect&ingress=us');
console.log('PASS: visible New York, mobile restriction, Windows selection/gate, AnyConnect selection and quick handoff');
