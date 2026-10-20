
const assert=require('node:assert/strict'),fs=require('node:fs');
const {JSDOM}=require(process.env.TOLF_JSDOM||'jsdom');
const html=fs.readFileSync('index.html','utf8'),source=fs.readFileSync('js/cisco-client-install.js','utf8');
const devices=[
 {native:'ios',ua:'Mozilla/5.0 (iPhone; CPU iPhone OS 26_0 like Mac OS X)',platform:'iPhone',touch:5},
 {native:'ios',ua:'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15)',platform:'MacIntel',touch:5},
 {native:'android',ua:'Mozilla/5.0 (Linux; Android 15)',platform:'Linux armv8',touch:5},
 {native:'windows',ua:'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',platform:'Win32',touch:0},
 {native:null,ua:'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15)',platform:'MacIntel',touch:0}
];
(async()=>{
 let cases=0;
 for(const lang of ['ru','en','lv'])for(const device of devices)for(const target of ['ios','android','windows']){
  const dom=new JSDOM(html,{runScripts:'outside-only',url:'https://vpn.tolf.is/'}),w=dom.window,d=w.document;
  Object.defineProperties(w.navigator,{userAgent:{value:device.ua},platform:{value:device.platform},maxTouchPoints:{value:device.touch},clipboard:{value:{writeText:async value=>{w.copied=value}}}});
  d.documentElement.lang=lang;w.currentPlatform=target;let protocol='anyconnect';w.getVpnTransport=()=>protocol;
  w.eval(source);await new Promise(setImmediate);
  const host=d.getElementById('ciscoClientInstall'),cross=device.native!==target;
  assert.equal(host.querySelectorAll('a.button-link').length,cross?0:1);
  assert.equal(host.querySelectorAll('.cisco-copy-link').length,cross?1:0);
  assert.equal(host.querySelectorAll('p').length,0,'No redundant confirmation notice');
  let url=cross?host.querySelector('.cisco-install-link input').value:host.querySelector('a').href;
  assert.ok(url.startsWith(target==='ios'?'https://apps.apple.com/':target==='android'?'https://play.google.com/':'https://www.infradead.org/'));
  if(cross){
   const input=host.querySelector('.cisco-install-link input');assert.equal(input.readOnly,true);
   host.querySelector('.cisco-copy-link').click();await new Promise(setImmediate);
   assert.equal(w.copied,url);assert.ok(host.querySelector('[role="status"]').textContent);
   w.navigator.clipboard.writeText=async()=>{throw new Error('Denied')};
   host.querySelector('.cisco-copy-link').click();await new Promise(setImmediate);
   assert.equal(input.selectionEnd,input.value.length,'Manual-copy fallback selects the URL');
  }
  const checkbox=host.querySelector('[type="checkbox"]');
  assert.equal(checkbox.checked,false);
  checkbox.checked=true;checkbox.dispatchEvent(new w.Event('change'));
  assert.equal(w.isCiscoClientConfirmed(target),true);
  protocol='ikev2';w.currentPlatform='android';w.dispatchEvent(new w.Event('vpntransportchange'));
  const strongHost=d.getElementById('ciscoClientInstall');
  assert.equal(strongHost.querySelector('[type="checkbox"]').checked,false);
  const strongUrl=strongHost.querySelector('.cisco-install-link input')?.value||strongHost.querySelector('a')?.href;
  assert.ok(strongUrl.includes('org.strongswan.android'));
  assert.equal(strongHost.querySelectorAll('a.button-link').length,device.native==='android'?1:0);
  dom.window.close();cases++;
 }
 assert.ok(!fs.readFileSync('js/anyconnect-access.js','utf8').includes('root.append(element("p",gateCopy.blocked'));
 console.log(cases+' client installation cases passed, plus strongSwan switching and copy-failure fallback');
})().catch(e=>{console.error(e);process.exitCode=1});
