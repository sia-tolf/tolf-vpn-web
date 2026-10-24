const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const {ids,withShares}=require('./ios-city-share-fixture.cjs');
const source=fs.readFileSync('js/ios-vpn-buttons.js','utf8');
const el=()=>({children:[],setAttribute(){},append(...v){this.children.push(...v)},replaceChildren(...v){this.children=v},addEventListener(){}});
const flat=n=>n.children.flatMap(c=>[c,...flat(c)]);
const published={moscow:'3b5b6270b5464d84866084aad873647b',riga:'02ed7a839cee48289255a2a4338392fe'};
for(const configured of ['production','synthetic','unpublished']){
 const ctx={window:{},document:{documentElement:{lang:'ru'},createElement:el},URL,Map,Date};
 const script=configured==='synthetic'?withShares(source):configured==='unpublished'?source.replace(/const CITY_SHARES = \{[\s\S]*?\n  \};/,'const CITY_SHARES = {moscow:null,riga:null};'):source;
 vm.createContext(ctx);vm.runInContext(script,ctx);
 for(const [name,city] of [['TOLF Moscow AnyConnect','moscow'],['TOLF Riga AnyConnect','riga']]){
  for(const lang of ['ru','en','lv']){
   const nodes=flat(ctx.window.tolfIosButtons.create({checked:true,vpnName:name,lang,url:'https://api.tolf.is/oc/access/devices/test-device/ios.mobileconfig?ingress='+city}));
   const a=nodes.find(n=>n.href);
   if(configured==='unpublished'){assert.equal(a,undefined);continue;}
   assert.equal(a.href,'https://www.icloud.com/shortcuts/'+(configured==='synthetic'?ids[city]:published[city]));
   assert(a.textContent.includes(name));
   assert(!nodes.some(n=>n.href?.includes('.shortcut')));
  }
 }
}
console.log('PASS: iCloud-only installation; unpublished shares cannot fall back to files or obsolete VPN names.');
