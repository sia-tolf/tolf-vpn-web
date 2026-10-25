const assert=require('node:assert/strict'),fs=require('node:fs');
const {JSDOM}=require(process.env.TOLF_JSDOM||'jsdom');
for(const language of ['ru','en','lv']){
 const dom=new JSDOM(fs.readFileSync('billing/index.html','utf8'),{runScripts:'outside-only',url:'https://vpn.tolf.is/billing/?lang='+language});
 const w=dom.window,d=w.document;w.fetch=()=>{throw Error('No payment requests in preview')};
 w.eval(fs.readFileSync('billing/pricing-curve.js','utf8'));w.eval(fs.readFileSync('billing/page.js','utf8'));
 assert.equal(d.documentElement.lang,language);assert.equal(d.querySelectorAll('[name="package"]').length,0);assert.equal(d.getElementById('volumeNumber').min,'50');
 for(const [gb,cents] of [[50,294],[200,1104],[375,1913],[500,2400],[1000,3600]]){
  w.TolfBillingVolume.setVolume(gb);assert.equal(w.TolfBillingVolume.getVolume(),gb);
  assert.equal(d.getElementById('priceTotal').textContent.replace(/[^0-9]/g,''),String(cents));assert.ok(d.getElementById('checkoutButton').textContent.includes(d.getElementById('priceTotal').textContent));
 }
 const range=d.getElementById('volumeRange');
 range.value='5000';range.dispatchEvent(new w.Event('input'));assert.equal(w.TolfBillingVolume.getVolume(),224);
 range.dispatchEvent(new w.KeyboardEvent('keydown',{key:'ArrowRight'}));assert.equal(w.TolfBillingVolume.getVolume(),225);
 range.dispatchEvent(new w.KeyboardEvent('keydown',{key:'End'}));assert.equal(w.TolfBillingVolume.getVolume(),1000);
 range.dispatchEvent(new w.KeyboardEvent('keydown',{key:'ArrowLeft',shiftKey:true}));assert.equal(w.TolfBillingVolume.getVolume(),990);
 range.dispatchEvent(new w.KeyboardEvent('keydown',{key:'Home'}));assert.equal(w.TolfBillingVolume.getVolume(),50);
 assert.equal(range.getAttribute('aria-valuenow'),'50');
 assert.equal(d.querySelectorAll('.volume-tick').length,11);assert.equal(d.querySelectorAll('.volume-tick-major').length,4);
 const number=d.getElementById('volumeNumber');number.value='49';number.dispatchEvent(new w.Event('input'));assert.equal(number.getAttribute('aria-invalid'),'true');assert.equal(w.TolfBillingVolume.getVolume(),null);assert.equal(d.getElementById('checkoutButton').disabled,true);
 number.dispatchEvent(new w.Event('change'));assert.equal(number.value,'50');
 d.getElementById('selectTrial').click();assert.equal(w.TolfBillingVolume.isTrial(),true);assert.equal(d.getElementById('volumeWorkbench').hidden,true);assert.equal(d.getElementById('checkoutButton').disabled,true);
 d.getElementById('returnToPaid').click();assert.equal(w.TolfBillingVolume.getVolume(),50);assert.equal(d.getElementById('volumeWorkbench').hidden,false);
 assert.deepEqual([...d.querySelectorAll('[name="payment"]')].map(x=>x.value),['card','bank']);
 assert.equal(d.querySelectorAll('a[href^="mailto:"]').length,0);
 assert.equal(d.querySelectorAll('[data-text]').length,[...d.querySelectorAll('[data-text]')].filter(x=>x.textContent&&!x.textContent.includes('undefined')).length);
 dom.window.close();
}
console.log('Volume checkout: RU/EN/LV, custom prices, minimum validation, trial transitions, no mailto invoice.');
