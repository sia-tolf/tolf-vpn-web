// This link is only a convenience. Every admin API request independently checks the role.
(() => {
 const card=document.getElementById('vpnCard');if(!card)return;
 const labels={en:'Administration',ru:'Администрирование',lv:'Administrēšana'};
 const link=document.createElement('a');link.href='/admin/';link.className='button-link secondary hidden';
 link.style.cssText='width:fit-content;margin:0 0 18px;min-height:40px';
 const heading=card.querySelector('.card-topline');if(!heading)return;heading.insertAdjacentElement('afterend',link);
 let epoch=0,visible=false;
 const label=()=>{link.textContent=labels[document.documentElement.lang]||labels.en;};
 function check(){const now=!card.classList.contains('hidden');if(now===visible)return;visible=now;const own=++epoch;link.classList.add('hidden');if(!now)return;
   fetch('https://api.tolf.is/admin/me',{credentials:'include',cache:'no-store',headers:{Accept:'application/json'}})
    .then(r=>r.ok?r.json():null).then(data=>{if(own===epoch&&visible&&data?.isAdmin===true)link.classList.remove('hidden');}).catch(()=>{});
 }
 new MutationObserver(check).observe(card,{attributes:true,attributeFilter:['class']});
 new MutationObserver(label).observe(document.documentElement,{attributes:true,attributeFilter:['lang']});
 label();check();
})();
