const assert=require('node:assert/strict'),fs=require('node:fs'),{JSDOM}=require(process.env.TOLF_JSDOM||'/tmp/tolf-manual-dom-check/node_modules/jsdom');
(async()=>{
 for(const language of ['ru','en','lv']){
  const dom=new JSDOM(fs.readFileSync('billing/index.html','utf8'),{url:'https://vpn.tolf.is/billing/?lang='+language,runScripts:'outside-only'}),w=dom.window,d=w.document;
  const methods={methods:['cardPayments','paymentInitiation','applePay','googlePay'],billingCountries:['LV','EE','LT'],banks:{LV:[{code:'TEST','name':'Test bank'}]}};
  const postRequests=[];let documentIssued=false;
  w.URL.createObjectURL=()=>"blob:test";w.URL.revokeObjectURL=()=>{};w.HTMLAnchorElement.prototype.click=function(){};
  w.fetch=async(url,options)=>{if(url.endsWith('/billing-document')){postRequests.push(JSON.parse(options.body));documentIssued=true;return {ok:true,json:async()=>({number:'TOLF-SB-2026-000002'})};}return {ok:true,blob:async()=>new w.Blob(['%PDF-test']),json:async()=>url.endsWith('/capabilities')?{mode:'sandbox',enabled:true,termsVersion:'2026-10-21',accountingExport:true}:url.endsWith('/methods')?methods:{testBalanceBytes:200e9,orders:[{reference:'TOLF-SB-test-immutable',status:'PAID',gb:200,amount:9,createdAt:1792656000,remainingBytes:175e9,billingDocumentNumber:documentIssued?'TOLF-SB-2026-000002':null,documents:[{number:'TOLF-SB-2026-000001',kind:'purchase'}]}]}};};
  w.eval(fs.readFileSync('billing/page.js','utf8'));w.eval(fs.readFileSync('billing/sandbox.js','utf8'));
  await new Promise(resolve=>setImmediate(resolve));
  assert.ok(d.querySelector('.preview-note').textContent.includes(language==='ru'?'Тестовый':language==='lv'?'testa':'test'));
  assert.equal(d.getElementById('checkoutButton').disabled,true);
  for(const id of ['sandboxTerms','sandboxEarly']){d.getElementById(id).checked=true;d.getElementById(id).dispatchEvent(new w.Event('change'));}
  assert.equal(d.getElementById('checkoutButton').disabled,false);
  assert.equal(d.querySelectorAll('.sandbox-document:not(.post-document-request)').length,1);
  assert.ok(d.getElementById('billingExports'));
  assert.equal(d.querySelectorAll('#billingExportLinks button').length,4);
  const buyer=d.getElementById('billingBuyerEnabled');buyer.checked=true;buyer.dispatchEvent(new w.Event('change',{bubbles:true}));
  assert.equal(d.getElementById('checkoutButton').disabled,true);
  for(const [id,value] of [['Name','SIA Test'],['Address','Rīga, LV-1001'],['Country','LV']]){
   d.getElementById('billingBuyer'+id).value=value;d.getElementById('billingBuyer'+id).dispatchEvent(new w.Event('input',{bubbles:true}));
  }
  assert.equal(d.getElementById('checkoutButton').disabled,false);
  d.getElementById('billingBuyerKind').value='company';d.getElementById('billingBuyerKind').dispatchEvent(new w.Event('change',{bubbles:true}));
  assert.equal(d.getElementById('checkoutButton').disabled,true);
  d.getElementById('billingBuyerRegistration').value='123';d.getElementById('billingBuyerRegistration').dispatchEvent(new w.Event('input',{bubbles:true}));
  assert.equal(d.getElementById('checkoutButton').disabled,false);
  buyer.checked=false;buyer.dispatchEvent(new w.Event('change',{bubbles:true}));
  assert.equal(d.getElementById('checkoutButton').disabled,false);
  const bank=d.querySelector('[name="payment"][value="bank"]');bank.checked=true;bank.dispatchEvent(new w.Event('change'));
  assert.equal(d.getElementById('checkoutButton').disabled,true);
  d.getElementById('sandboxBank').value='TEST';d.getElementById('sandboxBank').dispatchEvent(new w.Event('change'));
  assert.equal(d.getElementById('checkoutButton').disabled,false);
  d.querySelector('[data-lang="lv"]').click();
  assert.equal(new URL(d.getElementById('sandboxTermsLink').href).searchParams.get('lang'),'lv');
  assert.equal(d.getElementById('checkoutButton').disabled,false);
  const requestButton=d.querySelector('.post-document-request');assert.ok(requestButton);requestButton.click();
  assert.ok(d.getElementById('postDocumentDialog'));
  d.getElementById('postBuyerKind').value='company';d.getElementById('postBuyerKind').dispatchEvent(new w.Event('change'));
  for(const [id,value] of [['Name','SIA Post payment'],['Address','Rīga'],['Country','LV'],['Registration','456']])d.getElementById('postBuyer'+id).value=value;
  d.querySelector('#postDocumentDialog form').dispatchEvent(new w.Event('submit',{bubbles:true,cancelable:true}));
  await new Promise(resolve=>setImmediate(resolve));await new Promise(resolve=>setImmediate(resolve));
  assert.equal(postRequests.length,1);assert.equal(postRequests[0].buyer.name,'SIA Post payment');
  assert.equal(d.getElementById('postDocumentDialog'),null);
  assert.equal(d.querySelector('.post-document-request'),null);
  d.getElementById('selectTrial').click();
  assert.equal(d.getElementById('sandboxConsent').hidden,true);
  assert.equal(d.getElementById('checkoutButton').disabled,true);
  assert.ok(d.querySelector('.balance-value').textContent.includes('200'));
  assert.equal([...d.querySelectorAll('[name="payment"]')].filter(e=>!e.closest('label').hidden).length,4);
  dom.window.close();
 }
 console.log('Sandbox UI: 3 languages, consent gate, bank selection, test balance, trial disabled');
})().catch(e=>{console.error(e);process.exitCode=1});