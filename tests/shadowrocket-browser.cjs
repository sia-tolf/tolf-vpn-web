const {chromium}=require('playwright');
const http=require('node:http'),fs=require('node:fs'),fsp=require('node:fs/promises'),path=require('node:path'),assert=require('node:assert/strict');
(async()=>{
 const root=process.cwd();
 const server=http.createServer(async(req,res)=>{
  try{
   const pathname=decodeURIComponent(new URL(req.url,'http://localhost').pathname);
   const file=path.resolve(root,'.'+(pathname.endsWith('/')?pathname+'index.html':pathname));
   if(!file.startsWith(root+path.sep)){res.writeHead(403).end();return;}
   const mime={'.html':'text/html','.js':'application/javascript','.css':'text/css','.svg':'image/svg+xml','.png':'image/png'}[path.extname(file)]||'application/octet-stream';
   const content=await fsp.readFile(file);res.writeHead(200,{'Content-Type':mime});res.end(content);
  }catch{res.writeHead(404).end();}
 });
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
 const origin='http://127.0.0.1:'+server.address().port;
 const browser=await chromium.launch({headless:true});
 try{
  for(const [width,lang,colorScheme] of [[320,'ru','light'],[390,'lv','light'],[1024,'en','light'],[390,'ru','dark']]){
   const context=await browser.newContext({viewport:{width,height:1000},colorScheme,userAgent:'Mozilla/5.0 (iPhone; CPU iPhone OS 26_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148 Safari/604.1'});
   await context.addInitScript(lang=>{localStorage.setItem('tolfLanguage',lang);Object.defineProperties(navigator,{platform:{get:()=> 'iPhone'},maxTouchPoints:{get:()=>5}});},lang);
   const page=await context.newPage(),errors=[],unknown=new Set();let login=null;
   page.on('pageerror',error=>errors.push(error.message));
   await page.route('**/*',async route=>{
    const req=route.request(),url=new URL(req.url());
    if(url.origin===origin)return route.continue();
    if(url.origin!=='https://api.tolf.is')return route.abort();
    const headers={'Access-Control-Allow-Origin':origin,'Access-Control-Allow-Credentials':'true','Access-Control-Allow-Methods':'GET, POST, OPTIONS','Access-Control-Allow-Headers':'Content-Type, Accept'};
    if(req.method()==='OPTIONS')return route.fulfill({status:204,headers});
    let payload={};try{payload=req.postDataJSON()||{};}catch{}let data,status=200;
    switch(url.pathname){
     case '/me':data={authenticated:true,userId:'test-only-account',allowedServers:['riga','moscow','us'],vpn:{configured:true,username:'test-vpn',server:'riga'}};break;
     case '/quick-setup/capabilities':data={version:1};break;
     case '/oc/access/capabilities':data={issuance:true,ingresses:[{id:'moscow',host:'oc.tolf.is:4443'},{id:'riga',host:'oc-riga.tolf.is:443'},{id:'us',host:'oc-us-moscow.tolf.is:4443'}]};break;
     case '/oc/access/devices':data={devices:[]};break;
     case '/windows/capabilities':data={version:'1.0',servers:['riga','moscow','us'],certificatePackages:true,routingModes:{riga:['sr'],moscow:['','sr'],us:['sr']}};break;
     case '/windows/devices':data={devices:[]};break;
     case '/vpn/capabilities':data={mobileIkev2NewYork:true,servers:['riga','moscow','us']};break;
     case '/entry-point-recommendation':data={entryPoint:'moscow'};break;
     case '/password/capabilities':data={version:1,verifyAccountPassword:true,createOnly:true};break;
     case '/password/account':data={enabled:Boolean(login),username:login};break;
     case '/password/set':assert.equal(payload.createOnly,true);login=payload.username;data={username:login};break;
     case '/password/verify':assert.equal(payload.password,'Test_only_2026_Secret');data={username:login};break;
     default:unknown.add(url.pathname);status=404;data={detail:'test_endpoint_not_required'};
    }
    return route.fulfill({status,headers,contentType:'application/json',body:JSON.stringify(data)});
   });
   await page.goto(origin+'/',{waitUntil:'networkidle'});
   await page.waitForFunction(()=>window.tolfSetupMode&&window.tolfAccountState?.authenticated);
   assert.equal(await page.locator('#vpnProtocolDropdown').isVisible(),false,'No global protocol before mode selection');
   await page.locator('#manualSetupLink').click();
   await page.waitForFunction(()=>document.body.classList.contains('ios-manual-setup'));
   assert.equal(await page.locator('#vpnProtocolDropdown').isVisible(),false,'iOS manual uses client-specific protocols');
   await page.locator('#quickSetupLink').click();
   await page.locator('#quickModePanel').waitFor({state:'visible'});
   assert.equal(await page.locator('#vpnProtocolDropdown').isVisible(),true,'Can return to quick mode before selecting a protocol');
   assert.equal(await page.locator('#quickStartLink').getAttribute('aria-disabled'),'true');
   await page.locator('#vpnProtocolDropdown .vpn-dropdown-button').click();await page.locator('#vpnProtocolDropdown [data-value="ikev2"]').click();
   assert.equal(await page.locator('#quickStartLink').getAttribute('aria-disabled'),'false');
   const selected=await page.locator('#quickSetupLink').evaluate(el=>({fill:getComputedStyle(el).backgroundColor,color:getComputedStyle(el).color,radius:getComputedStyle(el).borderRadius}));
   assert.equal(selected.fill,colorScheme==='dark'?'rgb(181, 210, 255)':'rgb(23, 79, 158)');assert.equal(selected.radius,'7px');
   await page.screenshot({path:'/tmp/tolf-shadowrocket-quick-'+width+'-'+colorScheme+'.png',fullPage:true});
   await page.locator('#manualSetupLink').click();
   const order=await page.locator('[data-ios-client]').evaluateAll(elements=>elements.map(el=>el.dataset.iosClient));assert.deepEqual(order,['native','cisco','shadowrocket']);
   assert.equal(await page.locator('.ios-manual-client-symbol').count(),3);
   for(const [client,expected,other] of [['native','ikev2','anyconnect'],['cisco','anyconnect','ikev2']]){
    await page.locator('[data-ios-client-select="'+client+'"]').click();
    await page.locator('#quickSetupLink').click();await page.locator('#vpnProtocolDropdown .vpn-dropdown-button').click();await page.locator('#vpnProtocolDropdown [data-value="'+other+'"]').click();
    await page.locator('#manualSetupLink').click();assert.equal(await page.evaluate(()=>window.getVpnTransport()),expected);
    assert.equal(await page.locator('#iosManualBody-'+client).isVisible(),true);
    await page.locator('#quickSetupLink').click();assert.equal(await page.evaluate(()=>window.getVpnTransport()),other);
    await page.locator('#manualSetupLink').click();
   }
   await page.locator('[data-ios-client-select="shadowrocket"]').click();
   await page.locator('#srNewUsername').waitFor({state:'visible'});
   await page.screenshot({path:'/tmp/tolf-shadowrocket-manual-'+width+'-'+colorScheme+'.png',fullPage:true});
   await page.locator('#srNewUsername').fill('test-user');await page.locator('#srNewPassword').fill('Test_only_2026_Secret');await page.locator('#srRepeatPassword').fill('Test_only_2026_Secret');
   await page.locator('#srAccountForm button[type="submit"]').click();await page.locator('#srSavedCredentials').waitFor({state:'visible'});
   assert.equal(await page.locator('#srPassword').inputValue(),'Test_only_2026_Secret');
   await page.locator('#srInstalled').check();await page.locator('#srPrepare').click();await page.locator('#srReady').waitFor({state:'visible'});
   const overflow=await page.evaluate(()=>({width:innerWidth,content:document.documentElement.scrollWidth}));assert(overflow.content<=overflow.width,JSON.stringify(overflow));
   const downloadPromise=page.waitForEvent('download');await page.locator('#srDownloadConfig').click();const download=await downloadPromise;
   assert.equal(download.suggestedFilename(),'TOLF_Shadowrocket.conf');const content=fs.readFileSync(await download.path(),'utf8');assert.equal((content.match(/password=Test_only_2026_Secret/g)||[]).length,3);
   for(const platform of ['Android','Windows']){
    await page.locator('#platform'+platform).click();
    assert.equal(await page.locator('#iosManualClients').isVisible(),false);
    assert.equal(await page.locator('#manualProtocolField #vpnProtocolDropdown').isVisible(),true);
    await page.locator('#quickSetupLink').click();assert.equal(await page.locator('#quickModePanel #vpnProtocolDropdown').isVisible(),true);
    await page.locator('#manualSetupLink').click();assert.equal(await page.locator('#manualProtocolField #vpnProtocolDropdown').isVisible(),true);
   }
   assert.deepEqual(errors,[],'Runtime errors; mocked optional endpoints: '+[...unknown].join(','));await context.close();
  }
  console.log('PASS: actual page scripts, independent mode switching, scoped protocols, approved button colors, client order, local downloads, Android/Windows, RU/LV/EN and light/dark at 320/390/1024px');
 }finally{await browser.close();await new Promise(resolve=>server.close(resolve));}
})().catch(error=>{console.error(error);process.exit(1);});
