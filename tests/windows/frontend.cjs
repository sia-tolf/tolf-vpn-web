const vm=require('node:vm'), fs=require('node:fs'), assert=require('node:assert/strict');
const root=require('node:path').resolve(__dirname,'../..')+'/';
class E {
 constructor(){this.classList={toggle(){},add(){},remove(){}};this.dataset={};this.events={};this.value='';this.children=[];}
 setAttribute(){} removeAttribute(){} addEventListener(n,f){this.events[n]=f} append(...x){this.children.push(...x)} replaceChildren(){this.children=[]} focus(){}
}
const elements=new Map();const node=id=>{if(!elements.has(id))elements.set(id,new E());return elements.get(id)};
const calls=[];
const ctx={console,crypto:require('node:crypto').webcrypto,document:{getElementById:node,createElement:()=>new E()},navigator:{},window:{confirm:()=>true},localStorage:{setItem(){}},currentPlatform:'ios',currentLanguage:'en',vpnBusy:false,lastVpnState:{configured:true},platformIos:node('platformIos'),platformAndroid:node('platformAndroid'),generateProfileButton:node('generateProfileButton'),installProfileButton:node('installProfileButton'),shareProfileButton:node('shareProfileButton'),onDemandSection:node('onDemandSection'),onDemandAndroidNote:node('onDemandAndroidNote'),vpnMessage:node('vpnMessage'),t:k=>k,setInstallLink(){},copyText:async()=>{},setVpnBusy(v){ctx.vpnBusy=v;},apiRequest:async(path,opt)=>{calls.push([path,opt]);if(path.endsWith('capabilities'))return {version:'1.0',servers:['riga']};if(opt.method==='GET')return {devices:[]};return {profileUrl:'https://api.tolf.is/windows/p/test'};}};
vm.createContext(ctx);
vm.runInContext(fs.readFileSync(root+'js/platform.js','utf8'),ctx);
vm.runInContext(fs.readFileSync(root+'js/windows.js','utf8'),ctx);
(async()=>{
 await new Promise(r=>setImmediate(r));
 vm.runInContext('setPlatform("windows")',ctx);
 await new Promise(r=>setImmediate(r));
 assert.equal(calls.filter(([,o])=>o.method==='POST').length,0,'selecting Windows must not create a user');
 node('windowsDeviceName').value='Office PC';node('windowsCreateForm').events.submit({preventDefault(){}});
 await new Promise(r=>setImmediate(r));
 const posts=calls.filter(([,o])=>o.method==='POST');assert.equal(posts.length,1);assert.equal(posts[0][0],'/windows/devices');assert.equal(JSON.parse(posts[0][1].body).name,'Office PC');
 assert.ok(!calls.some(([p,o])=>p==='/vpn/create'&&o.method==='POST'));
 vm.runInContext('clearWindowsDevices()',ctx);assert.equal(node('windowsDeviceName').value,'');
 console.log('PASS: Windows selection is read-only; explicit device creation uses independent API; logout clears state');
})().catch(e=>{console.error(e);process.exit(1)});
