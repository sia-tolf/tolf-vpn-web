const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync('quick/quick-1.js','utf8'),strings=fs.readFileSync('quick/strings-1.js','utf8');
async function check(ua,platform,node,unsupported=false){
 const elements=new Map();const el=id=>{if(!elements.has(id))elements.set(id,{hidden:false,value:'',dataset:{},textContent:'',disabled:false,classList:{add(){},remove(){}},setAttribute(){}});return elements.get(id);};
 let posted;
 const context={document:{getElementById:el,documentElement:{lang:'en'},querySelectorAll:()=>[]},navigator:{userAgent:ua,platform:ua==='desktop-ipad'?'MacIntel':'',maxTouchPoints:ua==='desktop-ipad'?5:0,language:'ru'},localStorage:{getItem:()=>null,setItem(){}},sessionStorage:{getItem:k=>({quickPlatform:'windows',quickServer:'riga',quickManual:'yes'})[k],setItem(){},removeItem(){}},window:{addEventListener(){},location:{assign(){}}},URL,AbortSignal,
 fetch:async(url,opt={})=>{let data;if(url.endsWith('capabilities'))data={version:1};else if(url.endsWith('entry-point-recommendation'))data={entryPoint:node};else if(url.endsWith('/me'))data={authenticated:true};else if(url.endsWith('/prepare')){posted=JSON.parse(opt.body);data={profileUrl:'https://api.tolf.is/test/download'};}else throw Error('Unexpected '+url);return {ok:true,json:async()=>data};}};
 vm.createContext(context);vm.runInContext(strings,context);vm.runInContext(source,context);for(let n=0;n<30;n++)await Promise.resolve();
 assert.equal(el('change').hidden,true);assert.equal(el('choices').hidden,true);
 if(unsupported){assert.equal(el('prepare').disabled,true);return;}
 assert.equal(el('server').textContent,node==='moscow'?'Москва':'Рига');
 await el('prepare').onclick();assert.equal(posted.platform,platform);assert.equal(posted.server,node);assert.equal(posted.currentDevice,true);assert.equal(el('download').hidden,false);
}
(async()=>{await check('iPhone','ios','moscow');await check('desktop-ipad','ios','riga');await check('Android','android','moscow');await check('Windows NT','windows','riga');await check('Linux',null,'riga',true);console.log('PASS: native devices, stale choices ignored, recommendation, no selectors, unsupported device');})().catch(e=>{console.error(e);process.exit(1);});
