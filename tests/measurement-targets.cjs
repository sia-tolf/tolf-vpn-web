const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const assert = require('node:assert/strict');
const root = path.resolve(__dirname, '..');
const source = name => fs.readFileSync(path.join(root, 'js', name), 'utf8');
const internal = 'https://speedtest.vpn.tolf.is:8444/';
const publicMoscow = 'https://ikev2.tolf.is:8443/';
const publicRiga = 'https://ikev2-riga.tolf.is:8443/';
const privateRiga = 'https://speedtest-riga.vpn.tolf.is:8444/';
const privateUs = 'https://speedtest-us.vpn.tolf.is:8444/';

function setup() {
  const handlers = {}, requests = [], instances = [];
  let selected = 'moscow', mode = 'internal', testMode = 'vpn';
  let hold = null;
  const element = () => ({
    textContent: '—', disabled: false, className: '',
    setAttribute() {}, addEventListener() {}, querySelector() { return null; }
  });
  const window = {
    addEventListener(name, fn) { (handlers[name] ||= []).push(fn); },
    dispatchEvent(event) { for (const fn of handlers[event.type] || []) fn(event); },
    // The chosen protocol must not influence which address is accessible.
    getVpnTransport: () => 'ikev2'
  };
  class Speedtest {
    constructor() {
      instances.push(this);
      this.worker = {terminate: () => {this.terminated = true;}};
    }
    setParameter(k,v) { (this.settings ||= {})[k]=v; }
    setSelectedServer(target) { this.target = target; }
    start() { this.started = true; }
    abort() { this.aborted = true; }
  }
  const c = vm.createContext({
    window, document: {documentElement: {}, addEventListener() {}, hidden: false, getElementById: id => id === 'measurementMode' ? {value:testMode} : null},
    MutationObserver: class { observe() {} }, CustomEvent: class {
      constructor(type, options) { this.type = type; this.detail = options?.detail; }
    },
    Speedtest, console, Map, Date, Math, performance,
    measureConfirmedUpload:async(server,{onprogress})=>{onprogress({mbps:24,acknowledgedBytes:3000000});return {mbps:24};},
    AbortController, setTimeout: (fn, ms) => setTimeout(fn, Math.min(ms, 20)),
    clearTimeout, clearInterval,
    getSelectedServerKey: () => selected, t: key => key, serverInputs: [],
    latencyRiga: element(), latencyMoscow: element(),
    fetch: async (url, options) => {
      const server = url.split('empty.php')[0];
      requests.push(server);
      if (hold) await hold;
      if (mode === 'timeout') return new Promise((_, reject) => {
        options.signal.addEventListener('abort', () => reject(new Error('timeout')), {once: true});
      });
      const available = mode === 'internal' ? server !== publicMoscow
        : mode === 'public' ? ![internal, privateRiga, privateUs].includes(server) : false;
      if (!available) throw new Error('unreachable');
      return {status: 200, text: async () => ''};
    }
  });
  for (const name of ['connectionTestButton', 'connectionTestTitle', 'connectionTestStatus',
    'connectionTestLatency', 'connectionTestJitter', 'connectionTestDownload', 'connectionTestUpload']) {
    c[name] = element();
  }
  vm.runInContext(source('measurement-targets.js'), c);
  vm.runInContext(source('connection-test.js'), c);
  return { c, requests, instances, window, setMode: m => {mode = m;},
    setSelected: s => {selected = s;}, setTestMode: m => {testMode=m;}, setHold: p => {hold = p;} };
}

(async () => {
  const s = setup();
  const {c, requests, instances, window} = s;
  vm.runInContext(source('latency.js'), c);
  await c.measureEntryPointLatencies();
  assert.ok(c.latencyMoscow.textContent.endsWith(' ms'));
  assert.ok(!requests.includes(publicMoscow), 'prefer the reachable tunnel endpoint');
  await c.startConnectionTest();
  assert.equal(instances[0].target.server, internal, 'IKEv2 tab with active AnyConnect');
  assert.equal(c.connectionTestButton.disabled, true);
  window.dispatchEvent({type: 'vpntransportchange'});
  assert.ok(instances[0].aborted && instances[0].terminated);

  s.setMode('public');
  s.setTestMode('direct');
  await c.startConnectionTest();
  assert.equal(instances[1].target.server, publicMoscow, 'explicit direct mode uses the public target');
  instances[0].onupdate({pingStatus: '999'});
  assert.equal(c.connectionTestLatency.textContent, '—', 'ignore an old worker');
  instances[1].onupdate({pingStatus: '36', jitterStatus: '2', dlStatus: '158', ulStatus: '24'});
  assert.equal(instances[1].settings.test_order, 'P_D');
  await instances[1].onend(false);
  assert.equal(c.connectionTestStatus.textContent, 'connectionTestComplete');

  s.setMode('internal');
  s.setTestMode('vpn');
  s.setSelected('riga');
  c.resetConnectionTestContext();
  await c.startConnectionTest();
  assert.equal(instances[2].target.server, privateRiga, 'Riga speed uses its VPN-only listener');
  c.resetConnectionTestContext();
  s.setMode('none');
  await c.startConnectionTest();
  assert.equal(c.connectionTestStatus.textContent, 'connectionTestVpnUnavailable');
  assert.equal(c.connectionTestButton.disabled, false);
  assert.ok(c.latencyRiga.textContent.endsWith(' ms'), 'a speed-test failure must not overwrite entry latency');

  s.setMode('internal');
  let release;
  s.setHold(new Promise(resolve => {release = resolve;}));
  const pending = c.startConnectionTest();
  c.resetConnectionTestContext();
  release();
  await pending;
  assert.equal(instances.length, 3, 'cancel while resolving, before a worker starts');
  assert.equal(c.connectionTestButton.disabled, false);

  const offline = setup();
  offline.setSelected('riga'); offline.setMode('public');
  await offline.c.resolveMeasurementTarget('riga');
  const beforeVpnProbe = offline.requests.length;
  await offline.c.startConnectionTest();
  assert.equal(offline.instances.length, 0, 'do not start a public test when VPN is unavailable');
  assert.equal(offline.c.connectionTestStatus.textContent, 'connectionTestVpnUnavailable');
  assert.deepEqual(offline.requests.slice(beforeVpnProbe), [privateRiga], 'no public fallback for Riga VPN throughput');
  const separate = setup();
  const entry = separate.c.resolveMeasurementTarget('riga');
  const vpn = separate.c.resolveMeasurementTarget('riga', {purpose:'connection'});
  assert.notEqual(entry, vpn, 'entry and VPN cache entries are separate');
  assert.equal((await entry).server, publicRiga);
  assert.equal((await vpn).server, privateRiga);

  const timeout = setup();
  timeout.setMode('timeout');
  assert.equal(await timeout.c.resolveMeasurementTarget('moscow'), null);
  assert.deepEqual(timeout.requests, [internal, publicMoscow], 'bounded fallback after timeouts');

  const parallel = setup();
  const p1 = parallel.c.resolveMeasurementTarget('moscow');
  const p2 = parallel.c.resolveMeasurementTarget('moscow');
  assert.equal(p1, p2, 'badge and full test share an in-flight selection');
  await p1;
  assert.equal(parallel.requests.length, 3);
  const ny=setup();
  ny.setSelected('us');await ny.c.startConnectionTest();
  assert.equal(ny.instances[0].target.server,privateUs);
  assert.equal(ny.instances[0].target.name,'cityNewYork');
  ny.c.resetConnectionTestContext();
  ny.c.currentPlatform='windows';
  ny.c.document.getElementById=id=>id==='windowsDeviceServer'?{value:'us'}:id==='measurementMode'?{value:'direct'}:null;
  ny.setSelected('riga');await ny.c.startConnectionTest();
  assert.equal(ny.instances[1].target.server,'https://ikev2-us.tolf.is:8443/','Windows selector must determine destination');
  ny.c.resetConnectionTestContext();
  for (const [city, publicAddress, privateAddress] of [
    ['riga',publicRiga,privateRiga], ['moscow',publicMoscow,internal],
    ['us','https://ikev2-us.tolf.is:8443/',privateUs]]) {
    const route=setup();route.setSelected(city);route.setMode('public');
    await route.c.startConnectionTest();
    assert.equal(route.instances.length,0,'VPN mode must not fall back to a public endpoint: '+city);
    assert.deepEqual(route.requests,[privateAddress]);
    route.setTestMode('direct');await route.c.startConnectionTest();
    assert.equal(route.instances[0].target.server,publicAddress);
    assert.equal(route.instances[0].settings.workerFile,'/speedtest_worker.js');
    route.c.resetConnectionTestContext();
  }
  const independent=setup();independent.setMode("public");
  independent.c.currentPlatform='windows';
  independent.c.document.getElementById=id=>id==='measurementServer'?{value:'moscow'}:id==='measurementMode'?{value:'direct'}:id==='windowsDeviceServer'?{value:'us'}:null;
  await independent.c.startConnectionTest();
  assert.equal(independent.instances[0].target.server,publicMoscow,'measurement selector is independent of profile/platform selectors');
  independent.c.resetConnectionTestContext();
  console.log('PASS explicit direct/VPN routes for every city, private-only VPN, independent selection, cache and cancellation');
})().catch(error => { console.error(error); process.exitCode = 1; });
