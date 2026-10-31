const {chromium}=require('playwright');
const fs=require('node:fs'),assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({headless:true});
 try {
  for(const [width,lang] of [[320,'ru'],[390,'lv'],[1024,'en']]) {
   const page=await browser.newPage({viewport:{width,height:1000}}),errors=[];
   page.on('pageerror',error=>errors.push(error.message));
   await page.route('**/*',route=>route.abort());
   await page.setContent(fs.readFileSync('index.html','utf8').replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi,'').replace(/<link\b[^>]*>/gi,''));
   for(const path of ['css/styles.css','css/anyconnect-access.css','css/compact-header.css','css/vpn-layout-20261004.css','tolf-buttons.20260917-3.css','css/ios-manual-clients.css'])await page.addStyleTag({path});
   await page.evaluate(lang=>{
    document.documentElement.lang=lang;window.currentPlatform='ios';window.lastVpnState={configured:true};window.tolfAccountState={authenticated:true,userId:'test-only-account'};
    window.recommendedEntryPoint='moscow';let transport='',login=null,ingress='moscow';
    window.getVpnTransport=()=>transport;window.setInstallLink=()=>{};window.setInterval=()=>0;
    window.ocAccess={ingress:()=>({id:ingress}),ingresses:()=>['moscow','riga','us'].map(id=>({id})),selectIngress:id=>{ingress=id;}};
    window.fetch=async()=>({ok:true,json:async()=>({version:1})});
    window.apiRequest=async(path,options={})=>{
     const body=options.body?JSON.parse(options.body):{};
     if(path==='/password/capabilities')return {verifyAccountPassword:true,createOnly:true};
     if(path==='/password/account')return {enabled:Boolean(login),username:login};
     if(path==='/password/set'){login=body.username;return {username:login};}
     if(path==='/password/verify')return {username:login};
     throw Error('Unexpected API '+path);
    };
    document.getElementById('vpnCard').classList.remove('hidden');document.getElementById('quickSetupCard').classList.remove('hidden');document.getElementById('loadingCard').classList.add('hidden');
    for(const name of ['Ikev2','AnyConnect'])document.getElementById('vpnTransport'+name).addEventListener('click',()=>{transport=name==='Ikev2'?'ikev2':'anyconnect';document.documentElement.dataset.vpnTransport=transport;window.dispatchEvent(new Event('vpntransportchange'));});
   },lang);
   for(const name of ['cisco-client-install','vpn-compact-selectors','quick-entry','shadowrocket-config','ios-manual-clients'])await page.addScriptTag({path:'js/'+name+'.js'});
   await page.locator('#manualSetupLink').click();
   await page.waitForFunction(()=>document.body.classList.contains('ios-manual-setup'));
   assert.equal(await page.locator('#myVpnProtocolField').isVisible(),false);
   const order=await page.locator('[data-ios-client]').evaluateAll(elements=>elements.map(el=>el.dataset.iosClient));assert.deepEqual(order,['native','cisco','shadowrocket']);
   await page.locator('[data-ios-client-select="shadowrocket"]').click();
   await page.locator('#srNewUsername').fill('test-user');await page.locator('#srNewPassword').fill('Test_only_2026_Secret');await page.locator('#srRepeatPassword').fill('Test_only_2026_Secret');
   await page.locator('#srAccountForm button[type="submit"]').click();await page.locator('#srSavedCredentials').waitFor({state:'visible'});
   assert.equal(await page.locator('#srPassword').inputValue(),'Test_only_2026_Secret');
   await page.locator('#srInstalled').check();await page.locator('#srPrepare').click();await page.locator('#srReady').waitFor({state:'visible'});
   const overflow=await page.evaluate(()=>({width:innerWidth,content:document.documentElement.scrollWidth}));assert(overflow.content<=overflow.width,JSON.stringify(overflow));
   const downloadPromise=page.waitForEvent('download');await page.locator('#srDownloadConfig').click();const download=await downloadPromise;
   assert.equal(download.suggestedFilename(),'TOLF_Shadowrocket.conf');const content=fs.readFileSync(await download.path(),'utf8');assert.equal((content.match(/password=Test_only_2026_Secret/g)||[]).length,3);
   await page.screenshot({path:'/tmp/tolf-shadowrocket-'+width+'.png',fullPage:true});
   await page.evaluate(()=>{window.currentPlatform='android';window.dispatchEvent(new Event('vpnplatformchange'));});
   assert.equal(await page.locator('#iosManualClients').isVisible(),false);assert.equal(await page.locator('#myVpnProtocolField').isVisible(),true);
   assert.deepEqual(errors,[]);await page.close();
  }
  console.log('PASS: browser setup and real local downloads at 320/390/1024px in RU/LV/EN, no horizontal overflow, Android selector restored');
 }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exit(1);});
