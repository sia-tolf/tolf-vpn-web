const fs=require('node:fs');
const assert=require('node:assert/strict');
const path=require('node:path');
const root=__dirname;
const html=fs.readFileSync(path.join(root,'experiment.html'),'utf8');
for(const [id,operation,isOn] of [
 ['on','Connect',true],['off','Disconnect',false]
]) {
 const name=id.toUpperCase();
 const source=fs.readFileSync(path.join(root,'cherri-'+id+'.cherri'),'utf8');
 assert(source.startsWith('#define name TOLF '+name));
 assert(source.includes('"WFVPNOperation": "Set On Demand"'));
 assert(source.includes('"WFOnDemandValue": '+(isOn?'true':'false')));
 assert(source.includes('"WFVPNOperation": "'+operation+'"'));
 assert(source.includes('applyTolfOnDemand(vpnDemand)'));
 assert(source.includes('applyTolfConnection(vpnConnection)'));
 assert.equal((source.match(/#question /g)||[]).length,2);
 assert(html.includes('/shortcuts/signed/TOLF-'+name+'.shortcut'),
        'Website must link to Apple-signed binaries, not the Cherri editor');
 console.log('EXPERIMENT_SOURCE_VALID',id);
}
