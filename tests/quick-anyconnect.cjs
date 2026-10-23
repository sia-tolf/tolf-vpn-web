const {withShares}=require('./ios-city-share-fixture.cjs');
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync('quick/quick-1.js','utf8'),strings=fs.readFileSync('quick/strings-1.js','utf8');
async function run(ua,platform,node,{tamper=false,missingNode=false,loseReply=false,buttons=false,handoff=false,clockSkew=0,expireGrant=false,mobileLinkFault=false,automaticOnly=false}={}){
 const map=new Map(),store=new Map(),posts=[],created=[],user='test-account',device='aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee';
 let lost=loseReply, recommendation=node;
 const makeElement=()=>({children:[],events:{},style:{},hidden:false,value:'',dataset:{},textContent:'',disabled:false,
   classList:{add(){},remove(){}},setAttribute(){},removeAttribute(){},
   append(...nodes){this.children.push(...nodes);},replaceChildren(...nodes){this.children=nodes;},
   addEventListener(name,fn){this.events[name]=fn;},remove(){},click(){return this.events.click?.();}});
 const element=id=>{if(!map.has(id))map.set(id,makeElement());return map.get(id);};
 let assigned,elapsed=0;const copied=[],downloadedBlobs=[],downloadLinks=[];
 class FixtureURL extends URL {static createObjectURL(blob){downloadedBlobs.push(blob);return 'blob:test-download';}static revokeObjectURL(){}}
 const descendants=node=>node.children.flatMap(n=>[n,...descendants(n)]);
 const host=node==='us'?'oc-us.tolf.is:4443':node==='riga'?'oc-riga.tolf.is:443':'oc.tolf.is:4443';
 const cert='https://api.tolf.is/oc/access/import/AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA.p12';
 const grant={deviceId:device,password:'TEST-ONLY-PASSWORD',expiresAt:new Date(Date.now()+7200000).toISOString(),certificateUrl:tamper?'https://example.invalid/test.p12':cert,username:'tolf-oc-aaaaaaaabbbbccccddddeeeeeeeeeeee',importUri:'anyconnect://import/?type=pkcs12&uri='+encodeURIComponent(cert),connections:[{id:node,host,connectionUri:'anyconnect://create/?host='+encodeURIComponent(host)+'&certcommonname=tolf-oc-aaaaaaaabbbbccccddddeeeeeeeeeeee'}]};
 if(mobileLinkFault){grant.importUri='https://example.invalid/';grant.connections[0].connectionUri='https://example.invalid/';}
 const BrowserDate=class extends Date {static now(){return Date.now()+clockSkew;}};
 const ctx={Blob,TextEncoder,btoa:value=>Buffer.from(value,'binary').toString('base64'),Date:BrowserDate,performance:{now:()=>elapsed},URL:FixtureURL,URLSearchParams,AbortSignal,location:{href:'https://vpn.tolf.is/quick/?protocol=anyconnect'+(node==='us'?'&ingress=us':'')},navigator:{userAgent:ua,platform:ua==='desktop-ipad'?'MacIntel':'',maxTouchPoints:ua==='desktop-ipad'?5:0,language:'ru',clipboard:{writeText:async value=>{copied.push(value);}}},crypto:{randomUUID:()=> 'test-request-id'},localStorage:{getItem:k=>map.get('storage:'+k),setItem(k,v){map.set('storage:'+k,v)}},sessionStorage:{getItem:k=>store.get(k),setItem:(k,v)=>store.set(k,v),removeItem:k=>store.delete(k)},document:{getElementById:element,documentElement:{lang:'ru'},querySelectorAll:()=>[],querySelector:()=>element('defaults'),body:{append(link){downloadLinks.push(link);}},createElement:()=>makeElement()},window:{addEventListener(){},location:{assign(url){assigned=url;}}},setTimeout:()=>0,clearTimeout(){},
 fetch:async(url,opt={})=>{
 let data;
 if(url.endsWith('/quick-setup/capabilities'))data={version:1};
 else if(url.endsWith('/entry-point-recommendation'))data={entryPoint:recommendation};
 else if(url.endsWith('/oc/access/capabilities'))data={issuance:true,ingresses:missingNode?[]:[{id:node,host}]};
 else if(url.endsWith('/me'))data={authenticated:true,userId:user};
 else if(url.endsWith('/oc/access/devices')&&opt.method==='POST'){
 const body=JSON.parse(opt.body);created.push(body);
 assert.equal(opt.credentials,'include');
 if(lost){lost=false;throw Error('Lost reply');}
 data={device:{id:device,state:'active',label:'Test device',username:'tolf-oc-aaaaaaaabbbbccccddddeeeeeeeeeeee'}};
 }else if(url.endsWith('/oc/access/devices'))data={devices:[{id:device,state:'active',label:'Test device',username:'tolf-oc-aaaaaaaabbbbccccddddeeeeeeeeeeee',expires_at:new Date(Date.now()+86400000).toISOString()}]};
 else if(url.includes('/policy?ingress=')){data={mode:'auto',applied:true};}
 else if(url.endsWith('/import')){assert.equal(opt.credentials,'include');data=grant;}
 else throw Error('Unexpected API '+url);
 posts.push(url);return {ok:true,json:async()=>data};
 }};
 vm.createContext(ctx);vm.runInContext(strings,ctx);vm.runInContext(withShares(fs.readFileSync('js/ios-vpn-buttons.js','utf8')),ctx);vm.runInContext(fs.readFileSync('js/openconnect-windows-setup.js','utf8'),ctx);vm.runInContext(source,ctx);
 for(let i=0;i<40;i++)await Promise.resolve();
 if(missingNode){assert.equal(element('prepare').disabled,true);assert.equal(created.length,0);return;}
 assert.equal(assigned,undefined,'quick setup must not redirect to My VPN for installation');
 assert.equal(element('quickClientInstall').hidden,false,'install on the current device within quick setup');
 assert.equal(element('quickClientConfirmed').checked,false);
 assert.equal(element('prepare').disabled,true,'client installation still gates preparation');
 await element('prepare').onclick();assert.equal(created.length,0,'no preparation before installation');
 element('quickClientConfirmed').checked=true;element('quickClientConfirmed').onchange();
 assert.equal(store.has('quickClientHandoff'),false);
 assert.equal(element('prepare').disabled,false);
 if(platform==='ios' && node!=='us'){
  const option=descendants(element('iosVpnButtons')).find(n=>n.type==='checkbox');
  assert.equal(option.checked,false);
  if(buttons){option.checked=true;option.events.change();}
 }
 await element('prepare').onclick();
 if(loseReply){await element('prepare').onclick();assert.equal(created[0].requestId,created[1].requestId);}
 if(platform==='ios'){
  if(buttons){
   assert.equal(assigned,undefined,'button setup must not skip straight to MobileConfig');
   assert.equal(element('preparePanel').hidden,false);
   assert.equal(element('prepare').hidden,true);
   for(const mode of ['control']){
    let nodes=descendants(element('iosVpnButtons'));
    assert(!nodes.some(n=>n.href?.includes('/ios.mobileconfig?')));
    const save=descendants(element('iosProfileSave')).find(n=>n.textContent==='Сохранить MobileConfig');
    assert(save.hidden && save.disabled,'save must not bypass shortcut steps');
    let confirm=nodes.find(n=>n.textContent==='Команда добавлена — продолжить');
    assert(confirm.disabled);
    confirm.events.click();
    assert(!descendants(element('iosVpnButtons')).some(n=>n.href?.includes('/ios.mobileconfig?')));
    const shortcut=nodes.find(n=>n.href?.includes('/shortcuts/'+(node==='moscow'?'a':'b').repeat(32)));
    assert(shortcut);
    if(mode==='on')assert(!nodes.some(n=>n.href?.includes('/shortcuts/off.shortcut')));
    shortcut.events.click();
    assert(!confirm.disabled);
    // Re-entering the page must restore the opened step, including after a reload.
    vm.runInContext(withShares(fs.readFileSync('js/ios-vpn-buttons.js','utf8')),ctx);
    const profile='https://api.tolf.is/oc/access/devices/'+device+'/ios.mobileconfig?ingress='+node;
    element('iosVpnButtons').replaceChildren(ctx.window.tolfIosButtons.create({
      checked:true,includeInstall:true,lang:'ru',url:profile,
      vpnName:'TOLF '+(node==='moscow'?'Moscow':'Riga')+' AnyConnect'
    }));
    nodes=descendants(element('iosVpnButtons'));
    confirm=nodes.find(n=>n.textContent==='Команда добавлена — продолжить');
    assert(!confirm.disabled,'opened step persists across reload');
    assert(nodes.some(n=>n.href===shortcut.href));
    confirm.events.click();
   }
   // Reload all controller code after recommendation changes while away in Shortcuts.
   recommendation=node==='moscow'?'riga':'moscow';
   // Both nodes remain available; the active setup must win over the new recommendation.
   const originalFetch=ctx.fetch;
   ctx.fetch=async(url,opt)=>url.endsWith('/oc/access/capabilities')?{ok:true,json:async()=>({issuance:true,ingresses:[{id:'moscow',host:'oc.tolf.is:4443'},{id:'riga',host:'oc-riga.tolf.is:443'}]})}:originalFetch(url,opt);
   vm.runInContext(withShares(fs.readFileSync('js/ios-vpn-buttons.js','utf8')),ctx);
   vm.runInContext(fs.readFileSync('js/openconnect-windows-setup.js','utf8'),ctx);vm.runInContext(source,ctx);
   for(let i=0;i<80;i++)await Promise.resolve();
   assert.equal(assigned,undefined,'reload stays in quick setup');
   assert.equal(element('quickClientInstall').hidden,false,'reload asks for confirmation within quick setup');
   assert.equal(element('quickClientConfirmed').checked,false,'reload resets client confirmation');
   assert.equal(element('prepare').disabled,true,'reload gates further setup');
   assert.equal(element('iosVpnButtons').hidden,true,'saved profile links cannot bypass confirmation');
   store.set('quickClientHandoff',JSON.stringify({platform,createdAt:BrowserDate.now()}));
   vm.runInContext(fs.readFileSync('js/openconnect-windows-setup.js','utf8'),ctx);vm.runInContext(source,ctx);
   for(let i=0;i<80;i++)await Promise.resolve();
   assert.equal(element('prepare').hidden,true,'reload restores prepared device');
   assert.equal(created.length,loseReply?2:1,'reload must not create another device');
   const nodes=descendants(element('iosVpnButtons'));
   assert.equal(nodes.find(n=>n.type==='checkbox').checked,true);
   const install=nodes.find(n=>n.href?.includes('/ios.mobileconfig?'));
   assert(install,'profile appears only after the TOLF confirmation');
   assert(!descendants(element('iosProfileSave')).find(n=>n.textContent==='Сохранить MobileConfig').hidden);
   assigned=install.href;
   const other=ctx.window.tolfIosButtons.create({checked:true,includeInstall:true,lang:'ru',
     url:'https://api.tolf.is/oc/access/devices/other/ios.mobileconfig?ingress='+node,
     vpnName:'TOLF '+(node==='moscow'?'Moscow':'Riga')+' AnyConnect'});
   assert(!descendants(other).some(n=>n.href?.includes('/ios.mobileconfig?')),
     'completion must not carry into a different device');
   const option=nodes.find(n=>n.type==='checkbox');
   option.checked=false;option.events.change();
   option.checked=true;option.events.change();
   assert(!descendants(element('iosVpnButtons')).some(n=>n.href?.includes('/ios.mobileconfig?')),
     'unchecking resets the bundle');

  }
  const url=new URL(assigned);
  assert.equal(url.pathname,'/oc/access/devices/'+device+'/ios.mobileconfig');
  assert.equal(url.searchParams.get('ingress'),node);
  assert.equal(url.searchParams.get('buttons'),buttons?'true':null);
  assert.equal(posts.filter(p=>p.endsWith('/import')).length,0);
  if(node==='us')assert.equal(element('iosVpnButtons').hidden,true);
  else assert(descendants(element('iosVpnButtons')).some(n=>n.textContent.includes('TOLF '+(node==='moscow'?'Moscow':'Riga'))));
  return;
 }
 if(automaticOnly){
  assert.equal(platform,'windows');
  assert.equal(element('ocWindowsAutoPanel').hidden,false);
  assert.equal(element('ocConnectionStep').hidden,true);
  assert.equal(element('ocCertificateStep').hidden,true);
  await element('ocWindowsAutoCopy').onclick();
  if(tamper){assert.equal(element('ocWindowsCommand').value,'');assert.equal(copied.length,0);return;}
  const command=element('ocWindowsCommand').value;
  assert.equal(copied.at(-1),command);
  const encoded=command.match(/-ConfigBase64 '([^']+)'$/)[1];
  const config=JSON.parse(Buffer.from(encoded,'base64').toString('utf8'));
  assert.equal(config.deviceId,device);assert.equal(config.gateway,'https://'+host);
  assert.equal(config.username,grant.username);assert.equal(config.password,grant.password);
  assert.equal(config.certificateUrl,cert);
  assert.equal(config.name,'TOLF '+({moscow:'Moscow',riga:'Riga',us:'New York'}[node])+' Auto');
  const crypto=require('node:crypto');
  const hash=crypto.createHash('sha256').update(fs.readFileSync('windows/openconnect-setup-v1.ps1')).digest('hex');
  assert(command.includes(hash));assert(!command.includes('ExecutionPolicy'));assert(!command.includes('RunAs'));
  assert.equal(element('ocWindowsCommandPanel').hidden,false);
  const imports=posts.filter(p=>p.endsWith('/import')).length;
  await element('ocWindowsAutoDownload').onclick();
  assert.equal(posts.filter(p=>p.endsWith('/import')).length,imports+1,'each setup download receives a fresh grant');
  assert.equal(downloadLinks.at(-1).download,'TOLF VPN Setup.cmd');
  const cmd=await downloadedBlobs.at(-1).text();
  assert(cmd.startsWith('@echo off\r\nsetlocal DisableDelayedExpansion\r\n'));
  assert(cmd.includes('where powershell.exe >nul 2>&1'));
  assert(command.includes("PSVersionTable.PSVersion -lt [version]'5.1'"));
  assert(command.includes('CurrentBuildNumber -lt 10240'));
  assert(command.includes("CurrentVersion'; if ("));
  assert(command.includes("SilentlyContinue; if ("));

  assert(command.includes('Release -lt 461808'));
  assert(command.indexOf('Release -lt 461808') < command.indexOf('DownloadData'));

  assert(cmd.includes('powershell.exe -NoLogo -NoProfile -Command "'+command+'"\r\n'));
  assert(cmd.includes('if errorlevel 1 (\r\n'));
  assert(!/[^\x00-\x7f]/.test(cmd),'CMD file is ASCII to avoid code-page corruption');
  assert(!cmd.includes('ExecutionPolicy'));assert(!cmd.includes('RunAs'));

  elapsed=2*3600000+1;await element('ocCopyName').onclick();
  assert.equal(element('ocWindowsCommandPanel').hidden,true);assert.equal(element('ocWindowsCommand').value,'');
  return;
 }
 assert.equal(element('ocWindowsFields').hidden,platform!=='windows');
 if(platform==='windows'){
  assert.equal(element('ocWindowsGateway').value,'https://'+host);
  assert(element('ocWindowsName').value.startsWith('TOLF '));
  assert(element('ocReturn').textContent.includes('New profile (advanced)'));
  assert(element('ocWindowsCertificate').textContent.includes('Local Certificate'));
  assert(element('ocWindowsCertificate').textContent.includes('User Certificate'));
  assert(element('ocEnable').textContent.includes('OpenConnect GUI'));
  await element('ocCopyName').onclick();await element('ocCopyGateway').onclick();
  assert.deepEqual(copied.slice(-2),[element('ocWindowsName').value,'https://'+host]);
 }
 assert.equal(element('ocRenew').disabled,true);
 assert.equal(element('ocAlreadyImported').disabled,true);
 await element('ocRenew').onclick();
 assert.equal(posts.filter(p=>p.endsWith('/import')).length,0);
 assert.equal(element('ocPassword').value,'');
 element('ocConfirmConnection').onclick();
 assert.equal(element('ocRenew').disabled,false);
 assert.equal(element('ocConnectionCompleted').hidden,false);
 await element('ocRenew').onclick();
 if(tamper||(mobileLinkFault&&platform!=='windows')){assert.equal(element('ocGrantPanel').hidden,true);assert.equal(element('ocPassword').value,'');return;}
 assert.equal(element('ocDelivery').hidden,false);assert.equal(element('ocServer').textContent,({riga:'Рига',moscow:'Москва',us:'Нью-Йорк'}[node])+': '+host);
 assert.equal(element('ocPassword').value,'TEST-ONLY-PASSWORD');
 if(expireGrant){elapsed=2*3600000+1;await element('ocCopyPassword').onclick();assert.equal(element('ocGrantPanel').hidden,true);assert.equal(element('ocPassword').value,'');return;}
 assert.equal(element('ocConnection').hidden,platform==='windows');assert.equal(element('ocImport').hidden,platform==='windows');
 assert.equal(element('change').hidden,true);assert.equal(element('choices').hidden,true);
 assert.equal(posts.some(p=>p.endsWith('/quick-setup/prepare')),false);
 const before=created.length;await element('ocRenew').onclick();assert.equal(created.length,before);
 element('ocAlreadyImported').onclick();assert.equal(element('ocPassword').value,'');assert.equal(element('ocGrantPanel').hidden,true);assert.equal(element('ocCertificateDone').hidden,false);
 element('ocAgain').onclick();assert.equal(element('ocRenew').disabled,true);assert.equal(element('ocAlreadyImported').disabled,true);assert.equal(element('ocConnectionCompleted').hidden,true);
 element('ocAlreadyImported').onclick();assert.equal(element('ocCertificateDone').hidden,true);
 element('ocConfirmConnection').onclick();element('ocAlreadyImported').onclick();
 assert.equal(element('ocCertificateDone').hidden,false);
 await element('ocRenew').onclick();assert.equal(created.length,before);assert.equal(element('ocGrantPanel').hidden,false);
}
(async()=>{for(const [ua,p]of[['iPhone','ios'],['desktop-ipad','ios'],['Android','android'],['Windows NT','windows']])await run(ua,p,'moscow',{handoff:true});await run('iPhone','ios','riga',{handoff:true,buttons:true});for(const [ua,p]of[['iPhone','ios'],['desktop-ipad','ios'],['Android','android'],['Windows NT','windows']])for(const node of ['riga','moscow','us'])await run(ua,p,node);await run('iPhone','ios','riga',{buttons:true});await run('iPhone','ios','moscow',{missingNode:true});await run('Android','android','moscow',{loseReply:true});await run('Windows NT','windows','moscow',{clockSkew:5*3600000});await run('Windows NT','windows','moscow',{clockSkew:-5*3600000});await run('Windows NT','windows','moscow',{expireGrant:true});await run('Windows NT','windows','moscow',{tamper:true});await run('Windows NT','windows','moscow',{mobileLinkFault:true});await run('Android','android','moscow',{mobileLinkFault:true});for(const node of ['moscow','riga','us'])await run('Windows NT','windows',node,{automaticOnly:true});await run('Windows NT','windows','moscow',{automaticOnly:true,clockSkew:5*3600000});await run('Windows NT','windows','moscow',{automaticOnly:true,tamper:true});console.log('PASS: AnyConnect device/node selection, reusable device, lost reply, certificate URL validation, node availability, mobile/Windows steps, blocked import, confirmation, reset and certificate reuse');})().catch(e=>{console.error(e);process.exit(1)});
