const assert=require('node:assert/strict');
const {quote}=require('../billing/pricing-curve.js');
for(const [gb,cents] of [[50,294],[100,576],[200,1104],[500,2400],[750,3150],[1000,3600]])assert.equal(quote(gb).cents,cents);
let last=0;for(let g=50;g<=1000;g++){const q=quote(g);assert(q.cents>last,'Total must increase at '+g);assert(q.cents<=q.baseCents);assert.equal(q.cents+q.savingCents,q.baseCents);assert(q.discountPercent<=40);last=q.cents;}
assert.equal(quote(1000).savingCents/quote(1000).baseCents,.4);
for(const value of [0,1,49,1001,-1,50.5,NaN,Infinity,'200'])assert.throws(()=>quote(value),RangeError);
console.log('Curve verified for every whole volume from 50 to 1000 GB: increasing totals, exact cent rounding, 40% saving at 1 TB.');

const scale=require('../billing/pricing-curve.js');
assert.equal(scale.toPosition(50),0);assert.equal(scale.toPosition(1000),10000);
for(let g=50;g<=1000;g++)assert.equal(scale.fromPosition(scale.toPosition(g)),g,'Slider round trip at '+g);
const visited=new Set();let previous=50;
for(let p=0;p<=10000;p++){const g=scale.fromPosition(p);assert(g>=previous);visited.add(g);previous=g;}
assert.equal(visited.size,951);
const doubling=[50,100,200,400,800].map(g=>scale.toPosition(g));
const intervals=doubling.slice(1).map((p,i)=>p-doubling[i]);
assert(Math.max(...intervals)-Math.min(...intervals)<=1);
console.log('Log scale: endpoints, every reachable GB, exact input round trips and equal spacing for volume doublings verified.');
