const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const assert = require('node:assert/strict');
const root = path.resolve(__dirname, '..');
const source = name => fs.readFileSync(path.join(root, 'js', name), 'utf8');
const internal = 'https://speedtest.vpn.tolf.is:8444/';
const publicMoscow = 'https://ikev2.tolf.is:8443/';
const publicRiga = 'https://ikev2-riga.tolf.is:8443/';

function setup() {
  const handlers = {}, requests = [], instances = [];
  let selected = 'moscow', mode = 'internal';
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
    setParameter() {}
    setSelectedServer(target) { this.target = target; }
    start() { this.started = true; }
    abort() { this.aborted = true; }
  }
  const c = vm.createContext({
    window, document: {documentElement: {}, addEventListener() {}, hidden: false},
    MutationObserver: class { observe() {} }, CustomEvent: class {
      constructor(type, options) { this.type = type; this.detail = options?.detail; }
    },
    Speedtest, console, Map, Date, Math, performance,
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
        : mode === 'public' ? server !== internal : false;
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
    setSelected: s => {selected = s;}, setHold: p => {hold = p;} };
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
  await c.startConnectionTest();
  assert.equal(instances[1].target.server, publicMoscow, 'fallback without tunnel');
  instances[0].onupdate({pingStatus: '999'});
  assert.equal(c.connectionTestLatency.textContent, '—', 'ignore an old worker');
  instances[1].onupdate({pingStatus: '36', jitterStatus: '2', dlStatus: '158', ulStatus: '24'});
  instances[1].onend(false);
  assert.equal(c.connectionTestStatus.textContent, 'connectionTestComplete');

  s.setSelected('riga');
  c.resetConnectionTestContext();
  await c.startConnectionTest();
  assert.equal(instances[2].target.server, publicRiga, 'do not substitute Moscow for Riga');
  c.resetConnectionTestContext();
  s.setMode('none');
  await c.startConnectionTest();
  assert.equal(c.connectionTestStatus.textContent, 'connectionTestUnavailable');
  assert.equal(c.connectionTestButton.disabled, false);
  assert.equal(c.latencyRiga.textContent, 'connectionTestUnavailable');

  s.setMode('internal');
  let release;
  s.setHold(new Promise(resolve => {release = resolve;}));
  const pending = c.startConnectionTest();
  c.resetConnectionTestContext();
  release();
  await pending;
  assert.equal(instances.length, 3, 'cancel while resolving, before a worker starts');
  assert.equal(c.connectionTestButton.disabled, false);

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
  console.log('PASS measurement addresses, shared badges, fallback, unavailable, cancellation, timeouts');
})().catch(error => { console.error(error); process.exitCode = 1; });
