(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.TolfPricingCurve=api;})(typeof globalThis!=='undefined'?globalThis:this,function(){
'use strict';
function quote(gb){
 if(!Number.isInteger(gb)||gb<50||gb>1000)throw new RangeError('Volume must be an integer from 50 to 1000 GB');
 const baseCents=6*gb;
 // P in cents = 6G - 3G²/1250. Integer arithmetic, half-up to cents.
 const cents=Math.floor((7500*gb-3*gb*gb+625)/1250);
 return {gb,cents,baseCents,savingCents:baseCents-cents,discountPercent:gb/25,unitEuros:cents/100/gb};
}
const scaleSteps=10000;
function toPosition(gb){quote(gb);return Math.round(Math.log(gb/50)/Math.log(20)*scaleSteps);}
function fromPosition(position){
 if(!Number.isFinite(position))throw new RangeError('Invalid slider position');
 return Math.max(50,Math.min(1000,Math.round(50*Math.pow(20,Math.max(0,Math.min(scaleSteps,position))/scaleSteps))));
}
return Object.freeze({quote,min:50,max:1000,scaleSteps,toPosition,fromPosition});
});
