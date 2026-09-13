const {chromium}=require('playwright');
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'../..');
(async()=>{
 const browser=await chromium.launch({headless:true});
 const page=await browser.newPage({viewport:{width:390,height:844}});
 let logged=false, claimed=false, activeUsername="user0"; const requests=[]; const errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 await page.route('**/*',async route=>{
  const url=new URL(route.request().url());
  if(url.hostname==='vpn.tolf.is') {
    const file=path.join(root,url.pathname==='/'?'index.html':url.pathname);
    if(fs.existsSync(file)) return route.fulfill({body:fs.readFileSync(file),contentType:file.endsWith('.js')?'application/javascript':file.endsWith('.css')?'text/css':'text/html'});
  }
  if(url.hostname==='api.tolf.is') {
    requests.push({url:route.request().url(),body:route.request().postData()});
    if(url.pathname==='/vpn/invitations/capabilities') return route.fulfill({json:{version:2,passwordLinking:true}});
    if(url.pathname==='/vpn/invitations/verify') {
      const body=route.request().postDataJSON();
      if(body.username==='user0') return route.fulfill({status:403,json:{detail:'admin_invitation_required'}});
      return route.fulfill({json:{status:'ok',token:'v'.repeat(43),username:'manual',expiresIn:900}});
    }
    if(url.pathname==='/me') return route.fulfill({status:logged?200:401,json:logged?{vpn:{configured:claimed,username:activeUsername,server:'riga'},allowedServers:['riga','moscow']}:{detail:'Not authenticated'}});
    if(url.pathname==='/vpn/invitations/status') return route.fulfill({json:{imported:claimed,protected:claimed&&activeUsername==='user0'}});
    if(url.pathname==='/vpn/invitations/claim') {claimed=true;return route.fulfill({json:{status:'ok',username:activeUsername}});}
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
 assert.equal(claimed,true);
 assert.equal(await page.locator('#invitationButton').isVisible(),false);
 await page.waitForFunction(()=>document.getElementById('invitationText').textContent.includes('user0'));
 assert.equal(await page.locator('#deleteVpnButton').isVisible(),false);
 assert.equal(await page.locator('#deleteAccountButton').isVisible(),false);
 for(const lang of ['ru','lv','en']) {
  await page.evaluate(lang=>setLanguage(lang),lang);
  assert.equal(await page.locator('#invitationText').textContent().then(x=>x.includes('user0')),true);
 }
 assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth),true);
 assert.deepEqual(errors,[]);

 logged=false; claimed=false; activeUsername='manual';
 await page.evaluate(()=>sessionStorage.clear());
 await page.goto('https://vpn.tolf.is/');
 await page.waitForFunction(()=>!document.getElementById('existingVpnCard').classList.contains('hidden'));
 await page.locator('#existingVpnDetails summary').click();
 await page.locator('#existingVpnUsername').fill('user0');
 await page.locator('#existingVpnPassword').fill('private-test-value');
 await page.locator('#existingVpnSubmit').click();
 await page.waitForFunction(()=>document.getElementById('existingVpnMessage').textContent.includes('administrator'));
 assert.equal(await page.locator('#existingVpnPassword').inputValue(),'');
 assert.equal(await page.locator('#invitationCard').isVisible(),false);
 await page.locator('#existingVpnUsername').fill('manual');
 await page.locator('#existingVpnPassword').fill('private-test-value');
 await page.locator('#existingVpnSubmit').click();
 await page.waitForFunction(()=>!document.getElementById('invitationCard').classList.contains('hidden'));
 assert.equal(claimed,false,'verification must not bind before Passkey login');
 assert.equal(await page.locator('#existingVpnPassword').inputValue(),'');
 assert.equal(await page.evaluate(()=>JSON.stringify(sessionStorage).includes('private-test-value')),false);
 assert.ok(!requests.some(r=>r.url.includes('private-test-value')));
 logged=true;
 await page.evaluate(()=>loadAccount());
 assert.equal(claimed,true);
 await page.waitForFunction(()=>document.getElementById('invitationText').textContent.includes('manual'));
 assert.equal(await page.locator('#existingVpnCard').isVisible(),false);
 assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth),true);
 assert.deepEqual(errors,[]);

 // A configured account must never be overwritten by a pending invitation.
 const before=requests.filter(r=>r.url.endsWith('/vpn/invitations/claim')).length;
 await page.evaluate(()=>{vpnInvitation='z'.repeat(43);invitationMessageKey='';});
 await page.evaluate(()=>loadAccount());
 assert.equal(requests.filter(r=>r.url.endsWith('/vpn/invitations/claim')).length,before);
 assert.equal(await page.locator('#invitationButton').isVisible(),false);
 // A failed request offers an explicit retry and is not retried on every render.
 await page.evaluate(()=>{
   invitationAccount={userId:'empty',vpn:{configured:false}};
   vpnInvitation='q'.repeat(43);invitationMessageKey='';invitationAttempt='';
   const original=apiRequest;
   window.claimAttempts=0;
   apiRequest=async (p,o)=>{if(p==='/vpn/invitations/claim'){window.claimAttempts++;throw new Error('temporary_failure');}return original(p,o);};
 });
 await page.evaluate(()=>updateInvitationAccount(invitationAccount));
 await page.evaluate(()=>updateInvitationAccount(invitationAccount));
 assert.equal(await page.evaluate(()=>window.claimAttempts),1);
 assert.equal(await page.locator('#invitationButton').isVisible(),true);
 await page.locator('#invitationButton').click();
 await page.waitForFunction(()=>window.claimAttempts===2);
 await browser.close();
 console.log('PASS: password verification, admin-only protected users, invitation survives login, automatic claim after login, conflict protection, retry, three languages, protected controls, narrow layout');
})().catch(e=>{console.error(e);process.exit(1)});
