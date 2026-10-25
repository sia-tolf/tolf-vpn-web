const fs=require('fs'),http=require('http'),path=require('path'),assert=require('assert/strict');
const {chromium}=require(process.env.TOLF_PLAYWRIGHT||'playwright');
const root=path.resolve(__dirname,'..');
(async()=>{
 const server=http.createServer((req,res)=>{let f=path.resolve(root,'.'+decodeURI(req.url.split('?')[0]));if(!f.startsWith(root+'/')){res.writeHead(403);return res.end();}if(fs.existsSync(f)&&fs.statSync(f).isDirectory())f+='/index.html';if(!fs.existsSync(f)){res.writeHead(404);return res.end();}res.setHeader('Content-Type',f.endsWith('.css')?'text/css':f.endsWith('.js')?'text/javascript':f.endsWith('.svg')?'image/svg+xml':f.endsWith('.png')?'image/png':'text/html');res.end(fs.readFileSync(f));});
 await new Promise(r=>server.listen(0,'127.0.0.1',r));
 const browser=await chromium.launch({headless:true,args:['--no-sandbox']});
 const settings={enabled:true,beneficiary:'TEST ONLY',bankName:'TEST BANK',iban:'LV80BANK0000435195001',bic:'BANKLV22',vatStatus:'non_registered',vatNumber:'',dueDays:7};
 const seller={name:'SIA Tolf',registration:'40203551237',address:'Test address',email:'test@example.invalid'};
 for(const width of [375,1280])for(const lang of ['ru','en','lv']){
 const p=await browser.newPage({viewport:{width,height:1100}});let errors=[],created=null,confirmed=null;let invoice={number:'TOLF-BT-2026-000001',reference:'TOLF-BANK-test',gb:375,amount:19.13,status:'PENDING',buyer:{name:'Test Company',kind:'company'},accountNumber:9,dueDate:'2026-11-01',createdAt:1792920000,paymentReference:'TOLF-BT-2026-000001',bank:settings,pdfUrl:'/billing/bank/invoices/TOLF-BT-2026-000001.pdf',receiptUrl:null};p.on('pageerror',e=>errors.push(e.message));
 await p.route('https://api.tolf.is/**',async r=>{const request=r.request(),u=new URL(request.url()),url=u.pathname;let data;
 if(url==='/billing/live/capabilities')data={mode:'live',enabled:true,termsVersion:'2026-10-21',pricingVersion:'volume-parabola-20261025-v1',accountingExport:false};
 else if(url==='/billing/live/methods')data={methods:['cardPayments','paymentInitiation'],banks:{LV:[{name:'Bank',code:'bank'}]},billingCountries:['LV']};
 else if(url==='/billing/live/account')data={mode:'live',balanceBytes:confirmed?375e9:0,orders:created?[{reference:invoice.reference,package:'375',gb:375,amount:19.13,status:invoice.status,createdAt:invoice.createdAt,method:'bankTransfer',bankInvoice:{number:invoice.number,paymentReference:invoice.number,pdfUrl:invoice.pdfUrl,receiptUrl:invoice.receiptUrl}}]:[]};
 else if(url==='/billing/bank/capabilities')data={admin:true,enabled:true,pricingVersion:'volume-parabola-20261025-v1',termsVersion:'2026-10-21',billingCountries:['LV','EE','US']};
 else if(url==='/billing/bank/invoices'&&request.method()==='POST'){created=request.postDataJSON();assert.equal(created.package,'375');assert.equal(created.buyer.kind,'company');data=invoice;}
 else if(url==='/billing/bank/admin/settings'){if(request.method()==='POST'){const v=request.postDataJSON();assert.equal(v.settings.iban,settings.iban);data={settings:v.settings,revision:3,seller};}else data={settings,revision:2,seller};}
 else if(url==='/billing/bank/admin/invoices')data={invoices:[invoice],total:1,offset:0};
 else if(url.endsWith('/confirm')){confirmed=request.postDataJSON();assert.equal(confirmed.amount,'19.13');assert.equal(confirmed.transactionId,'TEST-TX-1');assert.equal(confirmed.confirmReceived,true);invoice={...invoice,status:'PAID',receiptUrl:'/billing/bank/invoices/TOLF-BT-2026-000001/receipt.pdf'};data=invoice;}
 else if(url.endsWith('.pdf'))return r.fulfill({contentType:'application/pdf',body:Buffer.from('%PDF-1.7\n% test download fixture\n')});
 else throw Error('Unexpected API request '+url);
 return r.fulfill({contentType:'application/json',body:JSON.stringify(data)});
 });
 await p.goto('http://127.0.0.1:'+server.address().port+'/billing/?lang='+lang);
 await p.locator('#bankInvoiceButton').waitFor({state:'visible'});await p.locator('#volumeNumber').fill('375');await p.locator('#bankInvoiceButton').click();
 await p.locator('#bankBuyer-kind').selectOption('company');await p.locator('#bankBuyer-name').fill('Test Company');await p.locator('#bankBuyer-registration').fill('TEST123');await p.locator('#bankBuyer-country').selectOption('LV');await p.locator('#bankBuyer-address').fill('Test address 123');await p.locator('#bankInvoiceTerms').check();
 assert.equal(await p.locator('.bank-dialog').evaluate(e=>e.scrollWidth>e.clientWidth),false);
 if(lang==='ru')await p.locator('.bank-dialog').screenshot({path:'/var/tmp/tolf-layout-qa/bank-form-'+width+'.png'});
 await p.locator('#bankInvoiceCreate').click();await p.locator('.bank-reference').waitFor();assert(created);
 assert.equal(await p.locator('.bank-reference').textContent(),invoice.number);
 const dl=p.waitForEvent('download');await p.locator('.bank-dialog .primary').click();const download=await dl;assert.equal(download.suggestedFilename(),invoice.number+'.pdf');
 await p.keyboard.press('Escape');await p.locator('.bank-dialog').waitFor({state:'detached'});await p.locator('#sandboxHistory .sandbox-document').first().waitFor();assert.equal(await p.locator('#sandboxHistory .sandbox-document').count(),1);
 await p.goto('http://127.0.0.1:'+server.address().port+'/admin/bank-payments.html?lang='+lang);
 await p.locator('#bankAdminWorkspace').waitFor({state:'visible'});await p.locator('.bank-invoice-row').waitFor();
 await p.locator('#bankSettingsDetails summary').click();await p.locator('#bankSaveSettings').click();await p.waitForTimeout(50);
 await p.locator('.bank-invoice-actions .primary').click();await p.locator('.bank-dialog input[type="text"]').fill('TEST-TX-1');await p.locator('.bank-dialog input[type="checkbox"]').check();
 if(lang==='ru')await p.locator('.bank-dialog').screenshot({path:'/var/tmp/tolf-layout-qa/bank-confirm-'+width+'.png'});
 await p.locator('.bank-dialog button[type="submit"]').click();await p.locator('.bank-dialog').waitFor({state:'detached'});assert(confirmed);await p.locator('.bank-status.paid').waitFor();assert.equal(await p.locator('.bank-status.paid').count(),1);
 assert.equal(await p.locator('.bank-invoice-actions button').count(),2);assert.equal(await p.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);assert.deepEqual(errors,[]);
 console.log(width,lang,'PASS: buyer form, invoice download, history, admin settings, explicit confirmation and receipt');await p.close();
 }
 await browser.close();server.close();
})().catch(e=>{console.error(e);process.exit(1)});
