const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const crypto = require('node:crypto').webcrypto;
const source = fs.readFileSync(require('node:path').join(__dirname,'../../js/visits.js'),'utf8');
let clock = 1793020000000;
class Element {
  constructor() { this.children=[]; this.handlers={}; this.hidden=false; this.nodes={}; }
  set innerHTML(value) { this.html=value; for(const key of ['h2','p','a','[data-allow]','[data-basic]','.tolf-visits-close']) this.nodes[key]=new Element(); }
  querySelector(key) { return this.nodes[key]; }
  querySelectorAll(key) { return key==='button' ? [this.nodes['[data-allow]'],this.nodes['[data-basic]'],this.nodes['.tolf-visits-close']] : []; }
  setAttribute() {}
  addEventListener(key,fn) { this.handlers[key]=fn; }
  appendChild(child) { this.children.push(child); }
}
function browser({storage=new Map(),url='https://vpn.tolf.is/billing/?private=SECRET#SECRET',dnt=false,gpc=false,owner=false,blocked=false}={}) {
  const calls=[],events={},windowEvents={},body=new Element(),footer=new Element();
  const localStorage={getItem:key=>{if(blocked)throw Error();return storage.get(key)||null;},setItem:(key,value)=>{if(blocked)throw Error();storage.set(key,value);},removeItem:key=>storage.delete(key)};
  class ClockDate extends Date { static now(){return clock;} }
  const location=new URL(url), history={replaceState:(...args)=>{history.replaced=args[2];},state:null};
  const document={documentElement:{lang:'ru'},readyState:'loading',visibilityState:'visible',referrer:'https://search.example/results?secret=SECRET',body,addEventListener:(key,fn)=>events[key]=fn,createElement:()=>new Element(),querySelector:()=>footer};
  const context={document,location,history,navigator:{doNotTrack:dnt?'1':'0',globalPrivacyControl:gpc},localStorage,crypto,Date:ClockDate,URL,AbortController,MutationObserver:class{observe(){}},setTimeout:()=>1,clearTimeout(){},fetch:async(url,options)=>{calls.push({url,options,payload:JSON.parse(options.body)});return {ok:true,json:async()=>owner?{excluded:true}:{status:'ok'}};}};
  context.window=context;context.top=context;context.self=context;context.addEventListener=(key,fn)=>windowEvents[key]=fn;
  vm.runInNewContext(source,context);
  return {calls,events,windowEvents,storage,body,footer,history,context,ready:()=>events.DOMContentLoaded?.(),count:async()=>{events.visibilitychange();await new Promise(setImmediate);}};
}
function permitted(storage=new Map()) {storage.set('tolfAnalyticsChoice',JSON.stringify({allow:true,expires:clock+86400000}));return storage;}
(async()=>{
  let b=browser();b.ready();await b.count();
  assert.equal(b.calls.length,1);assert.equal(b.calls[0].payload.page,'/billing/');assert.equal(b.calls[0].payload.referrer,'search.example');
  assert.equal(b.calls[0].payload.browserId,undefined);assert.equal(b.storage.has('tolfAnalyticsBrowser'),false);assert(!JSON.stringify(b.calls).includes('SECRET'));
  await b.count();assert.equal(b.calls.length,1,'visibility does not duplicate the current page view');
  b.windowEvents.pageshow({persisted:true});await new Promise(setImmediate);assert.equal(b.calls.length,2);assert.notEqual(b.calls[0].payload.eventId,b.calls[1].payload.eventId);
  let storage=permitted();b=browser({storage});b.ready();await b.count();
  const first=b.calls[0].payload;assert.equal(first.consent,true);assert(first.browserId&&first.visitId);
  clock+=1000;let next=browser({storage});next.ready();await next.count();assert.equal(next.calls[0].payload.browserId,first.browserId);assert.equal(next.calls[0].payload.visitId,first.visitId);
  clock+=1800001;next=browser({storage});next.ready();await next.count();assert.equal(next.calls[0].payload.browserId,first.browserId);assert.notEqual(next.calls[0].payload.visitId,first.visitId);
  clock+=31*86400000;storage.set('tolfAnalyticsChoice',JSON.stringify({allow:true,expires:clock+86400000}));next=browser({storage});next.ready();await next.count();assert.notEqual(next.calls[0].payload.browserId,first.browserId);
  // A choice must precede creation of a persistent identifier.
  b=browser();b.ready();const panel=b.body.children[0];assert.equal(panel.hidden,false);assert.equal(b.storage.has('tolfAnalyticsBrowser'),false);
  panel.querySelector('[data-allow]').handlers.click();await b.count();assert.equal(b.calls[0].payload.consent,true);
  panel.querySelector('[data-basic]').handlers.click();assert.equal(b.storage.has('tolfAnalyticsBrowser'),false);
  next=browser({storage:b.storage});next.ready();await next.count();assert.equal(next.calls[0].payload.browserId,undefined);
  for(const options of [{dnt:true},{gpc:true},{url:'https://vpn.tolf.is/admin/'},{storage:new Map([['tolfAnalyticsExcluded','1']])}]){b=browser(options);b.ready();await b.count();assert.equal(b.calls.length,0);}
  b=browser({url:'https://vpn.tolf.is/?analytics=exclude&lang=ru'});b.ready();await b.count();assert.equal(b.calls.length,0);assert.equal(b.storage.get('tolfAnalyticsExcluded'),'1');assert.equal(b.history.replaced,'/?lang=ru');
  assert.match(b.body.children[0].textContent,/исключён/);
  b=browser({url:'https://vpn.tolf.is/?analytics=exclude',blocked:true});b.ready();await b.count();assert.equal(b.calls.length,0);assert.match(b.body.children[0].textContent,/не разрешает/);
  b=browser({owner:true});b.ready();await b.count();assert.equal(b.storage.get('tolfAnalyticsExcluded'),'1');next=browser({storage:b.storage});next.ready();await next.count();assert.equal(next.calls.length,0);
  b=browser({blocked:true});b.ready();await b.count();assert.equal(b.calls.length,1);assert.equal(b.calls[0].payload.browserId,undefined);
  console.log('Analytics frontend: consent, anonymous counts, returning visits, deduplication, exclusions, DNT/GPC, storage failures and URL stripping passed.');
})().catch(error=>{console.error(error);process.exitCode=1;});
