const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
(async()=>{
 const browser=await chromium.launch({headless:true,args:['--no-sandbox']});
 try{
  for(const lang of ['en','ru','lv']){
   const page=await browser.newPage({viewport:{width:390,height:844}});
   const errors=[];page.on('pageerror',e=>errors.push(e.message));
   let enabled=false;const sent=[];
   await page.route('https://api.tolf.is/**',async r=>{
    if(r.request().method()==='OPTIONS')return r.fulfill({status:204,headers:{'Access-Control-Allow-Origin':'*','Access-Control-Allow-Headers':'content-type'}});
    const data=r.request().postDataJSON();
    if(data){sent.push(data);enabled=true;}
    await r.fulfill({json:data?{username:'lena-work'}:{enabled,username:enabled?'lena-work':null}});
   });
   const html=fs.readFileSync('account/index.html','utf8');
   const section=html.slice(html.indexOf('<section id="accountPasswordSection"'),html.indexOf('</section>',html.indexOf('<section id="accountPasswordSection"'))+10);
   await page.setContent('<html lang="'+lang+'"><style>.hidden{display:none!important}*{box-sizing:border-box}body{margin:16px}'+fs.readFileSync('css/account-password.css','utf8')+'</style>'+section+'</html>');
   await page.evaluate(()=>{window.copies=[];Object.defineProperty(navigator,'clipboard',{value:{writeText:async text=>window.copies.push(text)}});});
   await page.addScriptTag({content:fs.readFileSync('js/account-password.js','utf8')});
   await page.evaluate(()=>loadAccountPassword());
   await page.locator('#apOpen').click();await page.locator('#apNewLogin').fill('lena-work');
   await page.locator('#apGenerate').click();assert.equal((await page.locator('#apPassword').inputValue()).length,20);
   await page.locator('#apPassword').fill('Edited account password 123');
   await page.locator('#apForm button[type=submit]').click();
   await page.locator('#apResult').waitFor({state:'visible'});
   assert.equal(sent[0].password,'Edited account password 123');
   await page.locator('#apCopyDetails').click();await page.locator('#apCopyDetails').click();
   const copies=await page.evaluate(()=>window.copies);assert.equal(copies.length,2);assert(copies[0].includes('lena-work')&&copies[0].includes('Edited account password 123'));
   await page.evaluate(()=>{navigator.clipboard.writeText=async()=>{throw Error('denied')};document.execCommand=()=>false;});
   await page.locator('#apCopyDetails').click();assert.equal(await page.locator('#apCredentials').evaluate(e=>e.selectionEnd-e.selectionStart),(await page.locator('#apCredentials').inputValue()).length);
   assert(!await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth));
   await page.screenshot({path:'/tmp/tolf-password-account-'+lang+'.png',fullPage:true});
   await page.locator('#apSaved').click();assert.equal(await page.locator('#apCredentials').inputValue(),'');
   await page.evaluate(()=>loadAccountPassword());assert.equal(await page.locator('#apLogin').inputValue(),'lena-work');
   await page.locator('#apOpen').click();assert.equal(await page.locator('#apNewLoginGroup').isVisible(),false);
   assert.deepEqual(errors,[]);await page.close();
  }
  console.log('PASS account password: three languages, same-account setup, editable generation, repeated copy, manual fallback, secret dismissal, mobile width');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
