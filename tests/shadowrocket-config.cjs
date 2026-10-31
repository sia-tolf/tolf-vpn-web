const assert=require('node:assert/strict');
require('../js/shadowrocket-config.js');
const config=globalThis.TolfShadowrocketConfig;
const content=config.build('test-user','Test_only-2026!@');
assert.equal((content.match(/ = openconnect,/g)||[]).length,3);
assert.match(content,/TOLF_Moscow = openconnect, oc\.tolf\.is, 4443, user=test-user, password=Test_only-2026!@, udp=1/);
assert.match(content,/TOLF_New_York = openconnect, oc-us-moscow\.tolf\.is, 4443/);
assert(!content.includes('oc-us.tolf.is'));
assert.match(content,/dns-server = 10\.254\.0\.53#proxy/);
assert(!content.includes('[Proxy Group]'));
assert.match(content,/FINAL,PROXY/);
assert(!content.includes(',TOLF'));
assert(content.indexOf('10.254.0.53/32,PROXY')<content.indexOf('10.0.0.0/8,DIRECT'));
assert.match(content,/DOMAIN-SUFFIX,tolf\.is,DIRECT/);
for(const value of ['pass, udp=0',' leading-space','trailing-space ','with space','with"quote','with\\slash','with#comment','password\n[Rule]\nFINAL,DIRECT']) {
  assert.equal(config.supportsPassword(value),false);
  assert.throws(()=>config.build('test-user',value));
  const fallback=config.build('test-user',value,true);
  assert(!fallback.includes(value));
  assert.equal((fallback.match(/password=, udp=1/g)||[]).length,3);
}
assert.throws(()=>config.build('injected,invalid','Test_only-2026!@'));
const credentials=config.credentialsText('test-user','Test_only-2026!@');
assert(credentials.includes('https://vpn.tolf.is/auth/'));
assert(credentials.includes('test-user')&&credentials.includes('Test_only-2026!@'));
console.log('PASS: three endpoints, selected Home routing, own DNS, direct public service domains, credential injection prevention and explicit manual fallback');
