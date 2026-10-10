const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync('quick/quick-1.js','utf8'),strings=fs.readFileSync('quick/strings-1.js','utf8');
async function run(ua,platform,node,{tamper=false,missingNode=false,loseReply=false,buttons=false}={}){
 const map=new Map(),store=new Map(),posts=[],created=[],user='test-account',device='test-device';
 let lost=loseReply;
 const makeElement=()=>({children:[],events:{},hidden:false,value:'',dataset:{},textContent:'',disabled:false,
   classList:{add(){},remove(){}},setAttribute(){},removeAttribute(){},
   append(...nodes){this.children.push(...nodes);},replaceChildren(...nodes){this.children=nodes;},
   addEventListener(name,fn){this.events[name]=fn;},remove(){},click(){return this.events.click?.();}});
 const element=id=>{if(!map.has(id))map.set(id,makeElement());return map.get(id);};
 let assigned;
 const descendants=node=>node.children.flatMap(n=>[n,...descendants(n)]);
 const host=node==='riga'?'oc-riga.tolf.is:443':'oc.tolf.is:4443';
 const cert='https://api.tolf.is/oc/access/import/TEST.p12';
 const grant={deviceId:device,password:'TEST-ONLY-PASSWORD',expiresAt:new Date(Date.now()+7200000).toISOString(),certificateUrl:tamper?'https://example.invalid/test.p12':cert,username:'test-certificate-user',importUri:'anyconnect://import/?type=pkcs12&uri='+encodeURIComponent(cert),connections:[{id:node,host,connectionUri:'anyconnect://create/?host='+encodeURIComponent(host)+'&certcommonname=test-certificate-user'}]};
 const ctx={URL,URLSearchParams,AbortSignal,location:{href:'https://vpn.tolf.is/quick/?protocol=anyconnect'},navigator:{userAgent:ua,platform:ua==='desktop-ipad'?'MacIntel':'',maxTouchPoints:ua==='desktop-ipad'?5:0,language:'ru',clipboard:{writeText:async()=>{}}},crypto:{randomUUID:()=> 'test-request-id'},localStorage:{getItem:()=>null,setItem(){}},sessionStorage:{getItem:k=>store.get(k),setItem:(k,v)=>store.set(k,v),removeItem:k=>store.delete(k)},document:{getElementById:element,documentElement:{lang:'ru'},querySelectorAll:()=>[],querySelector:()=>element('defaults'),body:{append(){}},createElement:()=>makeElement()},window:{addEventListener(){},location:{assign(url){assigned=url;}}},setTimeout:()=>0,clearTimeout(){},
 fetch:async(url,opt={})=>{
 let data;
 if(url.endsWith('/quick-setup/capabilities'))data={version:1};
 else if(url.endsWith('/entry-point-recommendation'))data={entryPoint:node};
 else if(url.endsWith('/oc/access/capabilities'))data={issuance:true,ingresses:missingNode?[]:[{id:node,host}]};
 else if(url.endsWith('/me'))data={authenticated:true,userId:user};
 else if(url.endsWith('/oc/access/devices')&&opt.method==='POST'){
 const body=JSON.parse(opt.body);created.push(body);
 assert.equal(opt.credentials,'include');
 if(lost){lost=false;throw Error('Lost reply');}
 data={device:{id:device,state:'active',label:'Test device',username:'test-certificate-user'}};
 }else if(url.endsWith('/oc/access/devices'))data={devices:[{id:device,state:'active',label:'Test device',username:'test-certificate-user',expires_at:new Date(Date.now()+86400000).toISOString()}]};
 else if(url.endsWith('/import')){assert.equal(opt.credentials,'include');data=grant;}
 else throw Error('Unexpected API '+url);
 posts.push(url);return {ok:true,json:async()=>data};
 }};
 vm.createContext(ctx);vm.runInContext(strings,ctx);vm.runInContext(fs.readFileSync('js/ios-vpn-buttons.js','utf8'),ctx);vm.runInContext(source,ctx);
 for(let i=0;i<40;i++)await Promise.resolve();
 if(missingNode){assert.equal(element('prepare').disabled,true);assert.equal(created.length,0);return;}
 if(platform==='ios'){
  const option=descendants(element('iosVpnButtons')).find(n=>n.type==='checkbox');
  assert.equal(option.checked,false);
  if(buttons){option.checked=true;option.events.change();}
 }
 await element('prepare').onclick();
 if(loseReply){await element('prepare').onclick();assert.equal(created[0].requestId,created[1].requestId);}
 if(platform==='ios'){
  const url=new URL(assigned);
  assert.equal(url.pathname,'/oc/access/devices/'+device+'/ios.mobileconfig');
  assert.equal(url.searchParams.get('ingress'),node);
  assert.equal(url.searchParams.get('buttons'),buttons?'true':null);
  assert.equal(posts.filter(p=>p.endsWith('/import')).length,0);
  assert(descendants(element('iosVpnButtons')).some(n=>n.textContent.includes('TOLF '+(node==='moscow'?'Москва':'Рига')+' Test device')));
  return;
 }
 assert.equal(element('ocRenew').disabled,true);
 assert.equal(element('ocAlreadyImported').disabled,true);
 await element('ocRenew').onclick();
 assert.equal(posts.filter(p=>p.endsWith('/import')).length,0);
 assert.equal(element('ocPassword').value,'');
 element('ocConfirmConnection').onclick();
 assert.equal(element('ocRenew').disabled,false);
 assert.equal(element('ocConnectionCompleted').hidden,false);
 await element('ocRenew').onclick();
 if(tamper){assert.equal(element('ocGrantPanel').hidden,true);assert.equal(element('ocPassword').value,'');return;}
 assert.equal(element('ocDelivery').hidden,false);assert.equal(element('ocServer').textContent,(node==='riga'?'Рига':'Москва')+': '+host);
 assert.equal(element('ocPassword').value,'TEST-ONLY-PASSWORD');
 assert.equal(element('ocConnection').hidden,platform==='windows');assert.equal(element('ocImport').hidden,platform==='windows');
 assert.equal(element('change').hidden,true);assert.equal(element('choices').hidden,true);
 assert.equal(posts.some(p=>p.endsWith('/quick-setup/prepare')),false);
 const before=created.length;await element('ocRenew').onclick();assert.equal(created.length,before);
 element('ocAlreadyImported').onclick();assert.equal(element('ocPassword').value,'');assert.equal(element('ocGrantPanel').hidden,true);assert.equal(element('ocCertificateDone').hidden,false);
 element('ocAgain').onclick();assert.equal(element('ocRenew').disabled,true);assert.equal(element('ocAlreadyImported').disabled,true);assert.equal(element('ocConnectionCompleted').hidden,true);
 element('ocAlreadyImported').onclick();assert.equal(element('ocCertificateDone').hidden,true);
 element('ocConfirmConnection').onclick();element('ocAlreadyImported').onclick();
 assert.equal(element('ocCertificateDone').hidden,false);
 await element('ocRenew').onclick();assert.equal(created.length,before);assert.equal(element('ocGrantPanel').hidden,false);
}
(async()=>{for(const [ua,p]of[['iPhone','ios'],['desktop-ipad','ios'],['Android','android'],['Windows NT','windows']])for(const node of ['riga','moscow'])await run(ua,p,node);await run('iPhone','ios','riga',{buttons:true});await run('iPhone','ios','moscow',{missingNode:true});await run('Android','android','moscow',{loseReply:true});console.log('PASS: AnyConnect device/node selection, reusable device, lost reply, certificate URL validation, node availability, mobile/Windows steps, blocked import, confirmation, reset and certificate reuse');})().catch(e=>{console.error(e);process.exit(1)});
