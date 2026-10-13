// External exit belongs to a device and applies only to Moscow ingress.
(() => {
 const row=document.getElementById('anyConnectModeRow');
 if(!row)return;
 const field=document.createElement('div');field.className='oc-ingress-field';
 const label=document.createElement('label'),select=document.createElement('select'),status=document.createElement('span');
 label.htmlFor='ocExternalExit';select.id='ocExternalExit';status.setAttribute('role','status');
 field.append(label,select,status);row.append(field);
 const texts={
  ru:{label:'Выход для подключения через Москву',riga:'По режимам · Рига',us:'По режимам · Нью-Йорк',all_us:'Весь трафик · Нью-Йорк',loading:'Загрузка…',saving:'Применение…',saved:'Применено',failed:'Не удалось применить'},
  en:{label:'Exit for Moscow connections',riga:'By routing mode · Riga',us:'By routing mode · New York',all_us:'All traffic · New York',loading:'Loading…',saving:'Applying…',saved:'Applied',failed:'Unable to apply'},
  lv:{label:'Izeja savienojumam caur Maskavu',riga:'Pēc režīma · Rīga',us:'Pēc režīma · Ņujorka',all_us:'Visa datplūsma · Ņujorka',loading:'Ielāde…',saving:'Piemēro…',saved:'Piemērots',failed:'Neizdevās piemērot'}
 };
 let choice='riga',selectedId=null,epoch=0,busy=false,ready=false,message='';
 const copy=()=>texts[document.documentElement.lang]||texts.en;
 window.getMoscowExitChoice=()=>choice;
 function render(){
  const c=copy(),isMoscow=window.ocAccess?.ingress?.().id==='moscow';
  field.hidden=!isMoscow;label.textContent=c.label;
  select.replaceChildren();
  for(const key of ['riga','us','all_us']){const option=document.createElement('option');option.value=key;option.textContent=c[key];select.append(option);}
  select.value=choice;select.disabled=!ready||busy||!window.ocAccess?.selected?.();
  status.textContent=message?c[message]:'';
  window.dispatchEvent(new Event('tolf:external-exit-change'));
 }
 async function request(id,method='GET',value){
  const response=await fetch(API+'/oc/access/devices/'+encodeURIComponent(id)+'/external-exit',{method,credentials:'include',cache:'no-store',headers:{Accept:'application/json',...(method==='POST'?{'Content-Type':'application/json'}:{})},...(method==='POST'?{body:JSON.stringify({choice:value})}:{})});
  if(!response.ok)throw Error('Exit unavailable');
  const data=await response.json();
  if(!['riga','us','all_us'].includes(data.choice)||data.scope!=='moscow')throw Error('Invalid exit response');
  return data;
 }
 async function refresh(){
  const d=window.ocAccess?.selected?.();
  if(d?.id===selectedId){render();return;}
  selectedId=d?.id||null;const token=++epoch;choice='riga';ready=false;busy=false;
  if(!d){message='';render();return;}
  message='loading';render();
  try{
   const data=await request(d.id);
   if(token!==epoch)return;
   choice=data.choice;ready=data.available===true;message='';
  }catch{if(token===epoch)message='failed';}
  finally{if(token===epoch)render();}
 }
 select.addEventListener('change',async()=>{
  const d=window.ocAccess?.selected?.();if(!d||busy||!ready)return;
  const value=select.value,previous=choice,token=epoch;busy=true;message='saving';render();
  try{
   const data=await request(d.id,'POST',value);
   if(token!==epoch)return;
   if(data.applied!==true||data.choice!==value)throw Error('Exit unconfirmed');
   choice=value;message='saved';
  }catch{if(token===epoch){choice=previous;message='failed';}}
  finally{if(token===epoch){busy=false;render();}}
 });
 window.addEventListener('tolf:ingress-changed',refresh);
 window.addEventListener('vpntransportchange',refresh);
 new MutationObserver(render).observe(document.documentElement,{attributes:true,attributeFilter:['lang']});
 refresh();
})();
