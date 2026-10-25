
const assert=require('node:assert/strict'),fs=require('node:fs');
const {JSDOM}=require(process.env.TOLF_JSDOM||'jsdom');
for(const language of ['ru','en','lv']){
 const dom=new JSDOM(fs.readFileSync('billing/index.html','utf8'),{runScripts:'outside-only',url:'https://vpn.tolf.is/billing/?lang='+language});
 const w=dom.window,d=w.document;
 w.fetch=()=>{throw Error('Preview must not make requests or issue credit')};
 w.eval(fs.readFileSync('billing/page.js','utf8'));
 assert.equal(d.documentElement.lang,language);
 assert.deepEqual([...d.querySelectorAll('[name="package"]')].map(x=>x.value),['50','200','500']);
 for(const [gb,price] of [[50,3],[200,9],[500,20]]){
  const input=d.querySelector('[name="package"][value="'+gb+'"]');
  input.checked=true;input.dispatchEvent(new w.Event('change'));
  assert.ok(d.getElementById('checkoutButton').textContent.endsWith(price+' €'));
  assert.equal(d.querySelector('.checkout-action dl'),null);
  assert.equal(d.getElementById('paymentMethods').hidden,false);
 }
 d.getElementById('selectTrial').click();
 assert.ok(/1 (ГБ|GB)/.test(d.getElementById('checkoutButton').textContent));
 assert.equal(d.getElementById('selectTrial').getAttribute('aria-pressed'),'true');
 assert.equal(d.getElementById('paymentMethods').hidden,true);
 assert.equal(d.getElementById('checkoutButton').disabled,true);
 assert.ok([...d.querySelectorAll('[name="package"]')].every(x=>!x.checked));
 d.querySelector('[data-lang="en"]').click();
 assert.ok(/1 (ГБ|GB)/.test(d.getElementById('checkoutButton').textContent));
 assert.deepEqual([...d.querySelectorAll('[name="payment"]')].map(x=>x.value),['card','bank']);
 assert.deepEqual([...d.querySelectorAll('.payment-brands>span')].map(x=>x.textContent),['VISA','Mastercard','Apple Pay','Google Pay']);
 assert.equal(d.querySelector('[name="payment"][value="card"]').closest('label').querySelector('.payment-icon'),null);
 const input=d.querySelector('[name="package"][value="200"]');input.checked=true;input.dispatchEvent(new w.Event('change'));
 assert.equal(d.getElementById('checkoutButton').textContent,'Pay 9 €');
 assert.equal(d.getElementById('selectTrial').getAttribute('aria-pressed'),'false');
 assert.equal(d.getElementById('paymentMethods').hidden,false);
 assert.equal(d.querySelectorAll('input[name*="card"],input[name*="cvc"]').length,0);
 assert.equal(d.querySelectorAll('[data-text]').length,[...d.querySelectorAll('[data-text]')].filter(x=>x.textContent&&!x.textContent.includes('undefined')).length);
 dom.window.close();
}
console.log('Billing preview: 3 languages, paid/trial selection, totals, no payments or credits');
