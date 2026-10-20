const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

const root = path.resolve(__dirname, '../..');
const source = fs.readFileSync(path.join(root, 'js/quick-entry.js'), 'utf8');
const hidden = new Set(['quickSetupCard', 'signedOutCard', 'invitationCard']);
const elements = {};
for (const id of hidden) {
  elements[id] = {
    classList: {
      contains: name => name === 'hidden' && hidden.has(id),
      toggle: (name, force) => {
        if (name !== 'hidden') return;
        if (force) hidden.add(id); else hidden.delete(id);
      }
    }
  };
}
for (const id of ['manualSetupLink','quickSetupLink','vpnCard']) {
  if (!elements[id]) {
    const classes=new Set();
    elements[id]={
      href:id==='quickSetupLink'?'/quick/':'#vpnCard',
      attributes:{},listeners:{},parentElement:{after(){}},
      setAttribute(name,value){this.attributes[name]=value;},
      addEventListener(name,listener){this.listeners[name]=listener;},
      classList:{
        contains(name){return classes.has(name);},
        toggle(name,on){if(on)classes.add(name);else classes.delete(name);},
        add(name){classes.add(name);}
      }
    };
  }
}
const observers = [];
const bodyClasses = new Set();
const context = {
  URL,
  location:{href:'https://vpn.tolf.is/',hash:''},
  navigator:{userAgent:'iPhone',platform:'iPhone',maxTouchPoints:5},
  currentPlatform:'ios',
  window:{addEventListener(){},getVpnTransport:()=> 'ikev2'},
  document:{
    body:{classList:{add(name){bodyClasses.add(name);},remove(name){bodyClasses.delete(name);}}},
    documentElement:{lang:'ru'},
    createElement:()=>({
      className:'',children:[],setAttribute(){},replaceChildren(){},
      append(){},classList:{toggle(){}}
    }),
    getElementById:id => elements[id],
  },
  fetch: async () => ({ ok: true, json: async () => ({ version: 1 }) }),
  MutationObserver: class {
    constructor(callback) { observers.push(callback); }
    observe() {}
  }
};
vm.createContext(context);
vm.runInContext(source, context);

setImmediate(() => {
  assert.equal(hidden.has('quickSetupCard'), false, 'quick setup is visible to signed-out visitors');
  context.vpnInvitation = {token:'pending'};
  observers.forEach(callback => callback());
  assert.equal(hidden.has('quickSetupCard'), true, 'invitation takes priority');
  context.vpnInvitation = null;
  observers.forEach(callback => callback());
  assert.equal(hidden.has('quickSetupCard'), false);
  console.log('PASS main page quick-setup entry visibility and invitation priority');
});

for(const protocol of ['ikev2','anyconnect']){
 context.currentPlatform='windows';context.window.getVpnTransport=()=>protocol;
 bodyClasses.add('manual-setup-open');
 let prevented=false;
 elements.quickSetupLink.listeners.click({preventDefault(){prevented=true;}});
 assert(!bodyClasses.has('manual-setup-open'),'Quick setup hides manual panel');
 assert.equal(elements.manualSetupLink.attributes['aria-expanded'],'false');
 assert(prevented,'Windows quick setup on iPad is blocked for '+protocol);
}
context.currentPlatform='android';context.window.getVpnTransport=()=> 'anyconnect';
let androidPrevented=false;
elements.quickSetupLink.listeners.click({preventDefault(){androidPrevented=true;}});
assert(androidPrevented,'Android quick setup on iPad must first direct the user to Android');
context.currentPlatform='ios';
let iosPrevented=false;
elements.quickSetupLink.listeners.click({preventDefault(){iosPrevented=true;}});
assert.equal(iosPrevented,false,'current iPad can open quick setup before installing Cisco');
context.currentPlatform='windows';
context.navigator.userAgent='Windows NT 10.0';context.navigator.platform='Win32';context.navigator.maxTouchPoints=0;
let prevented=false;
elements.quickSetupLink.listeners.click({preventDefault(){prevented=true;}});
assert(!prevented);
assert.equal(new URL(elements.quickSetupLink.href).searchParams.get('platform'),'windows');
console.log('PASS Windows selection stays Windows; mobile quick setup blocked for both protocols');
