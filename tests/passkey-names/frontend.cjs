const {chromium}=require('playwright');
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
(async()=>{
 const root=process.cwd(),browser=await chromium.launch();
 const page=await browser.newPage({viewport:{width:390,height:844}});
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 let label="TOLF Passkey #1", calls=[];
 await page.route('**/*', async route=>{
  const u=new URL(route.request().url());
  if(u.hostname==="vpn.tolf.is"){
   const file=path.join(root,u.pathname==='/'?'index.html':u.pathname);
   if(fs.existsSync(file)) return route.fulfill({body:fs.readFileSync(file),contentType:file.endsWith('.js')?'application/javascript':file.endsWith('.css')?'text/css':'text/html'});
  }
  if(u.hostname==="api.tolf.is"){
   if(u.pathname==="/me") return route.fulfill({status:401,json:{}});
   if(u.pathname==="/passkeys/naming") return route.fulfill({json:{version:1}});
   if(u.pathname==="/passkeys") return route.fulfill({json:{passkeys:[{id:"YQ",name:label}]}});
   if(u.pathname==="/passkeys/rename"){calls.push(route.request().postDataJSON());label="TOLF · "+calls.at(-1).passkeyName;return route.fulfill({json:{status:"ok"}});}
   return route.fulfill({json:{passkeys:[],devices:[]}});
  }
  return route.abort();
 });
 await page.goto('https://vpn.tolf.is/');
 await page.evaluate(()=>setLanguage('ru'));
 await page.locator('#registerPasskeyName').fill("Ирина — iPad");
 assert.equal(await page.evaluate(()=>checkedPasskeyName("registerPasskeyName")),"Ирина — iPad");
 await page.evaluate(()=>{invitationUsername="manual";document.getElementById("registerPasskeyName").dataset.edited="";renderInvitation();});
 assert.equal(await page.locator('#registerPasskeyName').inputValue(),"manual");
 await page.evaluate(()=>{document.getElementById("passkeyList").closest("section").classList.remove("hidden");renderPasskeys([{id:"YQ",name:"TOLF Passkey #1"}]);});
 assert.equal(await page.locator('.passkey-label-actions button').count(),1);
 assert.equal(await page.locator('#addPasskeyName').inputValue(),"");
 assert.equal(await page.locator('.passkey-rename-form').count(),0);
 assert.deepEqual(calls,[]);
 for(const lang of ['en','lv','ru']){
  await page.evaluate(l=>setLanguage(l),lang);
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
 }
 assert.deepEqual(errors,[]);
 await browser.close();
 console.log("PASS: name input, verified login default, no rename button, empty additional name, translations, mobile layout");
})().catch(e=>{console.error(e);process.exit(1)});
