const {chromium}=require('playwright');
const assert=require('node:assert/strict'),fs=require('node:fs'),http=require('node:http'),path=require('node:path');
(async()=>{
const root=process.cwd();const server=http.createServer((req,res)=>{let p=path.join(root,new URL(req.url,'http://local').pathname);if(p.endsWith('/'))p+='index.html';if(!p.startsWith(root)||!fs.existsSync(p)){res.statusCode=404;return res.end();}res.setHeader('Content-Type',p.endsWith('.js')?'application/javascript':p.endsWith('.css')?'text/css':'text/html');res.end(fs.readFileSync(p));});
await new Promise(r=>server.listen(0,'127.0.0.1',r));const base='http://127.0.0.1:'+server.address().port;
const browser=await chromium.launch({args:['--no-sandbox']});
try{
for(const width of [390,1024]){
 const page=await browser.newPage({viewport:{width,height:900}});const errors=[],posts=[];page.on('pageerror',e=>errors.push(e.message));
 await page.route('https://api.tolf.is/**',async r=>{const p=new URL(r.request().url()).pathname;const headers={'Access-Control-Allow-Origin':base,'Access-Control-Allow-Credentials':'true','Access-Control-Allow-Headers':'content-type'};if(r.request().method()==='OPTIONS')return r.fulfill({status:204,headers});if(r.request().method()==='POST')posts.push(p);
 const data=p==='/me'?{vpn:{configured:false},allowedServers:['riga','moscow']}:p==='/password/account'?{enabled:true,username:'test-user'}:p==='/passkeys'?{passkeys:[{id:'test-key',name:'Test iPad',createdAt:'2026-09-21T10:00:00Z'}]}:p==='/recovery/regenerate'?{recoveryCode:'TEST-ONLY-RECOVERY'}:p==='/vpn/invitations/status'?{protected:false}:{};
 await r.fulfill({headers,json:data});});
 await page.goto(base+'/account/?lang=ru');await page.locator('#apLogin').waitFor({state:'visible'});assert.equal(await page.locator('#apLogin').inputValue(),'test-user');assert.equal(await page.locator('.passkey-name').textContent(),'Test iPad');
 for(const lang of ['en','lv','ru']){await page.locator('#lang'+lang[0].toUpperCase()+lang.slice(1)).click();assert.equal(await page.locator('html').getAttribute('lang'),lang);assert((await page.locator('#vpnNavigation').getAttribute('href')).endsWith('lang='+lang));}
 assert.equal(await page.locator('#apMessage').isVisible(),false);assert(!await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth));
 page.once('dialog',d=>d.accept());await page.locator('#generateRecoveryButton').click();await page.locator('#accountRecoveryCode').waitFor({state:'visible'});assert.equal(await page.locator('#accountRecoveryCode').textContent(),'TEST-ONLY-RECOVERY');await page.locator('#savedAccountRecoveryButton').click();assert.equal(await page.locator('#accountRecoveryCode').textContent(),'');
 page.once('dialog',d=>d.dismiss());await page.locator('#deleteAccountButton').click();assert(!posts.includes('/account/delete'));
 await page.screenshot({path:'/tmp/tolf-password-account-page-'+width+'.png',fullPage:true});
 await page.goto(base+'/?lang=ru');await page.locator('#accountNavigation').waitFor({state:'visible'});assert.equal(await page.locator('#deleteAccountButton,#accountPasswordSection,#passkeysSection,#recoverySection').count(),0);
 await page.evaluate(()=>setVpnBusy(true));await page.evaluate(()=>setVpnBusy(false));
 assert.deepEqual(errors,[]);await page.close();
}
console.log('PASS account page: language, passkeys, password, recovery, deletion cancellation, VPN separation and action state, mobile and desktop');
}finally{await browser.close();server.close();}
})().catch(e=>{console.error(e);process.exit(1)});
