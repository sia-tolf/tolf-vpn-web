const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path'),crypto=require('node:crypto').webcrypto;
const root=path.resolve(__dirname,'../..');
class Element{
 constructor(tag='div',text=''){this.tagName=tag;this.textContent=text;this.children=[];this.handlers={};this.dataset={};this.style={};this.attributes={};this.value='';this.hidden=false;this.classList={add(){},remove(){},toggle(){}};}
 append(...values){this.children.push(...values);}appendChild(v){this.children.push(v);}prepend(...values){this.children.unshift(...values);}replaceChildren(...values){this.children=[...values];}
 addEventListener(k,v){this.handlers[k]=v;}setAttribute(k,v){this.attributes[k]=v;}scrollIntoView(){}focus(){}
 querySelectorAll(selector){return walk(this).filter(x=>selector.split(',').includes(x.tagName));}
 click(){return this.handlers.click?.({preventDefault(){}});}
}
function walk(root){return root.children.flatMap(x=>x instanceof Element?[x,...walk(x)]:[]);}
const flush=()=>new Promise(setImmediate);
function baseDocument(html){const elements={};for(const[,id]of html.matchAll(/id="([^"]+)"/g))elements[id]=new Element();return {elements,document:{documentElement:{lang:'ru'},hidden:false,getElementById:id=>elements[id]||null,createElement:tag=>new Element(tag),querySelectorAll:()=>[],addEventListener(){}}};}
async function adminScenario({networkLoss=false}={}){
 const {elements,document}=baseDocument(fs.readFileSync(path.join(root,'admin/index.html'),'utf8'));elements.accountKindFilter.value='all';
 const calls=[],target='22222222-2222-4222-8222-222222222222',content=elements.detailContent;let deleted=false,finished=false;
 const user={id:target,number:2,deletion:{allowed:true},trialRegistration:{registeredAt:'2026-10-26T00:00:00+00:00',hasPaidTraffic:true}};
 const context={document,location:new URL('https://vpn.tolf.is/admin/?tab=users'),navigator:{language:'ru'},localStorage:{getItem:()=> 'ru'},URL,URLSearchParams,AbortController,crypto,setTimeout,clearTimeout,addEventListener(){},fetch:async(url,options={})=>{
  calls.push({url,options});
  if(url.endsWith('/delete')){assert.equal(JSON.parse(options.body).number,2);assert.equal(JSON.parse(options.body).confirm,'DELETE');if(networkLoss)throw Error('lost response');deleted=true;return {ok:true,json:async()=>({deleted:true,vpnRevocationPending:false})};}
  if(url.includes('/account-deletions/')){if(finished){deleted=true;return {ok:true,json:async()=>({deleted:true})};}return {ok:true,json:async()=>({deleted:false,status:'running'})};}
  return {ok:true,json:async()=>({users:[],total:0})};
 }};context.window=context;
 let source=fs.readFileSync(path.join(root,'admin/admin-1.3.js'),'utf8');
 source=source.replace("language();$('gateMessage').textContent=t('loading');start();","allowed=true;detailEpoch=1;window.fixture={accountActions,load};");
 vm.runInNewContext(source,context);context.fixture.accountActions(user,content,1);
 assert(walk(content).some(x=>x.textContent.includes('Пробный · есть оплата')));
 const input=walk(content).find(x=>x.tagName==='input'),button=walk(content).find(x=>x.className==='admin-delete-button');
 assert.equal(button.disabled,true);input.value='99';input.handlers.input();assert.equal(button.disabled,true);
 input.value='2';input.handlers.input();assert.equal(button.disabled,false);await button.click();await flush();
 assert.equal(calls.filter(x=>x.url.endsWith('/delete')).length,1);
 assert(calls.some(x=>x.url.includes('/users/'+target+'/delete')));
 if(networkLoss){assert.equal(deleted,false);assert.match(button.textContent,/Проверить/);await button.click();assert.equal(calls.filter(x=>x.url.endsWith('/delete')).length,1);finished=true;await button.click();}
 assert.equal(deleted,true);assert.equal(elements.status.textContent,'Аккаунт удалён.');
 // No destructive control for protected users.
 content.replaceChildren();context.fixture.accountActions({...user,deletion:{allowed:false,reason:'protected'}},content,1);assert(!walk(content).some(x=>x.className==='admin-delete-button'));
 elements.accountKindFilter.value='only';await context.fixture.load();assert(calls.some(x=>x.url.includes('trial=only')));
}
(async()=>{await adminScenario();await adminScenario({networkLoss:true});require('node:child_process').execFileSync(process.execPath,[path.join(root,'tests/trials/frontend.cjs')],{stdio:'inherit'});console.log('Account UI: typed-number deletion, target isolation, protected users, lost-response checks, trial filtering and explicit trial registration passed.');})().catch(error=>{console.error(error);process.exitCode=1;});

