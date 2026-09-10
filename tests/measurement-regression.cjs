const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const path = require('node:path');
const root = path.resolve(__dirname, '..');

function simulate(kind, outcome) {
  let now = 0, id = 0, finished = false;
  const jobs = new Map(), requests = [];
  function schedule(fn, ms, repeat = false) {
    const n = ++id;
    jobs.set(n, {fn, time: now + Math.max(1, ms), repeat, ms});
    return n;
  }
  class XHR {
    constructor() { this.upload = {}; this.status = 0; requests.push(this); }
    open(method) { this.method = method; }
    setRequestHeader() {}
    abort() { this.aborted = true; }
    send(body) {
      this.bytes = body?.size || 0;
      schedule(() => {
        if (this.aborted) return;
        if (outcome === 'network') return this.onerror?.();
        if (outcome === 'timeout') return this.ontimeout?.();
        this.status = outcome === 'http' ? 500 : 200;
        this.onprogress?.({loaded: 1048576});
        this.onload?.();
      }, 100);
    }
  }
  const context = vm.createContext({
    console, Blob, ArrayBuffer, Uint32Array, Math, JSON,
    Date: class extends Date { getTime() { return now; } },
    XMLHttpRequest: XHR, navigator: {userAgent: 'Safari'},
    performance: {getEntries: () => []},
    setTimeout: (f, ms) => schedule(f, ms),
    setInterval: (f, ms) => schedule(f, ms, true),
    clearInterval: n => jobs.delete(n), clearTimeout: n => jobs.delete(n),
    addEventListener() {}, postMessage() {}
  });
  vm.runInContext(fs.readFileSync(path.join(root, 'speedtest_worker.js'), 'utf8'), context);
  Object.assign(context.settings, {
    forceIE11Workaround: true, xhr_ignoreErrors: 0,
    xhr_ul_blob_megabytes: 4, xhr_ulMultistream: 4, xhr_dlMultistream: 4,
    time_ulGraceTime: 0, time_dlGraceTime: 0,
    time_ul_max: 1, time_dl_max: 1, time_auto: false,
    overheadCompensationFactor: 1, count_ping: 3
  });
  context.testState = {upload: 3, download: 1, ping: 2}[kind];
  context[{upload: 'ulTest', download: 'dlTest', ping: 'pingTest'}[kind]](() => { finished = true; });
  for (let step = 0; !finished && step < 10000; step++) {
    const entry = [...jobs].sort((a, b) => a[1].time - b[1].time)[0];
    assert.ok(entry, 'test must finish');
    const [n, job] = entry;
    now = job.time;
    if (job.repeat) job.time += job.ms; else jobs.delete(n);
    job.fn();
  }
  assert.ok(finished);
  const result = context[{upload: 'ulStatus', download: 'dlStatus', ping: 'pingStatus'}[kind]];
  if (outcome === 'success') assert.ok(Number(result) > 0, result);
  else assert.equal(result, 'Fail');
  if (kind === 'upload') {
    assert.ok(requests.every(r => r.bytes === 4 * 1048576));
    if (outcome === 'success') assert.ok(requests.length >= 4);
  }
}
for (const kind of ['upload', 'download', 'ping']) {
  for (const outcome of ['success', 'http', 'network', 'timeout']) {
    simulate(kind, outcome);
    console.log(`PASS ${kind}: ${outcome}`);
  }
}

const element = () => ({textContent: '—', setAttribute() {}, addEventListener() {}, querySelector() {return null;}});
const c = vm.createContext({
  connectionTestButton: element(), connectionTestTitle: element(),
  connectionTestStatus: element(), connectionTestLatency: element(),
  connectionTestJitter: element(), connectionTestDownload: element(), connectionTestUpload: element(),
  serverInputs: [], getSelectedServerKey: () => 'riga', t: key => key,
  clearTimeout() {}, console
});
vm.runInContext(fs.readFileSync(path.join(root, 'js/connection-test.js'), 'utf8'), c);
c.connectionTestLatency.textContent = '14.0 ms';
assert.equal(c.connectionTestHasResult(), false);
c.connectionTestDownload.textContent = '123.0 Mbps';
c.connectionTestUpload.textContent = '45.0 Mbps';
assert.equal(c.connectionTestHasResult(), true);
c.finishConnectionTest(false);
assert.equal(c.connectionTestStatus.textContent, 'connectionTestComplete');
c.connectionTestUpload.textContent = '—';
c.finishConnectionTest(false);
assert.equal(c.connectionTestStatus.textContent, 'connectionTestFailed');
console.log('PASS completion requires all measurements');
