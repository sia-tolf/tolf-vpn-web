(()=>{'use strict';
const B=window.TolfBank,$=id=>document.getElementById(id);let cap=null,dialog=null,busy=false,requestId=null,chosen=null;
function update(){const b=$('bankInvoiceButton');if(!b)return;b.hidden=!cap?.admin||window.TolfBillingVolume.isTrial();b.textContent=B.t('request');b.disabled=!window.TolfBillingVolume.isValid();}
function field(key,type='text',max=160){const label=B.node('label');label.append(B.node('span',B.t(key)));const input=document.createElement('input');input.id='bankBuyer-'+key;input.type=type;input.maxLength=max;label.append(input);return label;}
function close(){if(!busy){dialog.close();dialog.remove();dialog=null;}}
function show(){
 if(dialog||!cap?.admin)return;
 dialog=document.createElement('dialog');dialog.className='bank-dialog';dialog.setAttribute('aria-labelledby','bankInvoiceTitle');dialog.addEventListener('cancel',e=>{e.preventDefault();close();});
 dialog.append(B.node('h2',B.t('title')));dialog.firstChild.id='bankInvoiceTitle';
 const error=B.node('p','','bank-error');error.id='bankInvoiceError';error.setAttribute('role','status');
 const actions=B.node('div',undefined,'bank-actions'),cancel=B.node('button',B.t('close'),'billing-secondary secondary');cancel.type='button';cancel.addEventListener('click',close);
 if(!cap.enabled){dialog.append(B.node('p',B.t('notConfigured'),'bank-note'));const a=B.node('a',B.t('settings'),'billing-secondary secondary');a.href='../admin/bank-payments.html?lang='+B.lang();actions.append(a,cancel);dialog.append(actions);document.body.append(dialog);dialog.showModal();return;}
 chosen=window.TolfBillingVolume.getVolume();if(chosen===null){dialog.remove();dialog=null;return;}
 requestId=crypto.randomUUID();const quote=window.TolfPricingCurve.quote(chosen);
 dialog.append(B.node('p',chosen+' '+(B.lang()==='ru'?'ГБ':'GB')+' · '+B.money(quote.cents/100),'bank-summary'));
 const form=document.createElement('form'),fields=B.node('div',undefined,'bank-fields');
 const kindLabel=B.node('label');kindLabel.append(B.node('span',B.t('kind')));const kind=document.createElement('select');kind.id='bankBuyer-kind';for(const [v,k] of [['individual','individual'],['company','company']]){const o=B.node('option',B.t(k));o.value=v;kind.append(o);}kindLabel.append(kind);fields.append(kindLabel);
 const name=field('name');name.classList.add('bank-wide');fields.append(name);const registration=field('registration', 'text',50);fields.append(registration);fields.append(field('vat','text',50));
 const countryLabel=B.node('label');countryLabel.append(B.node('span',B.t('country')));const country=document.createElement('select');country.id='bankBuyer-country';country.required=true;const empty=B.node('option',B.t('chooseCountry'));empty.value='';country.append(empty);let names;try{names=new Intl.DisplayNames([B.lang()],{type:'region'});}catch{}
 for(const code of cap.billingCountries){const o=B.node('option',names?.of(code)||code);o.value=code;country.append(o);}countryLabel.append(country);fields.append(countryLabel);
 const address=field('address','text',400);address.classList.add('bank-wide');fields.append(address);form.append(fields);
 $('bankBuyer-name')?.setAttribute('required',''); // Fields enter the document below.
 const terms=B.node('label',undefined,'bank-check'),check=document.createElement('input');check.type='checkbox';check.required=true;check.id='bankInvoiceTerms';terms.append(check,B.node('span',B.t('terms')));form.append(terms);
 const link=B.node('a',B.t('termsLink'));link.href='../terms.html?lang='+B.lang();link.target='_blank';link.rel='noopener';form.append(link,B.node('p',B.t('proforma'),'bank-note'),error);
 const create=B.node('button',B.t('create'),'billing-primary primary');create.type='submit';create.id='bankInvoiceCreate';actions.append(create,cancel);form.append(actions);dialog.append(form);document.body.append(dialog);
 $('bankBuyer-name').required=true;$('bankBuyer-address').required=true;
 function kindChange(){registration.hidden=kind.value!=='company';$('bankBuyer-registration').required=kind.value==='company';}kind.addEventListener('change',kindChange);kindChange();
 form.addEventListener('submit',async e=>{e.preventDefault();if(busy||!form.reportValidity())return;busy=true;for(const el of fields.querySelectorAll('input,select'))el.disabled=true;create.disabled=cancel.disabled=true;create.textContent=B.t('creating');error.textContent='';
  try{const invoice=await B.request('/billing/bank/invoices',{package:String(chosen),pricingVersion:cap.pricingVersion,termsVersion:cap.termsVersion,acceptTerms:true,startNow:true,requestId,locale:B.lang(),buyer:{kind:kind.value,name:$('bankBuyer-name').value.trim(),address:$('bankBuyer-address').value.trim(),country:country.value,registration:kind.value==='company'?$('bankBuyer-registration').value.trim():'',vatNumber:$('bankBuyer-vat').value.trim()}});busy=false;showResult(invoice);window.dispatchEvent(new Event('tolf:bank-invoice-created'));}
  catch(err){busy=false;for(const el of fields.querySelectorAll('input,select'))el.disabled=false;create.disabled=cancel.disabled=false;create.textContent=B.t('create');error.textContent=B.t(err.message);}
 });dialog.showModal();$('bankBuyer-name').focus();
}
function showResult(invoice){dialog.replaceChildren(B.node('h2',B.t('created')),B.node('p',invoice.number,'bank-reference'),B.node('p',B.t('pending'),'bank-status'),B.node('p',invoice.gb+' '+(B.lang()==='ru'?'ГБ':'GB')+' · '+B.money(invoice.amount),'bank-summary'));
 dialog.firstChild.id='bankInvoiceTitle';
 const details=B.node('dl');for(const [k,v] of [['due',invoice.dueDate],['beneficiary',invoice.bank.beneficiary],['bankName',invoice.bank.bankName],['iban',invoice.bank.iban],['reference',invoice.paymentReference]]){details.append(B.node('dt',B.t(k)),B.node('dd',v));}dialog.append(details,B.node('p',B.t('paymentNote'),'bank-note'));
 const actions=B.node('div',undefined,'bank-actions'),pdf=B.node('button',B.t('download'),'billing-primary primary'),copy=B.node('button',B.t('copy'),'billing-secondary secondary'),cancel=B.node('button',B.t('close'),'billing-secondary secondary'),error=B.node('p','','bank-error');
 pdf.type=copy.type=cancel.type='button';pdf.addEventListener('click',async()=>{try{await B.download(invoice.pdfUrl,invoice.number+'.pdf');}catch(e){error.textContent=B.t(e.message);}});copy.addEventListener('click',async()=>{try{await navigator.clipboard.writeText(invoice.paymentReference);copy.textContent=B.t('copied');}catch{error.textContent=invoice.paymentReference;}});cancel.addEventListener('click',close);actions.append(pdf,copy,cancel);dialog.append(actions,error);
}
window.addEventListener('tolf:billing-render',update);
(async()=>{try{cap=await B.request('/billing/bank/capabilities');update();$('bankInvoiceButton')?.addEventListener('click',show);}catch{update();}})();
})();
