const fs=require('fs'),path=require('path'),assert=require('assert/strict');
const {chromium}=require('playwright');
const root=path.resolve(__dirname,'../..');
(async()=>{
 const browser=await chromium.launch({headless:true});
 try{
 const page=await browser.newPage({viewport:{width:1100,height:900}});
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 const id='12345678-1234-1234-1234-123456789abc';let role=true;
 await page.route('https://api.tolf.is/admin/**',r=>{
   const url=new URL(r.request().url());let body;
   if(url.pathname.endsWith('/me'))body={isAdmin:role,number:1};
   else if(!role)return r.fulfill({status:403,contentType:'application/json',body:'{}'});
   else if(url.pathname==='/admin/users')body={users:[{id,number:1,createdAt:'2026-09-14T00:00:00Z',access:[{username:'test_user',server:'riga'}],windowsDevices:1,passkeys:1,isAdmin:true,protected:false}],total:1};
   else if(url.pathname==='/admin/users/'+id)body={id,number:1,passkeyNames:['iPad <script>'],devices:[{name:'Office <script>',username:'test_user',server:'riga',state:'active'}]};
   else if(url.pathname==='/admin/registry')body={records:[{number:2,username:'manual_user',accountId:null,provisioned:1,source:'manual'}],total:1};
   else body={events:[]};
   return r.fulfill({contentType:'application/json',headers:{'Access-Control-Allow-Origin':'https://vpn.tolf.is','Access-Control-Allow-Credentials':'true'},body:JSON.stringify(body)});
 });
 await page.route('https://vpn.tolf.is/**',r=>{const p=new URL(r.request().url()).pathname;const file=p==='/admin/'?'admin/index.html':p.slice(1);if(!fs.existsSync(path.join(root,file)))return r.fulfill({status:404,body:''});return r.fulfill({contentType:file.endsWith('.css')?'text/css':file.endsWith('.js')?'text/javascript':'text/html',body:fs.readFileSync(path.join(root,file),'utf8')});});
 await page.goto('https://vpn.tolf.is/admin/');
 await page.getByRole('button',{name:'Русский',exact:true}).click();
 await page.getByRole('button',{name:'Подробнее',exact:true}).click();
 await page.getByText('Office <script>',{exact:true}).waitFor();
 assert.equal(await page.locator('#detailContent script').count(),0);
 await page.screenshot({path:'/tmp/tolf-admin-preview.png',fullPage:true});
 await page.getByRole('button',{name:'Реестр VPN',exact:true}).click();
 await page.getByText('manual_user',{exact:true}).waitFor();
 role=false;await page.getByRole('button',{name:'Обновить',exact:true}).click();
 await page.getByText(/Номер вашего аккаунта: 1/).waitFor();
 assert.equal(await page.locator('#workspace').isVisible(),false);
 assert.equal(await page.locator('#results tr').count(),0);
 assert.deepEqual(errors,[]);
 console.log('PASS admin inventory, device details, literal rendering and role revocation');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
