const assert=require('node:assert/strict'),fs=require('node:fs'),{JSDOM}=require(process.env.TOLF_JSDOM||'/tmp/tolf-manual-dom-check/node_modules/jsdom');
(async()=>{
 for(const language of ['ru','en','lv']){
  const dom=new JSDOM(fs.readFileSync('billing/index.html','utf8'),{url:'https://vpn.tolf.is/billing/?lang='+language,runScripts:'outside-only'}),w=dom.window,d=w.document;
  const methods={methods:['cardPayments','paymentInitiation','applePay','googlePay'],billingCountries:['LV','EE','LT'],banks:{LV:[{code:'TEST','name':'Test bank'}]}};
  const balanceBytes=language==='ru'?200e9:language==='lv'?0:200.123456e9;
  const remainingBytes=language==='ru'?175e9:language==='lv'?0:175.987654e9;
  const postRequests=[],fetchUrls=[];let documentIssued=false;
  w.URL.createObjectURL=()=>"blob:test";w.URL.revokeObjectURL=()=>{};w.HTMLAnchorElement.prototype.click=function(){};
  w.fetch=async(url,options)=>{fetchUrls.push(url);if(url.endsWith('/billing-document')){postRequests.push(JSON.parse(options.body));documentIssued=true;return {ok:true,json:async()=>({number:'TOLF-SB-2026-000002'})};}return {ok:true,blob:async()=>new w.Blob(['%PDF-test']),json:async()=>url.endsWith('/capabilities')?{mode:'sandbox',enabled:true,termsVersion:'2026-10-21',accountingExport:true}:url.endsWith('/methods')?methods:{testBalanceBytes:balanceBytes,orders:[{reference:'TOLF-SB-test-immutable',status:'PAID',gb:200,amount:9,createdAt:1792656000,remainingBytes,billingDocumentNumber:documentIssued?'TOLF-SB-2026-000002':null,documents:[{number:'TOLF-SB-2026-000001',kind:'purchase'}]}]}};};
  w.eval(fs.readFileSync('billing/page.js','utf8'));w.eval(fs.readFileSync('billing/sandbox.js','utf8'));
  await new Promise(resolve=>setImmediate(resolve));
  assert.ok(d.querySelector('.preview-note').textContent.includes(language==='ru'?'Тестовый':language==='lv'?'testa':'test'));
  assert.ok(d.querySelector('.balance-value').textContent.includes((balanceBytes/1e9).toLocaleString(language,{minimumFractionDigits:3,maximumFractionDigits:3})));
  assert.ok(d.querySelector('.sandbox-order-description').textContent.includes((remainingBytes/1e9).toLocaleString(language,{minimumFractionDigits:3,maximumFractionDigits:3})));
  assert.equal(d.getElementById('checkoutButton').disabled,true);
  for(const id of ['sandboxTerms','sandboxEarly']){d.getElementById(id).checked=true;d.getElementById(id).dispatchEvent(new w.Event('change'));}
  assert.equal(d.getElementById('checkoutButton').disabled,false);
  assert.equal(d.querySelectorAll('.sandbox-history-actions').length,1);
  const invoiceActions=d.querySelector('.sandbox-history-actions');
  assert.equal(invoiceActions.children.length,2);
  assert.ok(!invoiceActions.textContent.includes('PDF'));
  assert.ok(d.querySelector('.traffic-whole'));
  assert.equal(d.querySelector('.traffic-fraction').textContent,(balanceBytes/1e9).toLocaleString(language,{minimumFractionDigits:3,maximumFractionDigits:3}).match(/[.,][0-9]{3}$/)[0]);
  assert.equal(d.querySelectorAll('.sandbox-document:not(.post-document-request)').length,1);
  assert.ok(d.getElementById('billingExports'));
  assert.equal(d.querySelectorAll('#billingExportLinks button').length,8);
  d.getElementById('billingExportMonth').value='2026-09';
  d.getElementById('billingExportMonth').dispatchEvent(new w.Event('change'));
  for(const [index,kind] of ['purchases','movements','balances','fees'].entries()){
   const group=d.querySelectorAll('.billing-export-group')[index],buttons=group.querySelectorAll('button');
   assert.equal(buttons[0].textContent,'PDF');assert.equal(buttons[1].textContent,'CSV');
   for(const button of buttons)button.click();
   await new Promise(resolve=>setImmediate(resolve));
   assert.ok(fetchUrls.some(url=>url.endsWith('/export.pdf?month=2026-09&kind='+kind+'&locale='+language)));
   assert.ok(fetchUrls.some(url=>url.endsWith('/export.csv?month=2026-09&kind='+kind)));
  }
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
  assert.ok(d.querySelector('.balance-value').textContent.includes((balanceBytes/1e9).toLocaleString('lv',{minimumFractionDigits:3,maximumFractionDigits:3})));
  assert.equal([...d.querySelectorAll('[name="payment"]')].filter(e=>!e.closest('label').hidden).length,4);
  dom.window.close();
 }
 console.log('Sandbox UI: 3 languages, consent gate, bank selection, test balance, trial disabled');
})().catch(e=>{console.error(e);process.exitCode=1});