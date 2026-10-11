const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const el=()=>({children:[],setAttribute(){},append(...v){this.children.push(...v)},replaceChildren(...v){this.children=v},addEventListener(){}});
const ctx={window:{},document:{documentElement:{lang:'ru'},createElement:el},URL,Map,Date};
vm.createContext(ctx);vm.runInContext(fs.readFileSync('js/ios-vpn-buttons.js','utf8'),ctx);
const flat=n=>n.children.flatMap(c=>[c,...flat(c)]);
for(const [name,ingress] of [['TOLF Москва iPhone','moscow'],['TOLF Рига iPhone','riga'],['TOLF Москва iPad','moscow']]){
 const nodes=flat(ctx.window.tolfIosButtons.create({checked:true,vpnName:name,url:'https://api.tolf.is/oc/access/devices/test/ios.mobileconfig?ingress='+ingress}));
 const a=nodes.find(n=>n.href);
 assert(a.href.includes('control.shortcut?ingress='+ingress));
 assert.equal(a.textContent,'Добавить команду «'+name+'»');
 assert(!nodes.some(n => n.href?.includes('icloud.com')));

}
console.log('PASS: all installation links use updated per-device controller');
