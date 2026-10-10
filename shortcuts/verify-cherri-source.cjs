const fs=require('node:fs');
const vm=require('node:vm');
const assert=require('node:assert/strict');
const root=__dirname;
const html=fs.readFileSync(root+'/experiment.html','utf8');
const script=html.match(/<script>([\s\S]*?)<\/script>/)?.[1];
assert(script,'Experiment JS not found');
const links={on:{},off:{}};
vm.runInNewContext(script,{URL,document:{getElementById:id=>links[id]}});
for(const [id,op,desired] of [['on','Connect',true],['off','Disconnect',false]]) {
 const url=new URL(links[id].href), code=url.searchParams.get('code');
 assert.equal(url.origin,'https://playground.cherrilang.org');
 assert(code.includes('"WFVPNOperation": "Set On Demand"'));
 assert(code.includes('"WFVPNOperation": "'+op+'"'));
 assert(code.includes('"WFOnDemandValue": '+(desired?'true':'false')));
 assert.equal((code.match(/#question /g)||[]).length,2);
 assert(code.includes('"TOLF Москва iPhone"'), 'Import questions need a default value');
 fs.writeFileSync(root+'/cherri-'+id+'.cherri',code+'\n');
 console.log('SOURCE_VALID',id,'chars',code.length);
}
