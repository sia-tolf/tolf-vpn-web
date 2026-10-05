(() => {
 const labels={ru:'Возврат',lv:'Atpakaļ',en:'Back'};
 const anchors=[...document.querySelectorAll('[data-return-control]')];
 function render(){
  const label=labels[document.documentElement.lang]||labels.en;
  for(const a of anchors){
   if(!a.querySelector('.tolf-return-label')){
    const logo=a.querySelector('img');
    const text=document.createElement('span');text.className='tolf-return-label';
    if(logo)a.replaceChildren(logo,text);
    else if(a.dataset.returnLogo==='yes'){
     const image=document.createElement('img');image.src='https://tolf.is/tolf-logo-star.svg';image.alt='';image.width=22;image.height=22;
     a.replaceChildren(image,text);
    }else a.replaceChildren(text);
   }
   const text=a.querySelector('.tolf-return-label');
   if(text.textContent!==label)text.textContent=label;
   if(a.getAttribute('aria-label')!==label)a.setAttribute('aria-label',label);
  }
 }
 render();
 new MutationObserver(render).observe(document.documentElement,{attributes:true,attributeFilter:['lang']});
 for(const a of anchors)new MutationObserver(render).observe(a,{childList:true,subtree:true});
})();