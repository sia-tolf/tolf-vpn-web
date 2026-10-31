const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
class Element {
 constructor(){this.attributes={};this.listeners={};this.dataset={};this.hidden=false;this.children=[];const classes=new Set();this.classList={contains:x=>classes.has(x),add:x=>classes.add(x),remove:x=>classes.delete(x),toggle:(x,on)=>{if(on)classes.add(x);else classes.delete(x);}};}
 setAttribute(k,v){this.attributes[k]=String(v);}
 removeAttribute(k){delete this.attributes[k];if(k==='href')this.href='';}
 addEventListener(k,fn){(this.listeners[k]||=[]).push(fn);}
 click(){let prevented=false;for(const f of this.listeners.click||[])f({preventDefault(){prevented=true;}});return prevented;}
 append(...children){this.children.push(...children);}
 replaceChildren(...children){this.children=children;}
 before(node){this.movedBefore=node;}
 focus(){this.focused=true;}
}
const ids={};const get=id=>ids[id]||=new Element();
for(const id of ['quickSetupCard','vpnCard','quickModePanel','quickSetupLink','manualSetupLink','quickStartLink','quickWindowsNotice','vpnSetupModes','quickSetupHelp','vpnPageTools','invitationCard'])get(id);
get('quickSetupCard').classList.add('hidden');
const observers=[],events={},body=new Element();let protocol='';
const context={URL,Date,encodeURIComponent,document:{body,documentElement:{lang:'ru'},getElementById:get,createElement:()=>new Element(),querySelector:()=>get('protocolButton')},
 currentPlatform:'ios',navigator:{userAgent:'iPhone',platform:'iPhone',maxTouchPoints:5},location:{href:'https://vpn.tolf.is/',hash:'',pathname:'/',search:''},history:{state:null,replaceState(){}},
 Event:class{constructor(type){this.type=type;}},MutationObserver:class{constructor(fn){observers.push(fn);}observe(){}},
 window:{getVpnTransport:()=>protocol,addEventListener:(k,f)=>(events[k]||=[]).push(f),dispatchEvent:e=>{for(const f of events[e.type]||[])f(e);}},
 sessionStorage:{removeItem(){},setItem(){}},fetch:async()=>({ok:true,json:async()=>({version:1})})};
context.window.clearVpnTransportChoice=()=>{protocol='';context.window.dispatchEvent(new context.Event('vpntransportchange'));};
for(const [id,value] of [['vpnTransportIkev2','ikev2'],['vpnTransportAnyConnect','anyconnect']])get(id).addEventListener('click',()=>{protocol=value;context.window.dispatchEvent(new context.Event('vpntransportchange'));});
vm.createContext(context);vm.runInContext(fs.readFileSync('js/quick-entry.js','utf8'),context);
(async()=>{
 await new Promise(setImmediate);
 assert(!get('quickSetupCard').classList.contains('hidden'));
 assert.equal(context.window.tolfSetupMode.get(),null);assert(get('quickModePanel').hidden);
 assert.equal(get('vpnPageTools').movedBefore,get('vpnCard'));
 for(const platform of ['ios','android','windows']){
  context.currentPlatform=platform;protocol='';
  for(let i=0;i<3;i++){
   assert(!get('manualSetupLink').click());assert(body.classList.contains('manual-setup-open'));
   assert.equal(get('quickSetupLink').attributes['aria-disabled'],'false');
   assert(!get('quickSetupLink').click());assert(!body.classList.contains('manual-setup-open'));
   assert(!get('quickModePanel').hidden);assert.equal(get('quickSetupLink').attributes['aria-selected'],'true');
  }
  assert(get('quickStartLink').click(),'Only launch requires a protocol');
  protocol='anyconnect';context.window.dispatchEvent(new context.Event('vpntransportchange'));
  const blocked=get('quickStartLink').click();
  assert.equal(blocked,platform!=='ios','Only launch checks the physical target device');
  get('manualSetupLink').click();assert.equal(context.window.tolfSetupMode.get(),'manual');
 }
 context.currentPlatform='windows';context.navigator.userAgent='Windows NT 10.0';context.navigator.platform='Win32';context.navigator.maxTouchPoints=0;
 get('quickSetupLink').click();assert(!get('quickStartLink').click());
 assert.equal(new URL(get('quickStartLink').href).searchParams.get('platform'),'windows');
 context.vpnInvitation={token:'pending'};observers.forEach(fn=>fn());assert(get('quickSetupCard').classList.contains('hidden'));
 context.vpnInvitation=null;observers.forEach(fn=>fn());assert(!get('quickSetupCard').classList.contains('hidden'));
 console.log('PASS: mode selection never launches or requires a protocol; launch retains native-device checks and invitation priority');
})().catch(error=>{console.error(error);process.exit(1);});
