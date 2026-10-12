const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
let selected = 'us';
const listeners = {};
const element = () => ({children:[], textContent:'', classList:{remove(){}}, appendChild(e){this.children.push(e);}, replaceChildren(){this.children=[];}, addEventListener(k,f){listeners[k]=f;}});
const elements = {networkMetrics:element(), networkMetricMeasuredAt:element(), windowsDeviceServer:element()};
const pairs = [
  {source:'riga',target:'moscow',forward_mbps:100,reverse_mbps:200},
  {source:'riga',target:'us',forward_mbps:300,reverse_mbps:400},
  {source:'moscow',target:'us',forward_mbps:500,reverse_mbps:600}
];
let ready;
const context = vm.createContext({
  document:{readyState:'loading', documentElement:{lang:'ru'}, addEventListener(k,f){ready=f;}, getElementById:id=>elements[id], createElement:element},
  window:{addEventListener(k,f){listeners[k]=f;}, setInterval(){}},
  getConnectionTestServerKey:()=>selected, serverInputs:[],
  MutationObserver:class {observe(){}}, AbortController,
  setTimeout(){return 1;},clearTimeout(){},console,
  fetch:async()=>({ok:true,json:async()=>({pairs})})
});
vm.runInContext(fs.readFileSync(path.join(__dirname,'../js/network-metrics.js'),'utf8'),context);
for(const source of ['riga','moscow','us']) {
  const result=context.networkPairsForIngress(pairs,source);
  assert.equal(result.length,2);
  assert.ok(result.every(p=>p.source===source && p.target!==source));
  const us=result.find(p=>p.target==='us');
  if(source==='riga') assert.equal(us.forward_mbps,300);
}
const us=context.networkPairsForIngress(pairs,'us');
assert.equal(us[0].forward_mbps,400);assert.equal(us[0].reverse_mbps,300);
assert.equal(us[1].forward_mbps,600);assert.equal(us[1].reverse_mbps,500);
assert.equal(context.networkPairsForIngress([], 'us')[0].forward_mbps,undefined);
(async()=>{
  ready(); await new Promise(resolve=>setImmediate(resolve));
  assert.equal(elements.networkMetrics.children.length,2);
  assert.equal(elements.networkMetrics.children[0].children[0].textContent,'Нью-Йорк ↔ Рига');
  selected='moscow';listeners.vpntransportchange();
  assert.equal(elements.networkMetrics.children[0].children[0].textContent,'Москва ↔ Рига');
  assert.equal(elements.networkMetrics.children[1].children[0].textContent,'Москва ↔ Нью-Йорк');
  selected='riga';listeners.change();
  assert.equal(elements.networkMetrics.children[0].children[0].textContent,'Рига ↔ Москва');
  console.log('PASS pair orientation, missing data and ingress changes');
})();
