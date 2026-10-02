const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const assert = require('node:assert/strict');
const root = path.resolve(__dirname, '..');
class Element {
  constructor(tag = 'div') {
    this.tagName = tag; this.children = []; this.events = {}; this.attributes = {};
    this.dataset = {}; this.disabled = false; this.value = ''; this._text = '';
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
  click() { assert.equal(this.disabled, false); return this.events.click?.(); }
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
    getElementById: id => ids[id], querySelectorAll: () => modes,
    createElement: tag => new Element(tag), addEventListener() {}};
  const handlers = {}, window = {tolfAccountState:{authenticated:true,userId:'owner'},
    addEventListener(name, fn) { (handlers[name] ||= []).push(fn); },
    dispatchEvent(event) { for (const fn of handlers[event.type] || []) fn(event); },
    confirm: () => true};
  const first = {id:'one',label:'iPad',username:'tolf-oc-'+'1'.repeat(32),state:'active',mode:'auto'};
  const second = {id:'two',label:'Phone',username:'tolf-oc-'+'2'.repeat(32),state:'active',mode:'lv'};
  const devices = [first,second], calls = [];
  let heldSession = null;
  async function request(url, options = {}) {
    const p = url.replace('https://api.tolf.is',''); calls.push([options.method || 'GET',p,options.credentials]);
    if (p.endsWith('/capabilities')) return {issuance:true,nodeReady:true,version:2};
    if (p === '/oc/access/devices') return {devices};
    const d = devices.find(d => p.includes('/'+d.id+'/'));
    if (p.endsWith('/session')) {
      if (heldSession) await heldSession;
      return {username:d.username,mode:d.mode,connected:true};
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
    Event:class {constructor(type){this.type=type;}},
    MutationObserver:class {observe(){}},
    setInterval(){},setTimeout,clearTimeout,
    apiRequest:request,copyText:async value=>{c.copied=value;},
    fetch:async (url,options)=>({ok:true,json:async()=>request(url,options)})});
  for (const file of ['transport-selector.js','anyconnect-access.js']) {
    vm.runInContext(fs.readFileSync(path.join(root,'js',file),'utf8'),c);
  }
  ids.vpnTransportAnyConnect.click(); await settle();
  assert.equal(ids.vpnUsername.textContent,first.username);
  assert(ids.anyConnectModeSelector.classList.contains('policy-confirmed'));
  button(ids.anyConnectAccess,'Получить сертификат и ссылки').click(); await settle();
  assert(ids.anyConnectAccess.textContent.includes('private-import-password'));
  const select = descendants(ids.anyConnectAccess).find(n=>n.tagName==='select');
  select.value = second.id; select.events.change(); await settle();
  assert(!ids.anyConnectAccess.textContent.includes('private-import-password'));
  assert.equal(ids.vpnUsername.textContent,second.username);
  modes[1].click(); await settle();
  assert.equal(first.mode,'auto'); assert.equal(second.mode,'ru');
  assert(calls.every(call => !call[1].includes('/oc-test')));
  assert(calls.filter(call=>call[1].endsWith('/policy')||call[1].endsWith('/session')).every(call=>call[2]==='include'));
  // A late session response must not restore the green indicator after logout.
  let release; heldSession = new Promise(resolve=>{release=resolve;});
  window.dispatchEvent(new c.Event('focus')); await settle();
  window.setAnyConnectAccount(null); release(); await settle();
  assert.equal(ids.anyConnectAccess.textContent,'');
  assert(!ids.anyConnectModeSelector.classList.contains('policy-confirmed'));
  assert(modes.every(n=>n.disabled));
  console.log('PASS personal UI: device selection, import secret clearing, isolated routing, authenticated endpoints, stale session after logout');
})().catch(error=>{console.error(error);process.exitCode=1;});
