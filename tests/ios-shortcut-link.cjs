const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const el=()=>({children:[],setAttribute(){},append(...v){this.children.push(...v)},replaceChildren(...v){this.children=v},addEventListener(){}});
const ctx={window:{},document:{documentElement:{lang:'ru'},createElement:el},URL,Map,Date};
vm.createContext(ctx);vm.runInContext(fs.readFileSync('js/ios-vpn-buttons.js','utf8'),ctx);
const flat=n=>n.children.flatMap(c=>[c,...flat(c)]);
for(const [name,ingress,shared] of [['TOLF Москва iPhone','moscow',true],['TOLF Рига iPhone','riga',false],['TOLF Москва iPad','moscow',false]]){
 const nodes=flat(ctx.window.tolfIosButtons.create({checked:true,vpnName:name,url:'https://api.tolf.is/oc/access/devices/test/ios.mobileconfig?ingress='+ingress}));
 const a=nodes.find(n=>n.href);
 assert.equal(a.href.startsWith('https://www.icloud.com/shortcuts/'),shared);
 if(shared)assert.equal(a.href,'https://www.icloud.com/shortcuts/3a9772ebbb5d4b179138784da39fca4e');
 else {assert(a.href.includes('control.shortcut?ingress='+ingress));assert.equal(a.textContent,'Скачать команду TOLF');}
}
console.log('PASS: iCloud controller only for exact VPN name; other connections keep their own file');
