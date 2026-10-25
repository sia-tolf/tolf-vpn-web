(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.TolfPricingCurve=api;})(typeof globalThis!=='undefined'?globalThis:this,function(){
'use strict';
function quote(gb){
 if(!Number.isInteger(gb)||gb<1||gb>1000)throw new RangeError('Volume must be an integer from 1 to 1000 GB');
 const baseCents=6*gb;
 // P in cents = 6G - 3G²/1250. Integer arithmetic, half-up to cents.
 const cents=Math.floor((7500*gb-3*gb*gb+625)/1250);
 return {gb,cents,baseCents,savingCents:baseCents-cents,discountPercent:gb/25,unitEuros:cents/100/gb};
}
return Object.freeze({quote,min:1,max:1000});
});
