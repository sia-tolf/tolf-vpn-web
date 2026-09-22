const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

function fixture() {
  const elements = {};
  for (const id of ['serverRiga','serverMoscow','entryPointNote','rigaRecommendation','moscowRecommendation','rigaConnectionWarning']) {
    const classes = new Set();
    const element = {checked:false,disabled:false,textContent:'',className:'',listeners:{},
      classList:{toggle(name,on){on ? classes.add(name) : classes.delete(name);},contains(name){return classes.has(name);}},
      addEventListener(name, fn){this.listeners[name]=fn;},closest(){return this;}};
    elements[id] = element;
  }
  const c = {API:'https://api.tolf.is',document:{getElementById:id=>elements[id]},
    serverInputs:[elements.serverRiga,elements.serverMoscow],t:key=>key,
    fetch:async()=>({ok:false}),setInstallLink(){},vpnMessage:{},updateSelectedServerAddress(){},lastVpnState:null};
  vm.createContext(c);
  vm.runInContext(fs.readFileSync(path.join(__dirname,'../../js/location.js'),'utf8'),c);
  return {c,e:elements,setGeo(value){vm.runInContext(`geographicEntryPoint = ${JSON.stringify(value)}; updateRecommendedEntryPoint();`,c);}};
}

test('Russia stays Moscow with faster Riga or a failed Moscow HTTP probe',()=>{
  const f=fixture(); f.setGeo('moscow');
  for(const latencies of [{moscow:150,riga:10},{moscow:null,riga:10},{moscow:10,riga:150}]) {
    f.c.setEntryPointLatencies(latencies);
    assert.equal(f.e.serverMoscow.checked,true);
    assert.equal(f.e.rigaConnectionWarning.classList.contains('hidden'),false);
    assert.equal(f.e.serverRiga.disabled,false);
  }
});
test('foreign connection prefers Riga unless Moscow is clearly faster',()=>{
  const f=fixture(); f.setGeo('riga');
  assert.equal(f.e.serverRiga.checked,true);
  f.c.setEntryPointLatencies({riga:50,moscow:10});
  assert.equal(f.e.serverRiga.checked,true);
  f.c.setEntryPointLatencies({riga:90,moscow:10});
  assert.equal(f.e.serverMoscow.checked,true);
  assert.equal(f.e.rigaConnectionWarning.classList.contains('hidden'),true);
});
test('manual Riga remains selected in Russia after new measurements',()=>{
  const f=fixture(); f.setGeo('moscow');
  f.e.serverRiga.checked=true; f.e.serverMoscow.checked=false;
  f.e.serverRiga.listeners.change({isTrusted:true});
  f.c.setEntryPointLatencies({riga:150,moscow:10});
  assert.equal(f.e.serverRiga.checked,true);
  assert.equal(f.e.serverMoscow.checked,false);
});
test('country change clears Russia warning without overriding manual selection',()=>{
  const f=fixture(); f.setGeo('moscow');
  f.e.serverMoscow.listeners.change({isTrusted:true});
  f.setGeo('riga');
  assert.equal(f.e.serverRiga.classList.contains('server-caution'),false);
  assert.equal(f.e.rigaConnectionWarning.classList.contains('hidden'),true);
  assert.equal(f.e.serverMoscow.checked,true);
});
