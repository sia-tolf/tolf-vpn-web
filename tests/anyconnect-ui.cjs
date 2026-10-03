const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const assert = require('node:assert/strict');
const root = path.resolve(__dirname, '..');
class Element {
  constructor(tag = 'div') {
    this.tagName = tag; this.children = []; this.events = {}; this.attributes = {};
    this.dataset = {}; this.disabled = false; this.value = ''; this._text = '';
    this.style = {};
    const classes = new Set();
    this.classList = {toggle(name, on) { if (on) classes.add(name); else classes.delete(name); },
      contains: name => classes.has(name), remove: name => classes.delete(name), add: name => classes.add(name)};
  }
  set textContent(text) { this._text = text; this.children = []; }
  get textContent() { return this._text + this.children.map(c => c.textContent).join(''); }
  append(...items) { this.children.push(...items); }
  appendChild(item) { this.append(item); }
  replaceChildren(...items) { this._text = ''; this.children = items; }
  setAttribute(name, value) { this.attributes[name] = value; }
  removeAttribute(name) { delete this.attributes[name]; }
  addEventListener(name, fn) { this.events[name] = fn; }
  click() { assert.equal(this.disabled, false); this.clicked = true; return this.events.click?.(); }
  remove() { this.removed = true; }
  focus() {}
}
function descendants(node) { return node.children.flatMap(child => [child, ...descendants(child)]); }
function button(panel, name) {
  const node = descendants(panel).find(n => n.tagName === 'button' && n.textContent === name);
  assert(node, name); return node;
}
async function settle() { for (let i = 0; i < 10; i++) await new Promise(resolve => setImmediate(resolve)); }
(async () => {
  const ids = {};
  for (const name of ['vpnTransportSelector','vpnTransportIkev2','vpnTransportAnyConnect','vpnOverviewTitle',
    'vpnStatus','usernameRow','vpnUsername','anyConnectModeRow','anyConnectModeLabel','anyConnectModeHelp',
    'anyConnectModeStatus','anyConnectModeSelector','anyConnectAccess']) ids[name] = new Element();
  const modes = ['auto','ru','lv','yt'].map(mode => { const n = new Element('button'); n.dataset.mode = mode; return n; });
  ids.anyConnectModeAuto = modes[0];
  const document = {documentElement:{lang:'ru',dataset:{}}, hidden:false,
    body:new Element('body'),
    getElementById: id => ids[id], querySelectorAll: () => modes,
    createElement: tag => new Element(tag), addEventListener() {}};
  const handlers = {}, window = {tolfAccountState:{authenticated:true,userId:'owner',vpn:{username:'user0_ipad'}},
    addEventListener(name, fn) { (handlers[name] ||= []).push(fn); },
    dispatchEvent(event) { for (const fn of handlers[event.type] || []) fn(event); },
    confirm: () => true};
  const first = {id:'one',label:'iPad',username:'tolf-oc-'+'1'.repeat(32),state:'active',mode:'auto'};
  const second = {id:'two',label:'Phone',username:'tolf-oc-'+'2'.repeat(32),state:'active',mode:'lv'};
  const devices = [first,second], calls = [];
  const downloads = [], revokedUrls = [];
  let heldSession = null, connected = true, sessionError = false;
  async function request(url, options = {}) {
    const p = url.replace('https://api.tolf.is',''); calls.push([options.method || 'GET',p,options.credentials]);
    if (p.endsWith('/capabilities')) return {issuance:true,nodeReady:true,version:2};
    if (p === '/oc/access/devices') {
      if (options.method === 'POST') {
        const data=JSON.parse(options.body),device={id:'three',label:data.label,username:'tolf-oc-'+'3'.repeat(32),state:'active',mode:'auto'};
        devices.push(device);return {device};
      }
      return {devices};
    }
    const d = devices.find(d => p.includes('/'+d.id+'/'));
    if (p.endsWith('/session')) {
      if (sessionError) throw Error('Session unavailable');
      if (heldSession) await heldSession;
      return {username:d.username,mode:d.mode,connected};
    }
    if (p.endsWith('/policy')) {
      if (options.method === 'POST') d.mode = JSON.parse(options.body).mode;
      return {username:d.username,mode:d.mode,applied:true};
    }
    if (p.endsWith('/import')) return {deviceId:d.id,password:'private-import-password',
      expiresAt:new Date(Date.now()+600000).toISOString(),certificateUrl:'https://api.tolf.is/import/token.p12',
      importUri:'anyconnect://import/?type=pkcs12',connectionUri:'anyconnect://create/?host=oc.tolf.is'};
    throw Error('Unexpected endpoint: '+p);
  }
  const c = vm.createContext({window,document,API:'https://api.tolf.is',currentPlatform:'ios',
    console,crypto:require('node:crypto').webcrypto,Date,Promise,
    URLSearchParams,Event:class {constructor(type){this.type=type;}},
    MutationObserver:class {observe(){}},
    setInterval(){},setTimeout,clearTimeout,
    apiRequest:request,copyText:async value=>{c.copied=value;},Blob,AbortController,
    URL:{createObjectURL(blob){assert.equal(blob.type,'application/octet-stream');return 'blob:test-package';},
      revokeObjectURL(url){revokedUrls.push(url);}},
    fetch:async (url,options)=>{
      if(url==='https://api.tolf.is/import/token.p12'){
        downloads.push(url);return {ok:true,arrayBuffer:async()=>new Uint8Array([48,2,1,0]).buffer};
      }
      return {ok:true,json:async()=>request(url,options)};
    }});
  for (const file of ['transport-selector.js','anyconnect-access.js']) {
    vm.runInContext(fs.readFileSync(path.join(root,'js',file),'utf8'),c);
  }
  ids.vpnTransportAnyConnect.click(); await settle();
  assert(!descendants(ids.anyConnectAccess).some(n=>n.tagName==='ol'));
  assert(descendants(ids.anyConnectAccess).some(n=>n.tagName==='a'&&n.textContent==='Установить Cisco Secure Client'));
  assert(!ids.anyConnectAccess.textContent.includes('Перед импортом сертификата'));
  assert.equal(descendants(ids.anyConnectAccess).filter(n=>n.tagName==='input').length,0);
  const deviceRow = ids.anyConnectAccess.children.find(n=>n.className==='oc-device-row');
  assert(deviceRow.children.some(n=>n.tagName==='select'));
  assert(deviceRow.children.some(n=>n.tagName==='button'&&n.textContent==='Отозвать доступ'));
  assert(ids.anyConnectAccess.children.some(n=>n.className==='oc-access-header'&&
    n.children.some(child=>child.textContent==='Создать дополнительный доступ')));
  assert(!descendants(ids.anyConnectAccess).some(n=>n.tagName==='button'&&n.textContent==='Обновить'));
  button(ids.anyConnectAccess,'Создать дополнительный доступ').click();
  assert.equal(descendants(ids.anyConnectAccess).filter(n=>n.tagName==='input').length,1);
  button(ids.anyConnectAccess,'Отмена').click();
  assert.equal(descendants(ids.anyConnectAccess).filter(n=>n.tagName==='input').length,0);
  assert.equal(ids.vpnUsername.textContent,'user0_ipad');
  const statusBadge=()=>descendants(ids.anyConnectAccess).find(n=>n.className?.startsWith('oc-device-status'));
  assert.equal(statusBadge().textContent,'Подключено');
  assert(statusBadge().className.includes('oc-session-connected'));
  let finishPoll;heldSession=new Promise(resolve=>{finishPoll=resolve;});
  window.dispatchEvent(new c.Event('focus'));await settle();
  assert.equal(statusBadge().textContent,'Подключено','background polling retains the confirmed status');
  finishPoll();heldSession=null;await settle();
  connected=false;window.dispatchEvent(new c.Event('focus'));await settle();
  assert.equal(statusBadge().textContent,'Не подключено');
  sessionError=true;window.dispatchEvent(new c.Event('focus'));await settle();
  assert.equal(statusBadge().textContent,'Не удалось проверить');
  sessionError=false;connected=true;window.dispatchEvent(new c.Event('focus'));await settle();
  assert(ids.anyConnectModeSelector.classList.contains('policy-confirmed'));
  button(ids.anyConnectAccess,'Передать на другое устройство').click();
  assert(!descendants(ids.anyConnectAccess).some(n=>n.tagName==='button'&&n.textContent==='Получить сертификат'));
  assert(descendants(ids.anyConnectAccess).some(n=>n.tagName==='input'&&n.readOnly&&n.value==='https://vpn.tolf.is/?ocDevice=one'));
  button(ids.anyConnectAccess,'Скопировать ссылку').click();await settle();
  assert.equal(c.copied,'https://vpn.tolf.is/?ocDevice=one');
  assert(ids.anyConnectAccess.textContent.includes('Ссылка скопирована'));
  button(ids.anyConnectAccess,'Настроить на этом устройстве').click();
  button(ids.anyConnectAccess,'Получить сертификат').click(); await settle();
  assert(ids.anyConnectAccess.textContent.includes('private-import-password'));
  assert(!descendants(ids.anyConnectAccess).some(n=>n.tagName==='button'&&n.textContent==='Скопировать пароль'));
  const copyIcon = descendants(ids.anyConnectAccess).find(n=>n.tagName==='button'&&n.attributes['aria-label']==='Скопировать пароль');
  assert(copyIcon);copyIcon.click();await settle();
  assert.equal(c.copied,'private-import-password');
  const copyControl = descendants(ids.anyConnectAccess).find(n=>n.className==='oc-copy-control');
  assert(copyControl.children.some(n=>n.className==='oc-copy-feedback'&&n.textContent==='Пароль скопирован'));
  assert(!descendants(ids.anyConnectAccess).find(n=>n.className==='oc-message').textContent.includes('Пароль скопирован'));
  const certificateStep = descendants(ids.anyConnectAccess).find(n=>n.className==='oc-step'&&n.textContent.startsWith('4.'));
  const importPosition = certificateStep.children.findIndex(n=>n.className==='oc-actions oc-import-actions');
  assert(certificateStep.children[importPosition-1].textContent.includes('Перед импортом сертификата'));
  assert(certificateStep.children[importPosition+1].className==='oc-note');
  assert(certificateStep.children.at(-1).className==='oc-note');
  assert(!ids.anyConnectAccess.textContent.includes(first.username));
  const connectionStep = descendants(ids.anyConnectAccess).find(n=>n.className==='oc-step'&&n.textContent.startsWith('3.'));
  const steps = descendants(ids.anyConnectAccess).find(n=>n.className==='oc-steps');
  assert.equal(steps.children[0],connectionStep);
  assert.equal(steps.children[1],certificateStep);
  assert(connectionStep.children[0].textContent.includes('«iPad»'));
  assert(certificateStep.children[0].textContent.includes('«iPad»'));
  assert(connectionStep.textContent.includes('Сначала добавьте соединение'));
  assert(button(ids.anyConnectAccess,'Получить сертификат').className.includes('oc-prepare'));
  const connectionPosition = connectionStep.children.findIndex(n=>n.tagName==='a');
  assert(connectionStep.children[connectionPosition-1].textContent.includes('External Control → Prompt'));
  const importLink = descendants(ids.anyConnectAccess).find(n=>n.tagName==='a'&&n.textContent==='Импортировать в AnyConnect');
  assert(importLink.className.includes('button-link')&&importLink.className.includes('primary'));
  button(ids.anyConnectAccess,'Скачать сертификат .p12').click();await settle();
  const downloadAnchor=document.body.children.at(-1);
  assert.equal(downloadAnchor.href,'blob:test-package');
  assert.equal(downloadAnchor.download,'TOLF-AnyConnect.p12');
  assert(downloadAnchor.clicked&&downloadAnchor.removed);
  button(ids.anyConnectAccess,'Скачать сертификат .p12').click();await settle();
  assert.equal(downloads.length,1,'repeat save reuses the one-time download in page memory');
  const select = descendants(ids.anyConnectAccess).find(n=>n.tagName==='select');
  select.value = second.id; select.events.change(); await settle();
  assert(!ids.anyConnectAccess.textContent.includes('private-import-password'));
  assert(!descendants(ids.anyConnectAccess).some(n=>n.className==='oc-copy-feedback'));
  assert.deepEqual(revokedUrls,['blob:test-package']);
  assert.equal(ids.vpnUsername.textContent,'user0_ipad');
  assert(descendants(ids.anyConnectAccess).filter(n=>n.tagName==='h4').some(n=>n.textContent==='3. Добавьте соединение для «Phone»'));
  assert(descendants(ids.anyConnectAccess).filter(n=>n.tagName==='h4').some(n=>n.textContent==='4. Импортируйте сертификат для «Phone»'));
  modes[1].click(); await settle();
  assert.equal(first.mode,'auto'); assert.equal(second.mode,'ru');
  button(ids.anyConnectAccess,'Создать дополнительный доступ').click();
  const nameInput = descendants(ids.anyConnectAccess).find(n=>n.tagName==='input');
  nameInput.value='New device';nameInput.events.input();
  button(ids.anyConnectAccess,'Создать доступ').click();await settle();
  assert.equal(descendants(ids.anyConnectAccess).filter(n=>n.tagName==='input').length,0);
  assert.equal(ids.vpnUsername.textContent,'user0_ipad');
  assert(!ids.anyConnectAccess.textContent.includes('private-import-password'));
  assert(calls.every(call => !call[1].includes('/oc-test')));
  assert(calls.filter(call=>call[1].endsWith('/policy')||call[1].endsWith('/session')).every(call=>call[2]==='include'));
  window.setAnyConnectAccount({authenticated:true,userId:'owner'});
  assert.equal(ids.vpnUsername.textContent,'');
  assert(ids.usernameRow.classList.contains('hidden'));
  window.setAnyConnectAccount({authenticated:true,userId:'owner',vpn:{username:'user0_ipad'}});
  assert.equal(ids.vpnUsername.textContent,'user0_ipad');
  // A late session response must not restore the green indicator after logout.
  let release; heldSession = new Promise(resolve=>{release=resolve;});
  window.dispatchEvent(new c.Event('focus')); await settle();
  window.setAnyConnectAccount(null); release(); await settle();
  assert.equal(ids.anyConnectAccess.textContent,'');
  assert(!ids.anyConnectModeSelector.classList.contains('policy-confirmed'));
  assert(modes.every(n=>n.disabled));
  window.location={search:'?ocDevice=two'};
  window.tolfAccountState={authenticated:true,userId:'owner',vpn:{username:'user0_ipad'}};
  vm.runInContext(fs.readFileSync(path.join(root,'js','anyconnect-access.js'),'utf8'),c);await settle();
  assert.equal(window.ocAccess.selected().id,'two','receiving link selects its device');
  window.setAnyConnectAccount(null);
  devices.length=0;
  window.setAnyConnectAccount({authenticated:true,userId:'different-owner'});await settle();
  assert.equal(window.ocAccess.selected(),null);
  assert(ids.anyConnectAccess.textContent.includes('Этот доступ недоступен в текущем аккаунте'));
  assert(!descendants(ids.anyConnectAccess).some(n=>n.tagName==='button'&&n.textContent==='Получить сертификат'));
  console.log('PASS personal UI: device selection, import secret clearing, isolated routing, authenticated endpoints, stale session after logout');
})().catch(error=>{console.error(error);process.exitCode=1;});
