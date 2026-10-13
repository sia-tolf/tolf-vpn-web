const {withShares}=require('./ios-city-share-fixture.cjs');
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
  addEventListener(name, fn) { const previous=this.events[name]; this.events[name]=(...args)=>{previous?.(...args); return fn(...args);}; }
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
const ids={};for(const id of ['ciscoClientInstall','quickSetupLink','manualSetupLink'])ids[id]=new Element();
const memory=new Map(), handlers={};
const window={getVpnTransport:()=>transport,addEventListener(n,f){(handlers[n]||=[]).push(f)},dispatchEvent(e){for(const f of handlers[e.type]||[])f(e)}};
let transport='anyconnect';
const c={window,currentPlatform:'ios',document:{documentElement:{lang:'ru'},getElementById:id=>ids[id],createElement:tag=>new Element(tag)},
localStorage:{getItem:k=>memory.get(k),setItem:(k,v)=>memory.set(k,v)},MutationObserver:class{observe(){}},Event:class{constructor(type){this.type=type}}};
vm.createContext(c);vm.runInContext(fs.readFileSync(path.join(root,'js/cisco-client-install.js'),'utf8'),c);
assert.equal(window.isCiscoClientConfirmed(),false);
let prevented=false;ids.quickSetupLink.events.click({preventDefault(){prevented=true},stopImmediatePropagation(){}});
assert(prevented);assert.equal(ids.manualSetupLink.attributes['aria-disabled'],'true');
let check=descendants(ids.ciscoClientInstall).find(n=>n.type==='checkbox');check.checked=true;check.events.change();
assert(window.isCiscoClientConfirmed('ios'));assert.equal(ids.quickSetupLink.attributes['aria-disabled'],'false');
c.currentPlatform='android';window.dispatchEvent(new c.Event('vpnplatformchange'));assert.equal(window.isCiscoClientConfirmed('android'),false);
assert.equal(ids.manualSetupLink.attributes['aria-disabled'],'true');
transport='ikev2';window.dispatchEvent(new c.Event('vpntransportchange'));assert.equal(ids.manualSetupLink.attributes['aria-disabled'],'false');
assert(ids.ciscoClientInstall.classList.contains('hidden'));
console.log('PASS Cisco installation confirmation: navigation blocked, persisted per platform, IKEv2 unaffected');
