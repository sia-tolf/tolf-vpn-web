const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
class Element {
  constructor(tag='div'){this.tagName=tag;this.children=[];this.attributes={};this.events={};this.style={};this.value='';}
  append(...nodes){this.children.push(...nodes);} replaceChildren(...nodes){this.children=nodes;}
  setAttribute(k,v){this.attributes[k]=v;} addEventListener(k,v){this.events[k]=v;}
  click(){if(!this.disabled)this.events.click?.();this.clicked=true;} remove(){this.removed=true;}
  get textContent(){return (this.text||'')+this.children.map(n=>n.textContent).join('');}set textContent(v){this.text=v;this.children=[];}
}
const all=n=>[n,...n.children.flatMap(all)];
const settle=async()=>{for(let i=0;i<10;i++)await new Promise(r=>setImmediate(r));};
async function scenario(unavailable=false){
  const root=new Element(),language=new Element('select'),body=new Element('body');
  const token='A'.repeat(43),calls=[],intervals=[],handlers={},revoked=[];
  const info={label:'Guest iPad',connectionUri:'anyconnect://create/?host=oc.tolf.is%3A4443',expiresAt:new Date(Date.now()+86400000).toISOString(),connections:[{id:'moscow',host:'oc.tolf.is:4443',connectionUri:'anyconnect://create/?host=oc.tolf.is%3A4443'},{id:'riga',host:'oc-riga.tolf.is:443',connectionUri:'anyconnect://create/?host=oc-riga.tolf.is%3A443'}]};
  const grant={password:'Aa123456',certificateUrl:'https://api.tolf.is/oc/access/import/token.p12',importUri:'anyconnect://import/?type=pkcs12',expiresAt:new Date(Date.now()+600000).toISOString()};
  const document={documentElement:{lang:'ru'},body,getElementById:id=>id==='setupLanguage'?language:root,createElement:tag=>new Element(tag)};
  const window={location:{hash:'#'+token},addEventListener:(k,fn)=>handlers[k]=fn};
  const navigator={userAgent:'iPad',language:'ru',clipboard:{writeText:async value=>{navigator.copied=value;}}};
  const context=vm.createContext({window,document,navigator,console,Date,Promise,Blob,AbortController,
    setTimeout,clearTimeout,setInterval:fn=>intervals.push(fn),
    URL:{createObjectURL:()=> 'blob:guest',revokeObjectURL:url=>revoked.push(url)},
    fetch:async(url,options)=>{calls.push([url,options]);
      if(url===grant.certificateUrl)return {ok:true,arrayBuffer:async()=>new Uint8Array([1,2]).buffer};
      if(unavailable)return {ok:false,status:410};
      return {ok:true,json:async()=>url.endsWith('/claim')?grant:info};
    }});
  vm.runInContext(fs.readFileSync(path.join(__dirname,'../js/anyconnect-setup.js'),'utf8'),context);await settle();
  const button=text=>{const result=all(root).find(n=>n.tagName==='button'&&n.textContent===text);assert(result,text);return result;};
  if(unavailable){assert(root.textContent.includes('Ссылка истекла'));assert.equal(calls.length,1);return;}
  assert(root.textContent.includes('Guest iPad'));assert(root.textContent.includes('Вход в аккаунт не требуется'));
  assert.equal(calls.length,1,'opening a link only reads metadata');
  const connection=all(root).find(n=>n.tagName==='a'&&n.textContent==='Добавить в AnyConnect');assert.equal(connection.href,info.connectionUri);
  assert(button('Получить сертификат').disabled);
  assert(button('Сертификат уже импортирован').disabled);
  connection.click();button('Получить сертификат').click();await settle();
  assert.equal(calls.length,1,'opening the app does not unlock certificate issuance');
  button('Соединение добавлено').click();
  assert(!all(root).some(n=>n.textContent==='Соединение добавлено'));
  assert(!all(root).some(n=>n.tagName==='a'&&n.textContent==='Добавить в AnyConnect'));
  assert(root.textContent.includes('✓ Соединение добавлено'));
  button('Добавить заново').click();assert(button('Получить сертификат').disabled);
  button('Соединение добавлено').click();
  assert(!button('Получить сертификат').disabled);
  button('Сертификат уже импортирован').click();await settle();
  assert(root.textContent.includes('✓ Сертификат уже импортирован'));
  assert.equal(calls.length,1,'existing certificate does not consume the setup link');
  const ingress=()=>all(root).find(n=>n.id==='ocIngress');
  ingress().value='riga';ingress().events.change();
  assert(button('Получить сертификат').disabled);
  assert.equal(all(root).find(n=>n.tagName==='a'&&n.textContent==='Добавить в AnyConnect').href,info.connections[1].connectionUri);
  button('Соединение добавлено').click();
  assert(root.textContent.includes('✓ Сертификат уже импортирован'));
  assert.equal(calls.length,1,'adding the second connection does not issue another certificate');
  assert(!all(root).some(n=>n.attributes['aria-label']==='Скопировать пароль'));
  button('Получить сертификат').click();await settle();
  assert(calls[1][0].endsWith('/'+token+'/claim'));assert.equal(calls[1][1].method,'POST');
  assert(root.textContent.includes(grant.password));
  all(root).find(n=>n.attributes['aria-label']==='Скопировать пароль').click();await settle();assert.equal(navigator.copied,grant.password);
  assert(root.textContent.includes('Пароль скопирован'));
  button('Скачать сертификат .p12').click();await settle();
  assert.equal(body.children.at(-1).download,'TOLF-AnyConnect.p12');assert.equal(body.children.at(-1).href,'blob:guest');
  button('Скачать сертификат .p12').click();await settle();assert.equal(calls.filter(c=>c[0]===grant.certificateUrl).length,1);
  assert(calls.every(c=>c[1].credentials==='omit'));assert(!calls.some(c=>/\/me|\/policy|\/devices/.test(c[0])));
  grant.expiresAt=new Date(Date.now()-1).toISOString();intervals[0]();assert(!root.textContent.includes(grant.password));assert(root.textContent.includes('Время импорта истекло'));assert.deepEqual(revoked,['blob:guest']);
  handlers.pagehide();
}
(async()=>{await scenario();await scenario(true);console.log('PASS guest setup: anonymous metadata, explicit claim, certificate links, copy, cached download, expiry and invalid link');})().catch(error=>{console.error(error);process.exitCode=1;});
