const assert=require('node:assert/strict');
const fixture=require('./ios-manual-clients.cjs');
async function open(options={}) {
  const f=await fixture({existing:true,...options});
  f.d.documentElement.lang='ru';f.q('manualSetupLink').click();await f.settle();
  f.w.tolfIosManual.select('shadowrocket');await f.settle();return f;
}
function check(f,id,value) {f.q(id).checked=value;f.q(id).dispatchEvent(new f.w.Event('change'));}
(async()=>{
  for(const country of ['RU','LV','US',null]) {
    const f=await open({country});
    assert.equal(f.q('srDirectRuRecommended').hidden,country!=='RU');
    assert.equal(f.q('srDirectLvRecommended').hidden,country!=='LV');
    assert.equal(f.q('srDirectHint').hidden,!['RU','LV'].includes(country));
    assert.equal(f.q('srDirectRu').checked,false,'A recommendation is not consent');
    assert.equal(f.q('srDirectLv').checked,false,'No country is automatically bypassed');
    f.dom.window.close();
  }
  const f=await open({country:'LV',directPreferences:['RU']});
  assert(f.q('srDirectRu').checked&&!f.q('srDirectLv').checked,'Saved preference beats a changed IP suggestion');
  check(f,'srDirectLv',true);
  const stored=f.w.localStorage.getItem('tolfShadowrocketDirect:v1:account-one');
  assert.deepEqual(JSON.parse(stored),{version:1,countries:['RU','LV']});
  f.q('srPassword').value='Test_only_2026_Secret';check(f,'srInstalled',true);
  f.q('srConfigForm').dispatchEvent(new f.w.Event('submit',{cancelable:true}));await f.settle();
  f.q('srDownloadConfig').click();const content=await f.files[0].text();
  for(const suffix of ['ru','su','xn--p1ai','lv'])assert(content.includes('DOMAIN-SUFFIX,'+suffix+',DIRECT'));
  assert.equal(f.q('srDirectSummary').textContent,'Без VPN: .ru, .su, .рф, .lv');
  assert(!stored.includes('Secret')&&!stored.includes('existing-user'),'Persistence contains only non-secret country choices');
  f.w.dispatchEvent(new f.w.CustomEvent('tolf:account-state',{detail:{authenticated:true,userId:'account-two'}}));await f.settle();
  assert(!f.q('srDirectRu').checked&&!f.q('srDirectLv').checked,'Another account does not inherit consent');
  f.w.dispatchEvent(new f.w.CustomEvent('tolf:account-state',{detail:{authenticated:true,userId:'account-one'}}));await f.settle();
  assert(f.q('srDirectRu').checked&&f.q('srDirectLv').checked,'Returning to an account restores its selection');
  f.d.documentElement.lang='lv';await f.settle();
  assert.equal(f.q('srDirectLvRecommended').textContent,'Ieteicams');
  f.dom.window.close();
  const off=await open({country:'RU',directPreferences:[]});
  assert(!off.q('srDirectRu').checked,'An explicitly empty preference stays empty');off.dom.window.close();
  const blocked=await open({country:'RU',storageUnavailable:true});
  check(blocked,'srDirectRu',true);
  blocked.w.dispatchEvent(new blocked.w.CustomEvent('tolf:account-state',{detail:{authenticated:true,userId:'account-two'}}));await blocked.settle();
  blocked.w.dispatchEvent(new blocked.w.CustomEvent('tolf:account-state',{detail:{authenticated:true,userId:'account-one'}}));await blocked.settle();
  assert(blocked.q('srDirectRu').checked,'Storage failure keeps the in-page choice usable');blocked.dom.window.close();
  const late=await fixture({existing:true});let resolveCountry;
  const original=late.w.apiRequest;
  late.w.apiRequest=(path,...args)=>path==='/client-country'?new Promise(resolve=>{resolveCountry=resolve;}):original(path,...args);
  late.q('manualSetupLink').click();await late.settle();late.w.tolfIosManual.select('shadowrocket');await late.settle();
  check(late,'srDirectRu',true);resolveCountry({countryCode:'LV'});await late.settle();
  assert(late.q('srDirectRu').checked&&!late.q('srDirectLv').checked,'A delayed country hint cannot overwrite a manual selection');
  late.dom.window.close();
  console.log('PASS: RU/LV/unknown hints, explicit consent, saved false choices, account isolation, translated controls, downloads, storage failure and async country races');
})().catch(error=>{console.error(error);process.exit(1);});
