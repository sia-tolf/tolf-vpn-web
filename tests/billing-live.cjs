const assert=require('node:assert/strict'),fs=require('node:fs');
const {JSDOM,VirtualConsole}=require(process.env.TOLF_JSDOM||'jsdom');
(async()=>{
 for(const lang of ['ru','en','lv']){
  const console=new VirtualConsole();console.on('jsdomError',e=>{if(!e.message.includes('Not implemented: navigation'))throw e;});
  const dom=new JSDOM(fs.readFileSync('billing/index.html','utf8'),{runScripts:'outside-only',virtualConsole:console,url:'https://vpn.tolf.is/billing/?lang='+lang});
  const w=dom.window,d=w.document,calls=[],orders=[];
  w.fetch=async (url,options)=>{calls.push(url);let data;
   if(url.endsWith('/billing/live/capabilities'))data={mode:'live',enabled:true,termsVersion:'2026-10-21',accountingExport:false};
   else if(url.endsWith('/billing/live/methods'))data={methods:['cardPayments','paymentInitiation'],banks:{LV:[{name:'Bank',code:'bank'}]},billingCountries:['LV']};
   else if(url.endsWith('/billing/live/account'))data={mode:'live',balanceBytes:200e9,orders:[]};
   else if(url.endsWith('/billing/live/orders')){orders.push(JSON.parse(options.body));data={reference:'TOLF-LIVE-test',paymentUrl:'https://stargate.montonio.com/test'};}
   else throw Error('Unexpected URL '+url);
   return {ok:true,json:async()=>data};
  };
  w.eval(fs.readFileSync('billing/page.js','utf8'));w.eval(fs.readFileSync('billing/sandbox.js','utf8'));
  await new Promise(r=>setTimeout(r,30));
  assert.equal(calls.length,3);assert.ok(calls.every(x=>x.includes('/billing/live/')));
  assert.equal(d.getElementById('checkoutButton').disabled,true);
  assert.equal(d.querySelector('.draft-price').hidden,true);
  assert.equal(d.getElementById('billingBuyer').hidden,true);
  assert.ok(!/sandbox|test mode|тестов|testa/i.test(d.querySelector('.preview-note').textContent));
  for(const id of ['sandboxTerms','sandboxEarly']){d.getElementById(id).checked=true;d.getElementById(id).dispatchEvent(new w.Event('change'));}
  assert.equal(d.getElementById('checkoutButton').disabled,false);
  assert.deepEqual([...d.querySelectorAll('[name="payment"]')].map(x=>x.value),['card','bank']);
  assert.deepEqual([...d.querySelectorAll('.payment-brands>*')].map(x=>x.alt||x.querySelector('img')?.alt||x.textContent),['VISA','Mastercard','Apple Pay','Google Pay']);
 assert.equal(d.querySelector('[name="payment"][value="card"]').closest('label').querySelector('.payment-icon'),null);
  const bank=d.querySelector('[name="payment"][value="bank"]');bank.checked=true;bank.dispatchEvent(new w.Event('change'));
  assert.equal(d.getElementById('sandboxBankFields').hidden,false);
  assert.equal(d.getElementById('checkoutButton').disabled,true);
  const card=d.querySelector('[name="payment"][value="card"]');card.checked=true;card.dispatchEvent(new w.Event('change'));
  assert.equal(d.getElementById('sandboxBankFields').hidden,true);
  d.getElementById('checkoutButton').click();
  await new Promise(r=>setTimeout(r,30));
  assert.equal(orders.length,1);assert.equal(orders[0].method,'cardPayments');
  dom.window.close();
 }
 console.log('Live frontend: RU/EN/LV, production API, real-payment labels, consent gate, provider method availability');
})().catch(e=>{console.error(e);process.exit(1)});
