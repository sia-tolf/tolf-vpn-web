// Browser regression for password reveal/rotate ownership UI; no real credentials.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {chromium}=require(require.resolve('playwright',{paths:[process.env.CODEX_PRIMARY_RUNTIME_NODE_MODULES||process.cwd()]}));
const root=path.resolve(__dirname,'..');
(async()=>{
 const browser=await chromium.launch({headless:true});
 try {
 const page=await browser.newPage({viewport:{width:820,height:1150}});
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 page.on('dialog',d=>d.accept());
 await page.route('https://tolf.test/**',r=>r.fulfill({body:'<!doctype html><html><body></body></html>',contentType:'text/html'}));
 await page.goto('https://tolf.test/');
 const html=fs.readFileSync(root+'/index.html','utf8').replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi,'').replace(/<link\b[^>]*>/gi,'');
 await page.setContent(html);await page.addStyleTag({content:fs.readFileSync(root+'/css/styles.css','utf8')});
 await page.evaluate(()=>{
   window.I18N={};window.currentLanguage='ru';window.currentPlatform='windows';window.lastVpnState={configured:true};window.vpnBusy=false;
   window.t=(key,args={})=>Object.entries(args).reduce((s,[k,v])=>s.replace('{'+k+'}',v),I18N.ru[key]||key);
   window.setVpnBusy=v=>window.vpnBusy=v;window.copyText=async text=>window.copied=text;
   window.requests=[];window.password='TEST_ONLY_PASSWORD';
   window.apiRequest=async(url,opt)=>{
     requests.push({url,...opt});
     if(url.endsWith('capabilities'))return {version:'1.0',servers:['riga','moscow'],passwordManagement:true};
     if(url==='/windows/devices')return {devices:[{id:'12345678-1234-1234-1234-123456789abc',name:'Рабочий компьютер',server:'moscow',state:'active',username:'user_TEST'}]};
     if(url.endsWith('/rotate'))password='TEST_ONLY_NEW_PASSWORD';
     return {password};
   };
 });
 await page.addScriptTag({content:fs.readFileSync(root+'/js/locales/ru.js','utf8')});
 await page.addScriptTag({content:fs.readFileSync(root+'/js/windows.js','utf8')});
 // Isolate the actual device list so unrelated logged-out account panels don't hide it.
 await page.evaluate(()=>{
  const list=document.getElementById('windowsDeviceList');document.body.append(list);list.style='max-width:740px;margin:24px auto';
 });
 await page.getByText('Рабочий компьютер',{exact:true}).click();
 await page.getByRole('button',{name:'Показать пароль',exact:true}).click();
 await page.waitForFunction(()=>document.querySelector('.windows-password-value')?.value==='TEST_ONLY_PASSWORD');
 assert.equal(await page.evaluate(()=>requests.filter(x=>x.url.endsWith('/profile')).length),0);
 await page.getByRole('button',{name:'Скопировать пароль',exact:true}).click();
 assert.equal(await page.evaluate(()=>copied),'TEST_ONLY_PASSWORD');
 await page.getByRole('button',{name:'Скрыть пароль',exact:true}).click();
 assert.equal(await page.locator('.windows-password-value').count(),0);
 await page.getByRole('button',{name:'Сменить пароль',exact:true}).click();
 await page.waitForFunction(()=>document.querySelector('.windows-password-value')?.value==='TEST_ONLY_NEW_PASSWORD');
 assert.equal(await page.evaluate(()=>requests.filter(x=>x.url.endsWith('/rotate')).length),1);
 await page.locator('#windowsDeviceList').screenshot({path:'/tmp/tolf-password-web.png'});
 await page.getByText('Рабочий компьютер',{exact:true}).click();
 await page.waitForFunction(()=>document.querySelector('.windows-password-value')===null);
 await page.getByText('Рабочий компьютер',{exact:true}).click();
 await page.getByRole('button',{name:'Показать пароль',exact:true}).click();
 await page.waitForFunction(()=>document.querySelector('.windows-password-value')?.value==='TEST_ONLY_NEW_PASSWORD');
 await page.evaluate(()=>clearWindowsDevices());
 assert.equal(await page.locator('.windows-password-value').count(),0);
 assert.deepEqual(errors,[]);
 console.log('PASS browser password show/copy/hide/rotate, collapse and logout; no setup link created');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
