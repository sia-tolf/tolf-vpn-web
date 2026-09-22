const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const source = name => fs.readFileSync(path.join(__dirname, '../../js', name), 'utf8');

for (const stalled of ['fetch', 'body']) {
  test('account request deadline covers stalled ' + stalled, async () => {
    let signal;
    const c = {API:'https://example.test', AbortController, setTimeout, clearTimeout,
      fetch: async (_, opts) => {
        signal = opts.signal;
        if (stalled === 'fetch') return new Promise(() => {});
        return {ok:true, json:() => new Promise(() => {})};
      }};
    vm.createContext(c); vm.runInContext(source('api.js'), c);
    await assert.rejects(c.apiRequest('/me', {timeoutMs:10}), /timed out/);
    assert.equal(signal.aborted, true);
  });
}

function fixture() {
  const elements = {};
  function el(id) {
    return elements[id] ||= {dataset:{},textContent:'',listeners:{},classes:new Set(),
      classList:{add(v){elements[id].classes.add(v);},remove(v){elements[id].classes.delete(v);}},
      addEventListener(k,v){this.listeners[k]=v;}};
  }
  const c = {document:{getElementById:el,addEventListener(){},hidden:false},
    window:{addEventListener(){}},t:k=>k, applyServerAccess(){},showVpn(){c.shown++;},
    showSignedOut(){c.signedOut++;}, updateInvitationAccount:async()=>{},shown:0,signedOut:0};
  for(const id of ['createAccountButton','cancelRegisterButton','signedOutMainActions','signedOutMessage',
    'signOutButton','signInButton','submitRegisterButton','loadingCard','vpnCard','signedOutCard']) c[id]=el(id);
  vm.createContext(c); vm.runInContext(source('account.js'),c);
  c.handleEntryAction=()=>{};
  return {c,el};
}
test('network failure offers retry, preserves auth, and retry can recover', async()=>{
  const {c,el}=fixture();
  c.apiRequest=async()=>{throw new Error('offline');};
  await c.loadAccount();
  assert.equal(c.signedOut,0);
  assert.equal(el('accountRetry').classes.has('hidden'),false);
  assert.equal(el('accountLoadMessage').dataset.i18n,'accountLoadFailed');
  c.apiRequest=async()=>({vpn:{configured:true}});
  await el('accountRetry').listeners.click();
  assert.equal(c.shown,1);
  assert.equal(el('accountRetry').classes.has('hidden'),true);
});
test('only expired authentication shows sign-in', async()=>{
  const {c}=fixture(); c.apiRequest=async()=>{throw Object.assign(new Error(),{status:401});};
  await c.loadAccount(); assert.equal(c.signedOut,1);
});
test('concurrent loads are deduplicated and invitations do not block loading', async()=>{
  const {c}=fixture(); let finish, calls=0;
  c.apiRequest=()=>{calls++; return new Promise(r=>{finish=r;});};
  c.updateInvitationAccount=()=>new Promise(()=>{});
  const first=c.loadAccount(); await c.loadAccount(); assert.equal(calls,1);
  finish({vpn:{configured:true}}); await first; assert.equal(c.shown,1);
});
