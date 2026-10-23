const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync('js/profile-settings.js','utf8').split('const dpdRate')[0];
for(const [server,city] of [['moscow','Moscow'],['riga','Riga'],['us','New York']]){
 for(const route of ['','ru','sr','auto']){
  const input={value:'',dataset:{}},context={getSelectedServerKey:()=>server,getSelectedLocalId:()=>route,document:{getElementById:()=>input}};
  vm.createContext(context);vm.runInContext(source,context);
  context.updateProfileNameDefault();
  const expected='TOLF '+city+' IKEv2'+(route?' '+route:'');
  assert.equal(input.value,expected);assert.equal(context.selectedAppleProfileName(),expected);
  assert.equal(input.value.includes('AnyConnect'),false);
 }
}
console.log('iOS website names: all cities and routing suffixes explicitly include IKEv2.');
