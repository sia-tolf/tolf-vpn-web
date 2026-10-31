const assert=require('node:assert/strict');
const fixture=require('./ios-manual-clients.cjs');
(async()=>{
 for(const platform of ['ios','android','windows'])for(const language of ['ru','en','lv']){
  const f=await fixture(),{w,d,q}=f;
  Object.defineProperties(w.navigator,{userAgent:{value:platform==='ios'?'iPhone':platform==='android'?'Android':'Windows NT 10.0',configurable:true},platform:{value:platform==='ios'?'iPhone':platform==='android'?'Linux armv8':'Win32',configurable:true}});
  w.currentPlatform=platform;d.documentElement.lang=language;w.dispatchEvent(new w.Event('vpnplatformchange'));await f.settle();
  assert.equal(w.tolfSetupMode.get(),null);
  assert(q('quickModePanel').hidden);
  assert(q('vpnProtocolDropdown').closest('.vpn-protocol-field').hidden,'No protocol before choosing a mode');
  assert(q('vpnCard').closest('#quickSetupCard'),'Both modes share My VPN');
  for(let n=0;n<3;n++){
   q('manualSetupLink').click();await f.settle();
   assert.equal(w.tolfSetupMode.get(),'manual');assert(!q('manualSetupLink').disabled);
   assert.equal(q('quickSetupLink').getAttribute('aria-disabled'),'false');
   assert.equal(q('manualSetupLink').getAttribute('aria-selected'),'true');
   assert.equal(q('vpnProtocolDropdown').closest('.vpn-protocol-field').hidden,platform==='ios');
   if(platform!=='ios')assert(q('manualProtocolField').contains(q('vpnProtocolDropdown')));
   q('quickSetupLink').click();await f.settle();
   assert.equal(w.tolfSetupMode.get(),'quick');assert(!q('quickModePanel').hidden);
   assert(q('myVpnProtocolField').contains(q('vpnProtocolDropdown')));
   assert(!q('vpnProtocolDropdown').closest('.vpn-protocol-field').hidden);
   assert.equal(q('quickStartLink').getAttribute('aria-disabled'),'true');
  }
  let e=new w.MouseEvent('click',{bubbles:true,cancelable:true});q('quickStartLink').dispatchEvent(e);
  assert(e.defaultPrevented,'Starting setup still requires a protocol');
  q('vpnProtocolDropdown').querySelector('[data-value="anyconnect"]').click();await f.settle();
  assert.equal(q('quickStartLink').getAttribute('aria-disabled'),'false');
  let blocked;
  q('quickStartLink').addEventListener('click',event=>{blocked=event.defaultPrevented;event.preventDefault();});
  q('quickStartLink').dispatchEvent(new w.MouseEvent('click',{bubbles:true,cancelable:true}));
  assert.equal(blocked,false,'Native launch is allowed after choosing a protocol');
  assert.equal(new URL(q('quickStartLink').href).searchParams.get('protocol'),'anyconnect');
  assert.equal(new URL(q('quickStartLink').href).searchParams.get('platform'),platform);
  q('manualSetupLink').click();await f.settle();
  if(platform==='ios'){
   w.tolfIosManual.select('shadowrocket');await f.settle();
   assert(!q('srAccountForm').hidden);
   q('quickSetupLink').click();await f.settle();assert(!q('quickModePanel').hidden);
   q('manualSetupLink').click();await f.settle();assert(!q('srAccountForm').hidden);
  }
  q('vpnSetupModes').dispatchEvent(new w.KeyboardEvent('keydown',{key:'Home',bubbles:true,cancelable:true}));
  assert.equal(w.tolfSetupMode.get(),'quick');
  q('vpnSetupModes').dispatchEvent(new w.KeyboardEvent('keydown',{key:'End',bubbles:true,cancelable:true}));
  assert.equal(w.tolfSetupMode.get(),'manual');
  await f.settle();
  f.dom.window.close();
 }
 const f=await fixture();f.q('manualSetupLink').click();await f.settle();
 for(const [client,expected] of [['native','ikev2'],['cisco','anyconnect'],['shadowrocket','anyconnect']]){
  f.w.tolfIosManual.select(client);await f.settle();
  f.q('quickSetupLink').click();await f.settle();
  const other=expected==='ikev2'?'anyconnect':'ikev2';
  f.q('vpnProtocolDropdown').querySelector('[data-value="'+other+'"]').click();await f.settle();
  f.q('manualSetupLink').click();await f.settle();
  assert.equal(f.w.getVpnTransport(),expected,'The selected iOS client defines its manual protocol');
  f.q('quickSetupLink').click();await f.settle();
  assert.equal(f.w.getVpnTransport(),other,'Quick setup retains its own protocol');
  f.q('manualSetupLink').click();await f.settle();
 }
 await f.settle();f.dom.window.close();
 console.log('PASS: nine platform/language combinations, mode-first protocol scope, unrestricted repeated switching, independent protocol choices, fixed iOS client protocols, native target, retained Shadowrocket form and keyboard navigation');
})().catch(error=>{console.error(error);process.exit(1);});
