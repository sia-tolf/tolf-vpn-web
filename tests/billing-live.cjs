const assert=require('node:assert/strict'),fs=require('node:fs');
const {JSDOM}=require(process.env.TOLF_JSDOM||'jsdom');
(async()=>{
 for(const lang of ['ru','en','lv']){
  const dom=new JSDOM(fs.readFileSync('billing/index.html','utf8'),{runScripts:'outside-only',url:'https://vpn.tolf.is/billing/?lang='+lang});
  const w=dom.window,d=w.document,calls=[];
  w.fetch=async url=>{calls.push(url);let data;
   if(url.endsWith('/billing/live/capabilities'))data={mode:'live',enabled:true,termsVersion:'2026-10-21',accountingExport:false};
   else if(url.endsWith('/billing/live/methods'))data={methods:['cardPayments','paymentInitiation'],banks:{LV:[{name:'Bank',code:'bank'}]},billingCountries:['LV']};
   else if(url.endsWith('/billing/live/account'))data={mode:'live',balanceBytes:200e9,orders:[]};
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
  assert.equal(d.getElementById('applePayMethod').hidden,true);
  dom.window.close();
 }
 console.log('Live frontend: RU/EN/LV, production API, real-payment labels, consent gate, provider method availability');
})().catch(e=>{console.error(e);process.exit(1)});
