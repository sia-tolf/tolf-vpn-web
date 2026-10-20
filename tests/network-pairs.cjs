const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
let selected = 'us';
const listeners = {};
const element = (tag='div') => ({tag,attrs:{},setAttribute(k,v){this.attrs[k]=v;},children:[], textContent:'', classList:{remove(){}}, appendChild(e){this.children.push(e);}, replaceChildren(){this.children=[];}, addEventListener(k,f){listeners[k]=f;}});
const elements = {networkMetrics:element(), networkMetricMeasuredAt:element(), windowsDeviceServer:element()};
const pairs = [
  {source:'riga',target:'moscow',forward_mbps:100,reverse_mbps:200},
  {source:'riga',target:'us',rtt_ms:111.2,measured_at:new Date().toISOString(),throughput_measured_at:'2000-01-01T00:00:00Z',forward_mbps:300,reverse_mbps:400},
  {source:'moscow',target:'us',forward_mbps:500,reverse_mbps:600}
];
let ready;
const context = vm.createContext({
  document:{readyState:'loading', documentElement:{lang:'ru'}, addEventListener(k,f){ready=f;}, getElementById:id=>elements[id], querySelector:()=>({textContent:'Соединения между серверами TOLF.'}), createElement:element},
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
  const table=()=>elements.networkMetrics.children[0];
  const rows=()=>table().children[2].children;
  assert.equal(elements.networkMetrics.children.length,1);
  assert.equal(table().tag,'table');
  assert.equal(table().children[1].tag,'thead');
  assert.equal(table().children[2].tag,'tbody');
  assert.deepEqual(table().children[1].children[0].children.map(x=>x.textContent),
    ['Соединение','Задержка','Прямое направление','Обратное направление']);
  assert.ok(table().children[1].children[0].children.every(x=>x.attrs.scope==='col'));
  assert.equal(rows().length,2);
  assert.equal(rows()[0].children[0].textContent,'Нью-Йорк ↔ Рига');
  assert.equal(rows()[0].children[0].attrs.scope,'row');
  assert.equal(rows()[0].children[1].children[1].textContent,'111.2 ms');
  assert.equal(rows()[0].children[1].children[0].textContent,'Задержка','mobile latency row has a localized label');
  assert.equal(rows()[0].children[2].children[0].textContent,'Нью-Йорк → Рига');
  assert.equal(rows()[0].children[2].children[1].textContent,'400.0 Mbps');
  assert.equal(rows()[0].children[3].children[0].textContent,'Рига → Нью-Йорк');
  assert.equal(rows()[0].children[3].children[1].textContent,'300.0 Mbps');
  assert.ok(rows()[0].children[2].children[2].textContent.includes('устарел'),'old throughput timestamps remain visible');
  assert.ok(!rows()[0].children[1].children[2].textContent.includes('устарел'),'latency has its own timestamp');
  selected='moscow';listeners.vpntransportchange();
  assert.equal(rows()[0].children[0].textContent,'Москва ↔ Рига');
  assert.equal(rows()[1].children[0].textContent,'Москва ↔ Нью-Йорк');
  assert.equal(rows()[0].children[2].children[1].textContent,'200.0 Mbps');
  assert.equal(rows()[0].children[3].children[1].textContent,'100.0 Mbps');
  assert.equal(rows()[0].children[1].children[1].textContent,'Нет замера');
  selected='riga';listeners.change();
  assert.equal(rows()[0].children[0].textContent,'Рига ↔ Москва');
  assert.equal(rows()[0].children[2].children[1].textContent,'100.0 Mbps');
  assert.equal(rows()[0].children[3].children[1].textContent,'200.0 Mbps');
  for(const [lang,header] of [['en','Connection'],['lv','Savienojums']]) {
    context.document.documentElement.lang=lang;listeners['tolf:measurement-selection-changed']();
    assert.equal(table().children[1].children[0].children[0].textContent,header);
    assert.equal(rows()[0].children[1].children[0].textContent,lang==='en'?'Latency':'Aizture');
  }
  console.log('PASS aligned semantic network table, directional values, missing data, separate timestamps, languages and ingress changes');
})();
