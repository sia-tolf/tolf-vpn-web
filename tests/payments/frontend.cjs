const assert=require('node:assert/strict'),fs=require('node:fs'),{JSDOM}=require(process.env.TOLF_JSDOM||'/tmp/tolf-manual-dom-check/node_modules/jsdom');
(async()=>{
 for(const language of ['ru','en','lv']){
  const dom=new JSDOM(fs.readFileSync('billing/index.html','utf8'),{url:'https://vpn.tolf.is/billing/?lang='+language,runScripts:'outside-only'}),w=dom.window,d=w.document;
  const methods={methods:['cardPayments','paymentInitiation','applePay','googlePay'],banks:{LV:[{code:'TEST','name':'Test bank'}]}};
  w.fetch=async(url,options)=>({ok:true,json:async()=>url.endsWith('/capabilities')?{mode:'sandbox',enabled:true,termsVersion:'2026-10-21'}:url.endsWith('/methods')?methods:{testBalanceBytes:200e9,orders:[]}});
  w.eval(fs.readFileSync('billing/page.js','utf8'));w.eval(fs.readFileSync('billing/sandbox.js','utf8'));
  await new Promise(resolve=>setImmediate(resolve));
  assert.ok(d.querySelector('.preview-note').textContent.includes(language==='ru'?'Тестовый':language==='lv'?'testa':'test'));
  assert.equal(d.getElementById('checkoutButton').disabled,true);
  for(const id of ['sandboxTerms','sandboxEarly']){d.getElementById(id).checked=true;d.getElementById(id).dispatchEvent(new w.Event('change'));}
  assert.equal(d.getElementById('checkoutButton').disabled,false);
  const bank=d.querySelector('[name="payment"][value="bank"]');bank.checked=true;bank.dispatchEvent(new w.Event('change'));
  assert.equal(d.getElementById('checkoutButton').disabled,true);
  d.getElementById('sandboxBank').value='TEST';d.getElementById('sandboxBank').dispatchEvent(new w.Event('change'));
  assert.equal(d.getElementById('checkoutButton').disabled,false);
  d.querySelector('[data-lang="lv"]').click();
  assert.equal(new URL(d.getElementById('sandboxTermsLink').href).searchParams.get('lang'),'lv');
  assert.equal(d.getElementById('checkoutButton').disabled,false);
  d.getElementById('selectTrial').click();
  assert.equal(d.getElementById('sandboxConsent').hidden,true);
  assert.equal(d.getElementById('checkoutButton').disabled,true);
  assert.ok(d.querySelector('.balance-value').textContent.includes('200'));
  assert.equal([...d.querySelectorAll('[name="payment"]')].filter(e=>!e.closest('label').hidden).length,4);
  dom.window.close();
 }
 console.log('Sandbox UI: 3 languages, consent gate, bank selection, test balance, trial disabled');
})().catch(e=>{console.error(e);process.exitCode=1});