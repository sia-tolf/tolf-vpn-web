const {chromium} = require('playwright');
const assert=require('node:assert/strict');
const http=require('node:http');
const fs=require('node:fs');
const path=require('node:path');
const root=path.resolve(__dirname,'../..');
(async()=>{
 const server=http.createServer((req,res)=>{
  const name=path.join(root,new URL(req.url,'http://local').pathname);
  const file=name.endsWith('/')?name+'index.html':name;
  if(!file.startsWith(root)||!fs.existsSync(file)){res.statusCode=404;return res.end();}
  res.setHeader('Content-Type',file.endsWith('.js')?'application/javascript':file.endsWith('.css')?'text/css':'text/html');res.end(fs.readFileSync(file));
 });
 await new Promise(r=>server.listen(0,'127.0.0.1',r));
 const base='http://127.0.0.1:'+server.address().port;
 const browser=await chromium.launch({headless:true,args:['--no-sandbox']});
 try {
  for(const lang of ['ru','en','lv']) {
   const page=await browser.newPage({viewport:{width:390,height:844}});
   await page.addInitScript(()=>{window.copies=[];Object.defineProperty(navigator,'clipboard',{value:{writeText:async text=>window.copies.push(text)}});});
   const errors=[];page.on('pageerror',e=>errors.push(e.message));
   let session=false;const sent=[];
   await page.route('https://api.tolf.is/**',async route=>{
    const url=new URL(route.request().url());const data=route.request().postDataJSON();
    const headers={'Access-Control-Allow-Origin':base,'Access-Control-Allow-Credentials':'true','Access-Control-Allow-Headers':'content-type','Access-Control-Allow-Methods':'GET,POST'};
    if(route.request().method()==='OPTIONS')return route.fulfill({status:204,headers});
    let status=200,body={};
    if(url.pathname==='/password/capabilities')body={version:1};
    else if(url.pathname==='/me'){status=session?200:401;body={authenticated:session};}
    else if(url.pathname==='/password/register'||url.pathname==='/password/recover'){
     sent.push({path:url.pathname,data});session=true;body={username:data.username,recoveryCode:'TOLF-TEST-CODE-2345-6789-ABCD-EFGH'};
    }else if(url.pathname==='/password/login'){sent.push({path:url.pathname,data});body={};}
    else {status=404;}
    await route.fulfill({status,headers,contentType:'application/json',body:JSON.stringify(body)});
   });
   await page.goto(base+'/auth/?mode=signup&lang='+lang+'&next=quick');
   for(const target of ['en','lv','ru',lang]) {
    await page.locator('#lang'+target[0].toUpperCase()+target.slice(1)).click();
    assert.equal(await page.locator('html').getAttribute('lang'),target);
    assert.equal(await page.locator('#backHome').getAttribute('href'),'https://tolf.is/?lang='+target);
   }
   assert.equal(await page.locator('.auth-mark,.back-home').count(),0);
   assert.equal(await page.locator('#backHome .brand-emblem').count(),1);
   await page.locator('#signupPanel [data-auth-method="password"]').click();
   await page.locator('#signupUsername').fill('Lena-Work');
   await page.locator('[data-generate-password="signupPassword"]').click();
   const generated=await page.locator('#signupPassword').inputValue();assert.equal(generated.length,20);
   await page.locator('#signupPassword').fill('My edited password 1234');
   assert.equal(await page.locator('#signupPassword').getAttribute('autocomplete'),'new-password');
   await page.locator('#passwordSignupForm button[type=submit]').click();
   await page.locator('#newRecoveryCode').waitFor({state:'visible'});
   assert.equal(sent[0].data.username,'lena-work');assert.equal(sent[0].data.password,'My edited password 1234');
   assert.equal(await page.locator('#continueButton').isDisabled(),true);
   assert.equal(await page.locator('#signupPassword').inputValue(),'');
   const storage=await page.evaluate(()=>JSON.stringify({...localStorage,...sessionStorage}));
   assert(!storage.includes('My edited')&&!storage.includes('TEST-CODE'));
   const downloadPromise=page.waitForEvent('download');await page.locator('#downloadCredentialsButton').click();
   const download=await downloadPromise;const file=await download.path();
   const content=fs.readFileSync(file,'utf8');assert(content.includes('lena-work'));assert(content.includes('My edited password 1234'));assert(content.includes('TOLF-TEST'));
   await page.locator('#copyCredentialsButton').click();await page.locator('#copyCredentialsButton').click();
   const copies=await page.evaluate(()=>window.copies);assert.equal(copies.length,2);assert(copies[0].includes('My edited password 1234')&&copies[0].includes('TOLF-TEST'));
   await page.locator('#credentialsSaved').check();assert.equal(await page.locator('#continueButton').isEnabled(),true);
   const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>window.innerWidth);assert(!overflow);
   assert.deepEqual(errors,[]);
   if(lang==='ru')await page.screenshot({path:'/tmp/tolf-password-recovery.png',fullPage:true});
   // Reset can be reached even with an existing session.
   await page.goto(base+'/auth/?mode=recover&lang='+lang);
   await page.locator('#recoverPanel [data-auth-method="password"]').click();
   await page.locator('#recoveryCode').fill('TOLF-OLD-CODE');
   await page.locator('#resetUsername').fill('lena-work');await page.locator('#resetPassword').fill('replacement password 5678');
   await page.locator('#passwordResetForm button[type=submit]').click();
   await page.locator('#newRecoveryCode').waitFor({state:'visible'});
   assert.equal(sent.at(-1).path,'/password/recover');assert.equal(sent.at(-1).data.recoveryCode,'TOLF-OLD-CODE');
   await page.close();
  }
  const page=await browser.newPage({viewport:{width:390,height:844}});
  await page.route('https://api.tolf.is/**',r=>r.fulfill({status:404,body:'{}'}));
  await page.goto(base+'/auth/?mode=signup&lang=ru');
  await page.waitForTimeout(100);
  assert.equal(await page.locator('#signupPanel [data-method-selector]').isVisible(),false);
  assert.equal(await page.locator('#signupButton').isVisible(),true);
  await page.screenshot({path:'/tmp/tolf-passkey-signup.png',fullPage:true});
  console.log('PASS: EN/RU/LV registration, generation/edit, recovery, download, no secret storage, mobile layout, backend capability fallback');
 } finally {await browser.close();server.close();}
})().catch(e=>{console.error(e);process.exit(1);});
