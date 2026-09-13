const {chromium}=require('playwright');
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'../..');
(async()=>{
 const browser=await chromium.launch({headless:true});
 const page=await browser.newPage({viewport:{width:390,height:844}});
 let logged=false, claimed=false; const errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 await page.route('**/*',async route=>{
  const url=new URL(route.request().url());
  if(url.hostname==='vpn.tolf.is') {
    const file=path.join(root,url.pathname==='/'?'index.html':url.pathname);
    if(fs.existsSync(file)) return route.fulfill({body:fs.readFileSync(file),contentType:file.endsWith('.js')?'application/javascript':file.endsWith('.css')?'text/css':'text/html'});
  }
  if(url.hostname==='api.tolf.is') {
    if(url.pathname==='/me') return route.fulfill({status:logged?200:401,json:logged?{vpn:{configured:claimed,username:'user0',server:'riga'},allowedServers:['riga','moscow']}:{detail:'Not authenticated'}});
    if(url.pathname==='/vpn/invitations/status') return route.fulfill({json:{imported:claimed,protected:claimed}});
    if(url.pathname==='/vpn/invitations/claim') {claimed=true;return route.fulfill({json:{status:'ok',username:'user0'}});}
    return route.fulfill({json:{passkeys:[],devices:[]}});
  }
  return route.abort();
 });
 await page.goto('https://vpn.tolf.is/#invite='+'x'.repeat(43));
 await page.waitForFunction(()=>!document.getElementById('signedOutCard').classList.contains('hidden'));
 assert.equal(new URL(page.url()).hash,'');
 assert.equal(await page.locator('#invitationCard').isVisible(),true);
 assert.equal(await page.locator('#invitationButton').isVisible(),false);
 logged=true;
 await page.evaluate(()=>loadAccount());
 assert.equal(await page.locator('#invitationButton').isVisible(),true);
 await page.locator('#invitationButton').click();
 await page.waitForFunction(()=>document.getElementById('invitationText').textContent.includes('user0'));
 assert.equal(await page.locator('#deleteVpnButton').isVisible(),false);
 assert.equal(await page.locator('#deleteAccountButton').isVisible(),false);
 for(const lang of ['ru','lv','en']) {
  await page.evaluate(lang=>setLanguage(lang),lang);
  assert.equal(await page.locator('#invitationText').textContent().then(x=>x.includes('user0')),true);
 }
 assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth),true);
 assert.deepEqual(errors,[]);
 await browser.close();
 console.log('PASS: invitation survives login, explicit claim, three languages, protected controls, narrow layout');
})().catch(e=>{console.error(e);process.exit(1)});
