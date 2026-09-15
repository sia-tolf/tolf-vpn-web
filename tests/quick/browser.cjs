const fs=require('fs'),path=require('path'),assert=require('assert/strict');
const {chromium}=require('playwright');
const root=path.resolve(__dirname,'../..');
(async()=>{
 const browser=await chromium.launch({headless:true});
 try{
  for(const locale of ['ru','en','lv']){
   const context=await browser.newContext({viewport:{width:390,height:844},locale,userAgent:'Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X)'});
   const page=await context.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
   let auth=false,saved=null,prepares=0,registeredName='';
   await page.route('https://api.tolf.is/**',r=>{
    const req=r.request(),url=new URL(req.url());const headers={'Access-Control-Allow-Origin':'https://vpn.tolf.is','Access-Control-Allow-Credentials':'true','Access-Control-Allow-Headers':'content-type','Access-Control-Allow-Methods':'GET,POST'};
    if(req.method()==='OPTIONS')return r.fulfill({status:204,headers});
    let body,status=200;
    switch(url.pathname){
     case '/quick-setup/capabilities':body={version:1};break;
     case '/entry-point-recommendation':body={entryPoint:'moscow'};break;
     case '/me':if(!auth){status=401;body={detail:'Login'};}else body={authenticated:true};break;
     case '/quick-setup/status':body={setup:saved};break;
     case '/passkey/register/begin':registeredName=req.postDataJSON().passkeyName;body={options:{},challengeId:'fake'};break;
     case '/passkey/register/finish':auth=true;body={recoveryCode:'RECOVERY-TEST'};break;
     case '/quick-setup/prepare':{
      const p=req.postDataJSON();assert.equal(p.platform,'ios');assert.equal(p.server,'moscow');assert.equal(p.language,locale);
      prepares++;saved={platform:p.platform,server:p.server,state:'ready'};
      body={profileUrl:'https://config.tolf.is/p/test'};break;
     }
     default:throw new Error('Unexpected API '+url.pathname);
    }
    return r.fulfill({status,headers,contentType:'application/json',body:JSON.stringify(body)});
   });
   await page.route('https://vpn.tolf.is/**',r=>{
    let file=new URL(r.request().url()).pathname.slice(1);if(file.endsWith('/'))file+='index.html';
    return r.fulfill({contentType:file.endsWith('.js')?'text/javascript':file.endsWith('.css')?'text/css':'text/html',body:fs.readFileSync(path.join(root,file))});
   });
   await page.goto('https://vpn.tolf.is/quick/');
   await page.locator('#register:not([disabled])').waitFor();
   assert.equal(await page.locator('#server').inputValue(),'moscow');
   assert.equal(await page.locator('#passkeyName').inputValue(),'iPhone');
   await page.locator('#passkeyName').fill(locale==='ru'?'iPad Александра':'Personal iPad');
   await page.evaluate(()=>{prepareRegistrationOptions=x=>x;serializeCredential=x=>x;Object.defineProperty(navigator,'credentials',{value:{create:async()=>({id:'fake'})},configurable:true});});
   await page.screenshot({path:`/tmp/tolf-quick-${locale}.png`,fullPage:true});
   await page.locator('#register').click();await page.locator('#code').waitFor();
   assert.equal(registeredName,locale==='ru'?'iPad Александра':'Personal iPad');
   assert.equal(await page.locator('#code').inputValue(),'RECOVERY-TEST');assert.equal(prepares,0);
   await page.locator('#saved').click();await page.locator('#download').waitFor();
   assert.equal(await page.locator('#download').getAttribute('href'),'https://config.tolf.is/p/test/download');
   assert.equal(await page.locator('#code').inputValue(),'');assert.equal(prepares,1);
   assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
   await page.screenshot({path:`/tmp/tolf-quick-ready-${locale}.png`,fullPage:true});
   await page.reload();await page.locator('#prepare:not([disabled])').waitFor();assert.equal(prepares,1);
   assert.equal(await page.locator('#change').isVisible(),false);
   await page.locator('#prepare').click();await page.locator('#download').waitFor();assert.equal(prepares,2);
   assert.deepEqual(errors,[]);await context.close();
  }
  // Unknown country and manual override; cross-device delivery is a personal link.
  const page=await browser.newPage({viewport:{width:900,height:900}});let sends=0;
  await page.route('https://api.tolf.is/**',r=>{
   const url=new URL(r.request().url());const headers={'Access-Control-Allow-Origin':'https://vpn.tolf.is','Access-Control-Allow-Credentials':'true','Access-Control-Allow-Headers':'content-type','Access-Control-Allow-Methods':'GET,POST'};
   if(r.request().method()==='OPTIONS')return r.fulfill({status:204,headers});
   let body={};
   if(url.pathname.endsWith('/capabilities'))body={version:1};
   if(url.pathname==='/me')body={authenticated:true};
   if(url.pathname.endsWith('/status'))body={setup:null};
   if(url.pathname.endsWith('/prepare')){sends++;assert.equal(r.request().postDataJSON().server,'moscow');assert.equal(r.request().postDataJSON().platform,'windows');body={profileUrl:'https://api.tolf.is/windows/p/test'};}
   return r.fulfill({headers,contentType:'application/json',body:JSON.stringify(body)});
  });
  await page.route('https://vpn.tolf.is/**',r=>{let f=new URL(r.request().url()).pathname.slice(1);if(f.endsWith('/'))f+='index.html';return r.fulfill({contentType:f.endsWith('.js')?'text/javascript':f.endsWith('.css')?'text/css':'text/html',body:fs.readFileSync(path.join(root,f))});});
  await page.goto('https://vpn.tolf.is/quick/');await page.locator('#prepare:not([disabled])').waitFor();
  assert.equal(await page.locator('#server').inputValue(),'riga');
  await page.locator('#change').click();await page.locator('#server').selectOption('moscow');await page.locator('#platform').selectOption('windows');
  await page.locator('#prepare').click();await page.locator('#profileLink').waitFor();assert.equal(sends,1);assert.equal(await page.locator('#download').isVisible(),false);
  assert.equal(await page.locator('#profileLink').inputValue(),'https://api.tolf.is/windows/p/test');
  await page.screenshot({path:'/tmp/tolf-quick-share.png',fullPage:true});
  console.log('PASS: three locales, registration, recovery, IP default/fallback, manual choice, resume, cross-device delivery');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
