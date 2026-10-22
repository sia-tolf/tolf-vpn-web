
const assert=require('node:assert/strict'),fs=require('node:fs');
const {JSDOM}=require(process.env.TOLF_JSDOM||'/tmp/tolf-manual-dom-check/node_modules/jsdom');
const html=fs.readFileSync('billing/index.html','utf8'),page=fs.readFileSync('billing/page.js','utf8'),sandbox=fs.readFileSync('billing/sandbox.js','utf8');
async function open(url){
 const dom=new JSDOM(html,{url,runScripts:'outside-only'}),w=dom.window;
 let orderChecks=0;
 w.fetch=async(url,options)=>({ok:true,json:async()=>{
  if(url.endsWith('/capabilities'))return {enabled:true,mode:'sandbox',termsVersion:'2026-10-21',accountingExport:false};
  if(url.endsWith('/methods'))return {methods:['cardPayments'],banks:{},billingCountries:['LV','EE']};
  if(url.endsWith('/validate-return'))return {reference:'TOLF-SB-return-test'};
  if(url.endsWith('/orders/TOLF-SB-return-test')){orderChecks++;return {reference:'TOLF-SB-return-test',status:'PAID',package:'50'};}
  if(url.endsWith('/account'))return {testBalanceBytes:50e9,orders:[]};
  throw Error('Unexpected request '+url);
 }});
 w.eval(page);w.eval(sandbox);
 for(let i=0;i<6;i++)await new Promise(resolve=>setImmediate(resolve));
 return {dom,w,d:w.document,orderChecks};
}
(async()=>{
 for(const lang of ['ru','en','lv']){
  const first=await open('https://vpn.tolf.is/billing/?lang='+lang+'&sandboxOrder=TOLF-SB-return-test&order-token=signed-test-token');
  assert.equal(first.orderChecks,1);
  const url=new URL(first.w.location.href);
  assert.equal(url.searchParams.has('sandboxOrder'),false);
  assert.equal(url.searchParams.has('order-token'),false);
  assert.match(first.d.getElementById('checkoutAvailability').textContent,/подтверждён|confirmed|apstiprināts/);
  const cleanUrl=first.w.location.href;
  const selected=first.d.querySelector('[name="package"][value="200"]');selected.checked=true;selected.dispatchEvent(new first.w.Event('change'));
  assert.doesNotMatch(first.d.getElementById('checkoutAvailability').textContent,/подтверждён|confirmed|apstiprināts/);
  first.dom.window.close();
  const refreshed=await open(cleanUrl);
  assert.equal(refreshed.orderChecks,0);
  assert.doesNotMatch(refreshed.d.getElementById('checkoutAvailability').textContent,/подтверждён|confirmed|apstiprināts/);
  refreshed.dom.window.close();
 }
 console.log('Return status: first return shown once, URL consumed, refresh and package change clear success (3 languages)');
})().catch(e=>{console.error(e);process.exitCode=1;});
