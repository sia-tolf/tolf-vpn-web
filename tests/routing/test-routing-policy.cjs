const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');
const root = path.resolve(__dirname, '../..');

function snapshot(revision = 1, extra = {}) {
  return {protocol: 1, revision, routingRules: {riga: [], moscow: ['delfi.lv'], usa: []},
    availableExits: ['riga', 'moscow'], state: 'pending', enforcementAvailable: false,
    appliedRevision: null, ...extra};
}
function deferred() {
  let resolve, reject;
  const promise = new Promise((yes, no) => {resolve = yes; reject = no;});
  return {promise, resolve, reject};
}
function context(api) {
  const elements = Object.fromEntries(['routingPolicySave', 'routingPolicyReload', 'routingPolicyStatus']
    .map(id => [id, {disabled: false, textContent: '', addEventListener() {}}]));
  const c = {URL, console, apiRequest: api, routingRuleGroups: null,
    routingRulesValidation: null, profileSettings: null, vpnBusy: false,
    t: key => key, setInterval() {return 1;}, clearInterval() {},
    document: {hidden: false, getElementById: id => elements[id] || null, querySelector() {return null;}}};
  vm.createContext(c);
  for (const file of ['routing-rules.js', 'routing-policy.js']) {
    vm.runInContext(fs.readFileSync(path.join(root, 'js', file), 'utf8'), c);
  }
  c.elements = elements;
  return c;
}
const settle = () => new Promise(resolve => setImmediate(resolve));

test('load then save uses server revision and independent endpoint', async () => {
  const calls = [];
  const c = context(async (url, opts) => {calls.push([url, opts]); return snapshot(opts.method === 'POST' ? 2 : 1);});
  c.setRoutingAccount('user0'); await settle();
  c.setRoutingRules({moscow:['delfi.lv', 'example.com']}); c.routingPolicyEdited();
  await c.saveRoutingPolicy();
  const [url, opts] = calls.at(-1);
  assert.equal(url, '/vpn/routing-rules');
  assert.equal(opts.method, 'POST');
  assert.deepEqual(JSON.parse(opts.body), {revision:1,routingRules:{riga:[],moscow:['delfi.lv','example.com'],usa:[]}});
  assert.equal(c.elements.routingPolicyStatus.textContent, 'routingStoredOnly');
});

test('only matching, enabled server acknowledgement is shown as applied', () => {
  const c = context(async () => snapshot());
  assert.equal(c.routingSnapshotStatus(snapshot(2, {state:'applied',appliedRevision:1,enforcementAvailable:true})), 'routingPending');
  assert.equal(c.routingSnapshotStatus(snapshot(2, {state:'applied',appliedRevision:2,enforcementAvailable:false})), 'routingStoredOnly');
  assert.equal(c.routingSnapshotStatus(snapshot(2, {state:'applied',appliedRevision:2,enforcementAvailable:true})), 'routingAppliedMoscow');
});

test('conflict keeps draft and disables overwrite until explicit reload', async () => {
  const c = context(async (_url, opts) => {
    if (opts.method === 'POST') throw Object.assign(new Error('Conflict'), {status:409});
    return snapshot();
  });
  c.setRoutingAccount('user0'); await settle();
  c.setRoutingRules({moscow:['example.com']}); c.routingPolicyEdited();
  await c.saveRoutingPolicy();
  assert.equal(c.elements.routingPolicyStatus.textContent, 'routingConflict');
  assert.equal(c.elements.routingPolicySave.disabled, true);
  assert.deepEqual(Array.from(c.getRoutingRulesSelection().moscow), ['example.com']);
  await c.refreshRoutingPolicy({discard:true});
  assert.deepEqual(Array.from(c.getRoutingRulesSelection().moscow), ['delfi.lv']);
});

test('late account response cannot restore rules after sign-out', async () => {
  const wait = deferred();
  const c = context(() => wait.promise);
  c.setRoutingAccount('user0'); c.setRoutingAccount(null);
  wait.resolve(snapshot()); await settle();
  assert.deepEqual(Array.from(c.getRoutingRulesSelection().moscow), []);
  assert.equal(c.elements.routingPolicySave.disabled, true);
});

test('stale status GET cannot overwrite a completed save', async () => {
  const wait = deferred(); let gets = 0;
  const c = context(async (_url, opts) => opts.method === 'POST' ? snapshot(2) : ++gets === 1 ? snapshot() : wait.promise);
  c.setRoutingAccount('user0'); await settle();
  const pending = c.refreshRoutingPolicy();
  c.routingPolicyEdited(); await c.saveRoutingPolicy();
  wait.resolve(snapshot(1)); await pending;
  assert.equal(vm.runInContext('routingRevision', c), 2);
});

test('polling preserves dirty editor when another browser updates the server', async () => {
  let revision = 1;
  const c = context(async () => snapshot(revision));
  c.setRoutingAccount('user0'); await settle();
  c.setRoutingRules({riga:['example.com']}); c.routingPolicyEdited();
  revision = 2; await c.refreshRoutingPolicy();
  assert.deepEqual(Array.from(c.getRoutingRulesSelection().riga), ['example.com']);
  assert.equal(c.elements.routingPolicyStatus.textContent, 'routingConflict');
});
