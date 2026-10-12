const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const crypto=require('node:crypto').webcrypto;
const path=require('node:path');
const c=vm.createContext({crypto,Uint8Array,AbortController,performance,setTimeout,clearTimeout,setInterval,clearInterval});
vm.runInContext(fs.readFileSync(path.join(__dirname,'../js/confirmed-upload.js'),'utf8'),c);
(async()=>{
  let receipts=0, sentBytes=0;
  const fetcher=async(url,options)=>{
    assert.ok(options.body instanceof Uint8Array);
    assert.equal(options.credentials,'omit');
    assert.ok(url.includes('cors=true'));
    await new Promise(r=>setTimeout(r,3));
    if(options.signal.aborted)throw new Error('aborted');
    receipts++;sentBytes+=options.body.byteLength;
    return {ok:true,arrayBuffer:async()=>new ArrayBuffer(0)};
  };
  const result=await c.measureConfirmedUpload('https://test/',{duration:80,fetcher});
  assert.ok(result.mbps>0);assert.ok(result.completed>0);
  assert.ok(result.acknowledgedBytes<=sentBytes);
  await assert.rejects(c.measureConfirmedUpload('https://test/',{duration:80,fetcher:async()=>({ok:false,status:413})}),/upload_http_413/);
  await assert.rejects(c.measureConfirmedUpload('https://test/',{duration:30,fetcher:async(url,{signal})=>new Promise((resolve,reject)=>signal.addEventListener('abort',()=>reject(new Error('abort'))))}),/upload_no_response/);
  const ctrl=new AbortController();ctrl.abort();
  await assert.rejects(c.measureConfirmedUpload('https://test/',{signal:ctrl.signal,fetcher}),/upload_cancelled/);
  const mid=new AbortController();setTimeout(()=>mid.abort(),30);
  await assert.rejects(c.measureConfirmedUpload('https://test/',{duration:100,signal:mid.signal,fetcher}),/upload_cancelled/);
  console.log('PASS confirmed bytes, typed-array body, HTTP rejection, stalled request, cancellation');
})().catch(e=>{console.error(e);process.exit(1)});
