const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync('js/ios-vpn-buttons.js','utf8');
const el=()=>({children:[],setAttribute(){},append(...v){this.children.push(...v)},replaceChildren(...v){this.children=v},addEventListener(){}});
const flat=n=>n.children.flatMap(c=>[c,...flat(c)]);
const ctx={window:{},document:{documentElement:{lang:'ru'},createElement:el},URL,Map,Date};
vm.createContext(ctx);vm.runInContext(source,ctx);
for(const [name,city] of [['TOLF Moscow AnyConnect','moscow'],['TOLF Riga AnyConnect','riga']]){
 for(const lang of ['ru','en','lv']){
  const nodes=flat(ctx.window.tolfIosButtons.create({checked:true,vpnName:name,lang,url:'https://api.tolf.is/oc/access/devices/test-device/ios.mobileconfig?ingress='+city+'&buttons=true'}));
  const a=nodes.find(n=>n.href);
  assert.equal(a.href,'https://api.tolf.is/oc/access/devices/test-device/shortcuts/control.shortcut?ingress='+city);
  assert(a.textContent.includes(name));
  assert(!a.textContent.includes('TOLF-'));
  assert(nodes.some(n=>n.tagName==='strong'||n.textContent===name));
 }
}
for(const url of ['https://other.example/oc/access/devices/test/ios.mobileconfig','https://api.tolf.is/invalid','https://api.tolf.is/oc/access/devices/test/ios.mobileconfig?ingress=us']){
 const nodes=flat(ctx.window.tolfIosButtons.create({checked:true,vpnName:'TOLF',url}));
 assert(!nodes.some(n=>n.href));
}
console.log('PASS: exact per-device signed command URL and full protocol-qualified name in all languages; no stale iCloud fallback.');
