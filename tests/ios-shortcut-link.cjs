
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const {ids,withShares}=require('./ios-city-share-fixture.cjs');
const source=fs.readFileSync('js/ios-vpn-buttons.js','utf8');
const el=()=>({children:[],setAttribute(){},append(...v){this.children.push(...v)},replaceChildren(...v){this.children=v},addEventListener(){}});
const flat=n=>n.children.flatMap(c=>[c,...flat(c)]);
for(const configured of [false,true]){
 const ctx={window:{},document:{documentElement:{lang:'ru'},createElement:el},URL,Map,Date};
 vm.createContext(ctx);vm.runInContext(configured?withShares(source):source,ctx);
 for(const [name,city] of [['TOLF Moscow','moscow'],['TOLF Riga','riga']]){
  for(const lang of ['ru','en','lv']){
   const nodes=flat(ctx.window.tolfIosButtons.create({checked:true,vpnName:name,lang,url:'https://api.tolf.is/oc/access/devices/test/ios.mobileconfig?ingress='+city}));
   const a=nodes.find(n=>n.href);
   if(!configured){assert.equal(a,undefined);continue;}
   assert.equal(a.href,'https://www.icloud.com/shortcuts/'+ids[city]);
   assert(a.textContent.includes(name));
   assert(!nodes.some(n=>n.textContent?.includes('Откройте скачанный')));
  }
 }
}
console.log('PASS: each city uses the same English shortcut across all site languages; missing shares cannot fall back to generic TOLF');
