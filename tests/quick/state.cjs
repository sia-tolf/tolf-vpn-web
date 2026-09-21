// Run the actual controller with a small DOM fixture; layout is checked in browser.cjs.
const vm=require('vm'),fs=require('fs'),assert=require('assert/strict');
const path=require('path'),root=path.resolve(__dirname,'../..');
async function scenario(country,device='ios',credentialError=''){
 const ids=[...fs.readFileSync(path.join(root,'quick/index.html'),'utf8').matchAll(/id="([^"]+)"/g)].map(m=>m[1]);
 const elements=Object.fromEntries(ids.map(id=>[id,{hidden:false,disabled:false,value:'',textContent:'',dataset:{},setAttribute(){},focus(){},select(){}}]));
 const storage=new Map(),langs=['en','ru','lv'].map(lang=>({dataset:{lang},setAttribute(){}}));
 let auth=false,record=null,requests=0,registeredName='';
 const context={URL,AbortSignal,console,sessionStorage:{getItem:k=>storage.get(k),setItem:(k,v)=>storage.set(k,v),removeItem:k=>storage.delete(k)},localStorage:{getItem:()=>null,setItem(){}},
 navigator:{userAgent:device==='windows'?'Windows NT':'iPhone',language:'ru',credentials:{create:async()=>{if(credentialError)throw Object.assign(new Error('credential failed'),{name:credentialError});return{id:'fake'};}}},
 document:{getElementById:id=>elements[id],documentElement:{lang:'ru'},querySelectorAll:s=>s==='[data-lang]'?langs:[]},window:{location:{assign:url=>{elements.destination={value:url};}},PublicKeyCredential:function(){},addEventListener(){}},
 prepareRegistrationOptions:x=>x,serializeCredential:x=>x,
 fetch:async(url,options={})=>{
  const p=new URL(url).pathname;let data={},ok=true,status=200;
  if(p.endsWith('/capabilities'))data={version:1};
  else if(p==='/entry-point-recommendation')data={entryPoint:country};
  else if(p==='/me'){data={authenticated:auth};if(!auth){ok=false;status=401;}}
  else if(p.endsWith('/status'))data={setup:record};
  else if(p==='/passkey/register/begin'){registeredName=JSON.parse(options.body).passkeyName;data={options:{},challengeId:'test'};}
  else if(p.endsWith('/finish')){auth=true;data={recoveryCode:'RECOVERY'};}
  else if(p.endsWith('/prepare')){requests++;const body=JSON.parse(options.body);record={platform:body.platform,server:body.server,state:'ready'};data={profileUrl:'https://config.tolf.is/p/test'};}
  else throw new Error(p);
  return{ok,status,json:async()=>data};
 }};
 vm.createContext(context);vm.runInContext(fs.readFileSync(path.join(root,'quick/strings-1.js'),'utf8'),context);vm.runInContext(fs.readFileSync(path.join(root,'quick/windows-1.js'),'utf8'),context);vm.runInContext(fs.readFileSync(path.join(root,'quick/quick-1.js'),'utf8'),context);
 for(let i=0;i<20;i++)await new Promise(setImmediate);
 assert.equal(elements.server.value,country==='moscow'?'moscow':'riga');
 assert.equal(elements.register.disabled,false);
 assert.equal(elements.windowsPrep.hidden,true);
 assert.equal(elements.passkeyNameField.hidden,true);
 assert.equal(elements.register.textContent,'Создать аккаунт');
 await elements.register.onclick();
 assert.equal(elements.destination.value,'/auth/?mode=signup&next=quick&lang=ru');
 assert.equal(storage.get('quickServer'),country==='moscow'?'moscow':'riga');
 assert.equal(storage.get('quickPlatform'),device);
 assert.equal(requests,0);
 await elements.login.onclick();
 assert.equal(elements.destination.value,'/auth/?mode=signin&next=quick&lang=ru');

 return true;
}
(async()=>{await scenario('moscow');await scenario('riga');await scenario(null);await scenario('riga','windows','NotAllowedError');console.log('PASS controller: Russia, non-Russia, unknown country, shared auth navigation and preserved setup selection');})().catch(e=>{console.error(e);process.exit(1)});

