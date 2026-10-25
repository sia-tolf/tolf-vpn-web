const assert=require('node:assert/strict');
const {quote}=require('../billing/pricing-curve.js');
for(const [gb,cents] of [[1,6],[50,294],[100,576],[200,1104],[500,2400],[750,3150],[1000,3600]])assert.equal(quote(gb).cents,cents);
let last=0;for(let g=1;g<=1000;g++){const q=quote(g);assert(q.cents>last,'Total must increase at '+g);assert(q.cents<=q.baseCents);assert.equal(q.cents+q.savingCents,q.baseCents);assert(q.discountPercent<=40);last=q.cents;}
assert.equal(quote(1000).savingCents/quote(1000).baseCents,.4);
for(const value of [0,1001,-1,1.5,NaN,Infinity,'200'])assert.throws(()=>quote(value),RangeError);
console.log('Curve verified for every whole volume from 1 to 1000 GB: increasing totals, exact cent rounding, 40% saving at 1 TB.');
