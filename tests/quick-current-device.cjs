const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync('quick/quick-1.js','utf8'),strings=fs.readFileSync('quick/strings-1.js','utf8');
async function check(ua,platform,node,unsupported=false,target=''){
 const elements=new Map();const el=id=>{if(!elements.has(id))elements.set(id,{hidden:false,value:'',dataset:{},textContent:'',disabled:false,classList:{add(){},remove(){}},setAttribute(){},replaceChildren(){}});return elements.get(id);};
 let posted;
 const context={location:{href:'https://vpn.tolf.is/quick/?protocol=ikev2'+(target?'&platform='+target:'')},document:{getElementById:el,documentElement:{lang:'en'},querySelectorAll:()=>[]},navigator:{userAgent:ua,platform:ua==='desktop-ipad'?'MacIntel':'',maxTouchPoints:ua==='desktop-ipad'?5:0,language:'ru'},localStorage:{getItem:()=>null,setItem(){}},sessionStorage:{getItem:k=>({quickPlatform:'windows',quickServer:'riga',quickManual:'yes'})[k],setItem(){},removeItem(){}},window:{addEventListener(){},location:{assign(){}}},URL,AbortSignal,
 fetch:async(url,opt={})=>{let data;if(url.endsWith('capabilities'))data={version:1};else if(url.endsWith('entry-point-recommendation'))data={entryPoint:node};else if(url.endsWith('/me'))data={authenticated:true};else if(url.endsWith('/prepare')){posted=JSON.parse(opt.body);data={profileUrl:'https://api.tolf.is/test/download'};}else throw Error('Unexpected '+url);return {ok:true,json:async()=>data};}};
 vm.createContext(context);vm.runInContext(strings,context);vm.runInContext(source,context);for(let n=0;n<30;n++)await Promise.resolve();
 assert.equal(el('change').hidden,true);assert.equal(el('choices').hidden,true);
 if(target==='windows'&&platform!=='windows'){assert.equal(el('prepare').disabled,true);await el('prepare').onclick();assert.equal(posted,undefined);assert.match(el('message').textContent,/Windows/);return;}
 if(unsupported){assert.equal(el('prepare').disabled,true);return;}
 assert.equal(el('server').textContent,node==='moscow'?'Москва':'Рига');
 await el('prepare').onclick();assert.equal(posted.platform,platform);assert.equal(posted.server,node);assert.equal(posted.currentDevice,true);assert.equal(el('download').hidden,false);
}
(async()=>{await check('iPhone','ios','moscow');await check('desktop-ipad','ios','riga');await check('Android','android','moscow');await check('Windows NT','windows','riga');await check('Linux',null,'riga',true);await check('desktop-ipad','ios','riga',false,'windows');await check('Android','android','moscow',false,'windows');await check('Windows NT','windows','riga',false,'windows');console.log('PASS: native devices, stale choices ignored, recommendation, no selectors, unsupported device');})().catch(e=>{console.error(e);process.exit(1);});
