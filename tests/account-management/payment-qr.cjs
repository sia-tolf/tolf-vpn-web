'use strict';
// UI contract only: /admin/me is stubbed; server authorization has its own tests.
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const root=path.resolve(__dirname,'../..'),source=fs.readFileSync(path.join(root,'admin/admin-1.3.js'),'utf8');
const flush=()=>new Promise(setImmediate);
function fixture(me={isAdmin:true,features:{paymentQr:true}}){
 const elements={},events={},windowEvents={},languages=['en','ru','lv'].map(lang=>({dataset:{lang},setAttribute(){},addEventListener(_,fn){this.click=fn;}}));
 function element(){return {children:[],handlers:{},dataset:{},value:'',hidden:false,style:{},setAttribute(){},append(...v){this.children.push(...v);},replaceChildren(...v){this.children=v;},addEventListener(k,fn){this.handlers[k]=fn;},before(v){elements[v.id]=v;},remove(){delete elements[this.id];}};}
 for(const [,id] of fs.readFileSync(path.join(root,'admin/index.html'),'utf8').matchAll(/id="([^"]+)"/g))elements[id]=element();
 const document={documentElement:{},hidden:false,getElementById:id=>elements[id]||null,createElement:element,querySelectorAll:s=>s==='[data-lang]'?languages:[],addEventListener:(k,fn)=>events[k]=fn};
 let response=me,pending=null;const calls=[];
 const context={document,location:new URL('https://vpn.tolf.is/admin/?tab=users'),navigator:{language:'ru'},localStorage:{getItem:()=> 'ru',setItem(){}},URL,URLSearchParams,AbortController,setTimeout,clearTimeout,addEventListener:(k,fn)=>windowEvents[k]=fn,fetch:async(url,options)=>{
  calls.push({url,options});let body=url.endsWith('/me')?response:{users:[],total:0};
  if(url.endsWith('/me')&&pending){const wait=pending;pending=null;body=await wait;}
  if(body instanceof Error)throw body;
  return {ok:!body.status,status:body.status,json:async()=>body};
 }};context.window=context;vm.runInNewContext(source,context);
 return {elements,document,events,windowEvents,languages,calls,setMe:v=>response=v,hold(){let resolve;pending=new Promise(r=>resolve=r);return resolve;},refresh:()=>elements.refresh.handlers.click(),link:()=>elements.privatePaymentQrLink};
}
(async()=>{
 for(const features of [undefined,{}, {paymentQr:false},{paymentQr:'true'},{paymentQr:1}]){
  const f=fixture({isAdmin:true,features});await flush();assert.equal(f.link(),undefined,'Only boolean true enables QR');
 }
 for(const me of [{isAdmin:false,features:{paymentQr:true}},{status:401},{status:403},new Error('offline')]){
  const f=fixture(me);await flush();assert.equal(f.link(),undefined);assert.equal(f.elements.workspace.hidden,true);
 }
 const f=fixture();await flush();
 const check=(label,lang)=>{assert.equal(f.link()?.textContent,label);assert.equal(f.link()?.href,'https://api.tolf.is/admin/payment-qr/?lang='+lang);};
 check('QR для перевода','ru');
 for(const [lang,label] of [['en','Transfer QR'],['lv','Pārskaitījuma QR'],['ru','QR для перевода']]){
  const done=f.hold();f.languages.find(x=>x.dataset.lang===lang).click();
  assert.equal(f.link(),undefined,'Hide the old link while language change revalidates access');
  done({isAdmin:true,features:{paymentQr:true}});await flush();check(label,lang);
 }
 // Session expiry, role/feature revocation and failures clear a previously visible link.
 for(const denied of [{status:401},{status:403},{isAdmin:false,features:{paymentQr:true}},{isAdmin:true,features:{}},new Error('offline')]){
  f.setMe(denied);f.refresh();await flush();assert.equal(f.link(),undefined);
  f.setMe({isAdmin:true,features:{paymentQr:true}});f.refresh();await flush();check('QR для перевода','ru');
 }
 // Sign-out in another tab and bfcache restoration must revalidate before exposing a link.
 f.document.hidden=true;f.events.visibilitychange();assert.equal(f.link(),undefined);
 f.setMe({status:401});f.document.hidden=false;f.events.visibilitychange();await flush();assert.equal(f.link(),undefined);
 f.setMe({isAdmin:true,features:{paymentQr:true}});f.refresh();await flush();check('QR для перевода','ru');
 let done=f.hold();f.windowEvents.pageshow({persisted:true});assert.equal(f.link(),undefined);done({status:401});await flush();assert.equal(f.link(),undefined);
 // An obsolete successful response cannot restore access after a newer denied response.
 done=f.hold();f.refresh();f.setMe({status:403});f.refresh();await flush();done({isAdmin:true,features:{paymentQr:true}});await flush();assert.equal(f.link(),undefined);
 assert(f.calls.every(c=>c.options.credentials==='include'&&c.options.cache==='no-store'));
 console.log('Payment QR UI: strict feature gate, roles, languages, expiry, re-login, visibility, bfcache and response races passed.');
})().catch(e=>{console.error(e);process.exitCode=1;});
