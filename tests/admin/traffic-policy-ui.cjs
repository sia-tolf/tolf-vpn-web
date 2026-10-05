const fs=require('fs'),vm=require('vm'),assert=require('assert');
class El{constructor(tag){this.tag=tag;this.children=[];this.listeners={};this.dataset={};this.value='';this.textContent='';}append(...x){this.children.push(...x)}replaceChildren(...x){this.children=x}setAttribute(k,v){this[k]=v}addEventListener(k,f){this.listeners[k]=f}scrollIntoView(){}querySelectorAll(tag){return this.children.flatMap(c=>[(c.tag===tag?c:null),...c.querySelectorAll(tag)]).filter(Boolean)}}
const ids={};const document={documentElement:new El('html'),getElementById:id=>ids[id]??=(new El('div')),createElement:t=>new El(t),querySelectorAll:()=>[],addEventListener(){}};
const p={quotaBytes:null,downloadMbps:null,uploadMbps:null,maxConnections:null,exceededAction:'warn',reducedDownloadMbps:null,reducedUploadMbps:null,periodTimezone:'UTC'};
const view={number:9,revision:0,inherit:true,policy:{...p},usedBytes:63057316,remainingBytes:null,periodEnd:'2026-11-01T00:00:00+00:00',state:'unlimited'};
const data={default:{revision:1,policy:{...p}},users:[view]};const writes=[];
const context={document,window:{addEventListener(){}},navigator:{language:'ru-RU'},localStorage:{getItem:()=> 'ru'},crypto:require('crypto').webcrypto,console,fetch:async(url,options)=>{if(options.method==='POST'){writes.push({url,options,payload:JSON.parse(options.body)});return{ok:true,json:async()=>({status:'ok'})}}return{ok:true,json:async()=>data}}};
let s=fs.readFileSync(__dirname+'/../../admin/admin-1.3.js','utf8');s=s.replace("language();$('gateMessage').textContent=t('loading');start();","globalThis.test={readPolicyNumber,policyForm,showPolicies};allowed=true;tab='limits';");vm.createContext(context);vm.runInContext(s,context);
const test=context.test;assert.equal(test.readPolicyNumber('100',1e9),1e11);assert.equal(test.readPolicyNumber(''),null);for(const n of ['-1','Infinity','NaN'])assert.throws(()=>test.readPolicyNumber(n));assert.throws(()=>test.readPolicyNumber('1.5',1,true));
function labels(form){const result={};for(const l of form.querySelectorAll('label'))result[l.textContent]=l.children[0];return result;}
function button(form,name){return form.querySelectorAll('button').find(b=>b.textContent===name);}
const flush=()=>new Promise(resolve=>setImmediate(resolve));
(async()=>{
 let host=new El('section');test.policyForm(data.default,host);let form=host.children[0],fields=labels(form);fields['Трафик за месяц, ГБ'].value='100';fields['Скачивание, Мбит/с'].value='50';form.listeners.submit({preventDefault(){}});await flush();await flush();assert.equal(writes[0].payload.policy.quotaBytes,1e11);assert.equal(writes[0].payload.policy.uploadMbps,null);assert.equal(writes[0].options.credentials,'include');assert.equal(writes[0].options.headers['Content-Type'],'application/json');
 host=new El('section');test.policyForm(view,host,9);form=host.children[0];fields=labels(form);fields['Дополнительный пакет, ГБ'].value='25';await button(form,'Добавить пакет').listeners.click();assert.equal(writes[1].payload.bytes,25e9);assert(writes[1].payload.requestId);
 host=new El('section');test.policyForm(view,host,9);await button(host.children[0],'Использовать общие настройки').listeners.click();assert.equal(writes[2].payload.policy,null);assert.equal(writes[2].payload.revision,0);
 test.showPolicies(data);assert(ids.results.children.length>0);console.log('PASS: units, unlimited fields, validation, save endpoint/credentials, extra package/request ID, inheritance, rendering');
})().catch(e=>{console.error(e);process.exit(1)});
