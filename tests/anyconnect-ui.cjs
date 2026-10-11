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
  scrollIntoView(options) { this.scrolled = options; }
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
    'anyConnectModeStatus','anyConnectModeSelector','anyConnectAccess','serverRiga','serverMoscow']) ids[name] = new Element();
  ids.serverRiga.value='riga';ids.serverRiga.checked=true;ids.serverMoscow.value='moscow';
  const modes = ['auto','ru','lv','yt'].map(mode => { const n = new Element('button'); n.dataset.mode = mode; return n; });
  ids.anyConnectModeAuto = modes[0];
  const document = {documentElement:{lang:'ru',dataset:{}}, hidden:false,
    body:new Element('body'),
    getElementById: id => ids[id], querySelectorAll: () => modes,
    createElement: tag => new Element(tag), addEventListener() {}};
  document.querySelector=()=>[ids.serverRiga,ids.serverMoscow].find(input=>input.checked);
  const handlers = {}, window = {tolfAccountState:{authenticated:true,userId:'owner',vpn:{username:'user0_ipad'}},
    addEventListener(name, fn) { (handlers[name] ||= []).push(fn); },
    dispatchEvent(event) { for (const fn of handlers[event.type] || []) fn(event); },
    confirm: () => true};
  const first = {id:'one',label:'iPad',username:'tolf-oc-'+'1'.repeat(32),state:'active',mode:'auto'};
  const second = {id:'two',label:'Phone',username:'tolf-oc-'+'2'.repeat(32),state:'active',mode:'lv'};
  const devices = [first,second], calls = [];
  const downloads = [], revokedUrls = [];
  let heldSession = null, connected = true, sessionError = false, sessionNodes = null, policyApplied = true;
  async function request(url, options = {}) {
    const p = url.replace('https://api.tolf.is',''); calls.push([options.method || 'GET',p,options.credentials]);
    if (p.endsWith('/capabilities')) return {issuance:true,nodeReady:true,version:2,guestSetup:true,ingresses:[{id:'moscow',host:'oc.tolf.is:4443'},{id:'riga',host:'oc-riga.tolf.is:443'}]};
    if (p === '/oc/access/devices') {
      if (options.method === 'POST') {
        const data=JSON.parse(options.body),device={id:'three',label:data.label,username:'tolf-oc-'+'3'.repeat(32),state:'active',mode:'auto'};
        devices.push(device);return {device};
      }
      return {devices};
    }
    const d = devices.find(d => p.includes('/'+d.id+'/'));
    if(p.endsWith('/setup-link'))return {deviceId:d.id,setupUrl:'https://vpn.tolf.is/anyconnect-setup.html#'+'A'.repeat(43),expiresAt:new Date(Date.now()+86400000).toISOString()};
    if (p.endsWith('/session')) {
      if (sessionError) throw Error('Session unavailable');
      if (heldSession) await heldSession;
      return {username:d.username,mode:d.mode,connected,nodes:sessionNodes};
    }
    if (p.endsWith('/policy')) {
      if (options.method === 'POST') d.mode = JSON.parse(options.body).mode;
      return {username:d.username,mode:d.mode,applied:policyApplied};
    }
    if (p.endsWith('/import')) return {deviceId:d.id,password:'private-import-password',
      expiresAt:new Date(Date.now()+600000).toISOString(),certificateUrl:'https://api.tolf.is/import/token.p12',
      importUri:'anyconnect://import/?type=pkcs12',connectionUri:'anyconnect://create/?host=oc.tolf.is'};
    throw Error('Unexpected endpoint: '+p);
  }
  const storage = new Map();
  const c = vm.createContext({sessionStorage:{getItem:k=>storage.get(k),setItem:(k,v)=>storage.set(k,v)},window,document,API:'https://api.tolf.is',currentPlatform:'ios',
    serverInputs:[ids.serverRiga,ids.serverMoscow],
    allowedServers:['riga','moscow'],
    console,crypto:require('node:crypto').webcrypto,Date,Promise,
    URLSearchParams,Event:class {constructor(type){this.type=type;}},
    MutationObserver:class {observe(){}},
    setInterval(){},setTimeout,clearTimeout,
    apiRequest:request,copyText:async value=>{c.copied=value;},Blob,AbortController,
    URL:class extends URL {static createObjectURL(blob){assert.equal(blob.type,'application/octet-stream');return 'blob:test-package';}
      static revokeObjectURL(url){revokedUrls.push(url);}},
    fetch:async (url,options)=>{
      if(url==='https://api.tolf.is/import/token.p12'){
        downloads.push(url);return {ok:true,arrayBuffer:async()=>new Uint8Array([48,2,1,0]).buffer};
      }
      return {ok:true,json:async()=>request(url,options)};
    }});
  const uiSource=fs.readFileSync(path.join(root,'js','ui.js'),'utf8');
  vm.runInContext(uiSource.slice(0,uiSource.indexOf('function updateSelectedServerAddress')),c);
  for (const file of ['ios-vpn-buttons.js','transport-selector.js','anyconnect-access.js']) {
    vm.runInContext(fs.readFileSync(path.join(root,'js',file),'utf8'),c);
  }
  ids.vpnTransportAnyConnect.click(); await settle();
  // iPhone now uses one authenticated MobileConfig with a linked certificate.
  const iosInstall=descendants(ids.anyConnectAccess).find(n=>n.tagName==='a'&&n.textContent==='Установить профиль AnyConnect');
  assert(iosInstall,'a single profile installation button is offered on iOS');
  assert(iosInstall.href.includes('/oc/access/devices/one/ios.mobileconfig?ingress=moscow'));
  const option = descendants(ids.anyConnectAccess).find(n=>n.tagName==='input'&&n.type==='checkbox');
  const details = descendants(ids.anyConnectAccess).find(n=>n.className==='ios-vpn-buttons-details');
  assert.equal(option.checked, false);
  assert.equal(details.hidden, true);
  assert(!new URL(iosInstall.href).searchParams.has('buttons'));
  option.checked = true; option.events.change();
  assert.equal(details.hidden, false);
  assert.equal(new URL(iosInstall.href).searchParams.get('buttons'), 'true');
  assert(details.textContent.includes('TOLF Москва iPad'));
  assert(iosInstall.hidden, 'ordinary installation hidden while bundle selected');
  assert.deepEqual(descendants(details).filter(n=>n.tagName==='a').map(n=>n.textContent), ['Добавить команду «TOLF Москва iPad»']);
  for (const mode of ['control']) {
    const shortcut=descendants(details).find(n=>n.tagName==='a'&&n.textContent==='Добавить команду «TOLF Москва iPad»');
    assert(shortcut);
    assert.equal(new URL(shortcut.href).pathname, '/oc/access/devices/one/shortcuts/'+mode.toLowerCase()+'.shortcut');
    shortcut.click();
    button(details,'Команда добавлена — продолжить').click();
  }
  assert(descendants(details).some(n=>n.tagName==='a'&&n.textContent==='Установить профиль'));
  option.checked = false; option.events.change();
  assert(!new URL(iosInstall.href).searchParams.has('buttons'));
  assert(!iosInstall.hidden);
  assert(!descendants(ids.anyConnectAccess).some(n=>n.tagName==='button'&&n.textContent==='Настроить на этом устройстве'));
  assert(!descendants(ids.anyConnectAccess).some(n=>n.tagName==='a'&&n.textContent==='Добавить в AnyConnect'));
  c.currentPlatform='android';
  window.dispatchEvent(new c.Event('vpnplatformchange'));await settle();
  // Legacy Android/manual flow remains available; further tests cover it.
  assert(descendants(ids.anyConnectAccess).includes(ids.anyConnectModeRow), 'routing is in the selected device section');
  assert(!descendants(ids.anyConnectAccess).some(n=>n.tagName==='ol'));
  assert(descendants(ids.anyConnectAccess).some(n=>n.tagName==='a'&&n.textContent==='Установить Cisco Secure Client'));
  assert(!ids.anyConnectAccess.textContent.includes('Перед импортом сертификата'));
  assert(!descendants(ids.anyConnectAccess).some(n=>n.tagName==='button'&&n.textContent==='Получить сертификат'));
  button(ids.anyConnectAccess,'Настроить на этом устройстве').click();
  assert(!ids.serverRiga.disabled,'Riga is enabled for activated AnyConnect access');
  ids.serverRiga.events.change();
  assert.equal(window.ocAccess.ingress().id,'riga');
  c.allowedServers=['moscow'];assert.equal(c.getSelectedServerKey(),'riga','AnyConnect ingress is independent of IKEv2 grants');c.allowedServers=['riga','moscow'];
  assert(ids.serverRiga.checked&&!ids.serverMoscow.checked);
  const connectionLink=()=>descendants(ids.anyConnectAccess).find(n=>n.tagName==='a'&&n.textContent==='Добавить в AnyConnect');
  assert.equal(new URLSearchParams(connectionLink().href.split('?')[1]).get('host'),'oc-riga.tolf.is:443');
  assert.equal(new URLSearchParams(connectionLink().href.split('?')[1]).get('certcommonname'),first.username);
  assert.equal(new URLSearchParams(connectionLink().href.split('?')[1]).get('name'),'TOLF Рига iPad');
  ids.serverMoscow.events.change();
  assert.equal(window.ocAccess.ingress().id,'moscow');
  assert.equal(new URLSearchParams(connectionLink().href.split('?')[1]).get('name'),'TOLF Москва iPad');
  assert(descendants(ids.anyConnectAccess).some(n=>n.tagName==='button'&&n.textContent==='Получить сертификат'));
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
  sessionNodes={moscow:{connected:false,available:true},riga:{connected:true,available:true}};
  window.dispatchEvent(new c.Event('focus'));await settle();
  assert.equal(statusBadge().textContent,'Подключено · Рига');
  sessionNodes=null;window.dispatchEvent(new c.Event('focus'));await settle();
  policyApplied=false;window.refreshAnyConnectTransport();await settle();
  assert(!ids.anyConnectModeSelector.classList.contains('policy-confirmed'),'pending multi-node policy cannot show the green dot');
  policyApplied=true;window.dispatchEvent(new c.Event('focus'));await settle();
  assert(ids.anyConnectModeSelector.classList.contains('policy-confirmed'),'a confirmed retry restores the indicator');
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
  button(ids.anyConnectAccess,'Создать ссылку для установки').click();await settle();
  const setupUrl='https://vpn.tolf.is/anyconnect-setup.html#'+'A'.repeat(43);
  assert(descendants(ids.anyConnectAccess).some(n=>n.tagName==='input'&&n.readOnly&&n.value===setupUrl));
  assert(!descendants(ids.anyConnectAccess).some(n=>n.tagName==='button'&&n.textContent==='Скопировать ссылку'));
  const copyLink=descendants(ids.anyConnectAccess).find(n=>n.tagName==='button'&&n.attributes['aria-label']==='Скопировать ссылку');
  copyLink.click();await settle();
  assert.equal(c.copied,setupUrl);
  assert(ids.anyConnectAccess.textContent.includes('Ссылка скопирована'));
  button(ids.anyConnectAccess,'Настроить на этом устройстве').click();
  const beforeImport=calls.filter(call=>call[1].endsWith('/import')).length;
  assert(button(ids.anyConnectAccess,'Получить сертификат').disabled);
  assert(button(ids.anyConnectAccess,'Сертификат уже импортирован').disabled);
  button(ids.anyConnectAccess,'Получить сертификат').events.click();await settle();
  assert.equal(calls.filter(call=>call[1].endsWith('/import')).length,beforeImport);
  button(ids.anyConnectAccess,'Соединение добавлено').click();
  assert(!descendants(ids.anyConnectAccess).some(n=>n.textContent==='Соединение добавлено'));
  assert(!descendants(ids.anyConnectAccess).some(n=>n.tagName==='a'&&n.textContent==='Добавить в AnyConnect'));
  assert(ids.anyConnectAccess.textContent.includes('✓ Соединение добавлено'));
  button(ids.anyConnectAccess,'Добавить заново').click();
  assert(button(ids.anyConnectAccess,'Получить сертификат').disabled);
  button(ids.anyConnectAccess,'Соединение добавлено').click();
  assert(!button(ids.anyConnectAccess,'Получить сертификат').disabled);
  button(ids.anyConnectAccess,'Сертификат уже импортирован').click();await settle();
  assert(ids.anyConnectAccess.textContent.includes('✓ Сертификат уже импортирован'));
  assert.equal(calls.filter(call=>call[1].endsWith('/import')).length,beforeImport,'existing certificate does not issue a bundle');
  const ingressSelect=()=>descendants(ids.anyConnectAccess).find(n=>n.id==='ocIngress');
  ingressSelect().value='riga';ingressSelect().events.change();
  button(ids.anyConnectAccess,'Настроить на этом устройстве').click();
  assert.equal(descendants(ids.anyConnectAccess).find(n=>n.className==='oc-steps').scrolled.block,'start','repeated local setup opens the selected ingress steps');
  assert(button(ids.anyConnectAccess,'Получить сертификат').disabled,'a different ingress needs connection confirmation');
  button(ids.anyConnectAccess,'Соединение добавлено').click();
  assert(ids.anyConnectAccess.textContent.includes('✓ Сертификат уже импортирован'),'the certificate belongs to the device across ingress changes');
  assert.equal(calls.filter(call=>call[1].endsWith('/import')).length,beforeImport);
  ingressSelect().value='moscow';ingressSelect().events.change();button(ids.anyConnectAccess,'Соединение добавлено').click();
  assert(!descendants(ids.anyConnectAccess).some(n=>n.attributes['aria-label']==='Скопировать пароль'));
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
  assert(!connectionStep.children.some(n=>n.tagName==='a'));
  assert(connectionStep.textContent.includes('✓ Соединение добавлено'));
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
  assert(descendants(ids.anyConnectAccess).includes(ids.anyConnectModeRow), 'routing survives device changes');
  assert(!ids.anyConnectAccess.textContent.includes('private-import-password'));
  assert(!descendants(ids.anyConnectAccess).some(n=>n.className==='oc-copy-feedback'));
  assert.deepEqual(revokedUrls,['blob:test-package']);
  assert.equal(ids.vpnUsername.textContent,'user0_ipad');
  button(ids.anyConnectAccess,'Настроить на этом устройстве').click();
  assert(button(ids.anyConnectAccess,'Получить сертификат').disabled,'a different device needs its own confirmation');
  assert(descendants(ids.anyConnectAccess).filter(n=>n.tagName==='h4').some(n=>n.textContent==='3. Добавьте соединение для «Phone» — Москва'));
  assert(descendants(ids.anyConnectAccess).filter(n=>n.tagName==='h4').some(n=>n.textContent==='4. Получите сертификат для импорта в AnyConnect — «Phone»'));
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
  // Full script reload, not merely rerender: retain non-default device and bundle step.
  c.currentPlatform='ios';
  ids.vpnTransportAnyConnect.click();
  window.ocAccess.selectIngress('riga');
  window.ocAccess.selectIngress('moscow');
  window.dispatchEvent(new c.Event('vpnplatformchange')); await settle();
  let bundle=descendants(ids.anyConnectAccess);
  let checkbox=bundle.find(n=>n.type==='checkbox');
  checkbox.checked=true; checkbox.events.change();
  bundle=descendants(ids.anyConnectAccess);
  bundle.find(n=>n.href?.includes('/shortcuts/control.shortcut')).events.click();
  const selectedBefore=window.ocAccess.selected().id;
  for(const file of ['ios-vpn-buttons.js','transport-selector.js','anyconnect-access.js'])
    vm.runInContext(fs.readFileSync(path.join(root,'js',file),'utf8'),c);
  await settle();
  assert.equal(window.getVpnTransport(),'anyconnect');
  assert.equal(window.ocAccess.ingress().id,'moscow');
  assert.equal(window.ocAccess.selected().id,selectedBefore);
  bundle=descendants(ids.anyConnectAccess);
  assert.equal(bundle.find(n=>n.type==='checkbox').checked,true);
  assert.equal(bundle.find(n=>n.textContent==='Команда добавлена — продолжить').disabled,false);
  bundle.find(n=>n.textContent==='Команда добавлена — продолжить').events.click();
  vm.runInContext(fs.readFileSync(path.join(root,'js','anyconnect-access.js'),'utf8'),c);
  await settle();
  assert(descendants(ids.anyConnectAccess).some(n=>n.href?.includes('ios.mobileconfig?ingress=moscow&buttons=true')));
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
