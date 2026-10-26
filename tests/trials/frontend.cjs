const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const source=fs.readFileSync(path.resolve(__dirname,'../../billing/trial-registration.js'),'utf8');
class Element{constructor(tag='div'){this.tagName=tag;this.children=[];this.handlers={};this.hidden=false;this.textContent='';}append(...v){this.children.push(...v);}appendChild(v){this.children.push(v);}setAttribute(){}addEventListener(k,v){this.handlers[k]=v;}click(){return this.handlers.click?.();}}
const flush=()=>new Promise(setImmediate);
async function scenario(guest=false){
 let selected=true,answer=guest?401:{trialPackage:null,canClaim:true},poll,calls=[],nav=[];
 const card=new Element(),layout=new Element(),note=new Element(),select=new Element(),events={},docEvents={};
 const document={hidden:false,documentElement:{lang:'ru'},querySelector:s=>({'.trial-card':card,'.billing-layout':layout,'.preview-note':note}[s]),getElementById:()=>select,createElement:t=>new Element(t),addEventListener:(k,v)=>docEvents[k]=v};
 const context={document,URL,Intl,AbortController,setTimeout,clearTimeout,setInterval:fn=>{poll=fn;},TolfBillingVolume:{isTrial:()=>selected},location:{href:'https://vpn.tolf.is/billing/?trial=1',assign:u=>nav.push(u)},addEventListener:(k,v)=>events[k]=v,fetch:async(url,options)=>{calls.push({url,options});if(answer==='error')throw Error('offline');if(typeof answer==='number')return{ok:false,status:answer};return{ok:true,json:async()=>answer};}};context.window=context;
 vm.runInNewContext(source,context);await flush();
 const panel=card.children[0],[label,balance,status,button]=panel.children;
 assert.equal(layout.hidden,true);assert.equal(button.hidden,false);assert.equal(button.disabled,false);
 if(guest){await button.click();assert.equal(new URL(nav[0],'https://vpn.tolf.is').searchParams.get('purpose'),'trial');assert.equal(calls.length,1);return;}
 answer={trialPackage:{balanceBytes:750000000,paidBalanceBytes:0},canClaim:false};await button.click();
 assert.deepEqual(JSON.parse(calls.at(-1).options.body),{confirm:'CLAIM_TRIAL'});assert.equal(button.hidden,true);assert.match(balance.textContent,/0,750/);
 selected=false;events['tolf:billing-render']();assert.equal(layout.hidden,false);assert.equal(panel.hidden,false);assert.equal(balance.textContent,'0,750 ГБ');
 answer='error';await poll();assert.equal(balance.textContent,'0,750 ГБ');assert.match(status.textContent,/последние/);
 const count=calls.length;document.hidden=true;await poll();assert.equal(calls.length,count);document.hidden=false;
 answer={trialPackage:{balanceBytes:0,paidBalanceBytes:0}};await poll();assert.match(status.textContent,/закончился/);assert.equal(balance.textContent,'0,000 ГБ');
 answer={trialPackage:{balanceBytes:0,paidBalanceBytes:50000000000}};await poll();assert.match(status.textContent,/оплаченный/);
 answer=401;await poll();assert.equal(panel.hidden,true);assert.equal(balance.textContent,'');
 selected=true;events['tolf:billing-render']();assert.equal(button.hidden,false);await button.click();assert.equal(nav.length,1);
 assert(calls.every(c=>c.url==='https://api.tolf.is/account/trial-package'));
}
(async()=>{await scenario(true);await scenario();console.log('Trial UI: explicit signup, confirmed claim, separate live balance, paid form preservation, exhaustion, paid continuation, hidden pause, transient error and logout passed.');})().catch(e=>{console.error(e);process.exitCode=1;});
