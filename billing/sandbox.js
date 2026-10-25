(() => {
'use strict';
const API='https://api.tolf.is', $=id=>document.getElementById(id);
const text={
ru:{pricingChanged:'Цена обновилась. Обновите страницу перед оплатой.',banner:'Тестовый режим Montonio. Реальные деньги не списываются. Тестовые гигабайты не используются для VPN.',balance:'Тестовый остаток трафика',balanceHelp:'Отдельный тестовый баланс. Рабочий трафик аккаунта не изменяется.',methods:'Способы оплаты получены от Montonio для тестового магазина.',country:'Страна банка',bank:'Банк',chooseBank:'Выберите банк',termsBefore:'Я принимаю ',terms:'условия сервиса',termsAfter:' для тестового заказа.',early:'Прошу начать оказание услуги сразу. При отказе в течение 14 дней стоимость уже оказанной части может удерживаться пропорционально использованному объёму. Сейчас это только тест.',ready:'Sandbox: платёж без списания реальных денег.',busy:'Открываем Montonio…',failed:'Не удалось выполнить тестовый запрос. Попробуйте обновить страницу.',consent:'Подтвердите условия и начало оказания услуги для тестового заказа.',pickBank:'Выберите банк для тестового платежа.',paid:'Тестовый платёж подтверждён. Тестовый пакет начислен.',pending:'Тестовый заказ ожидает оплаты или подтверждения. Продолжить оплату можно из истории.',declined:'Тестовый платёж не выполнен. Трафик не начислен.',checking:'Проверяем результат тестового платежа…',history:'Тестовые платежи',empty:'Тестовых заказов пока нет.',reference:'Заказ',status:'Статус',amount:'Сумма',trial:'Пробный пакет пока не активируется. Можно проверить оплату пакета 50, 200 или 500 ГБ.',resume:'Продолжить',invalid:'Результат возврата не подтверждён. Проверяем заказ по серверным данным.',unknown:'Результат запроса пока неизвестен. Проверьте историю перед повторной оплатой.',statuses:{CREATING:'Создаётся',UNKNOWN:'Проверяется',PENDING:'Ожидает оплаты',PAID:'Оплачен — тест',ABANDONED:'Не завершён',VOIDED:'Отменён',DECLINED:'Отклонён',CANCELLED:'Отменён',EXPIRED:'Истёк',AUTHORIZED:'Авторизован'}},
en:{pricingChanged:'Pricing has changed. Refresh the page before paying.',banner:'Montonio test mode. No real money is charged. Test gigabytes cannot be used for VPN.',balance:'Test traffic balance',balanceHelp:'Separate test balance. Your live traffic is not affected.',methods:'Payment methods supplied by Montonio for the sandbox store.',country:'Bank country',bank:'Bank',chooseBank:'Choose a bank',termsBefore:'I accept the ',terms:'terms of service',termsAfter:' for this test order.',early:'I request immediate service provision. If I withdraw within 14 days, the part already supplied may be charged proportionately to usage. This is currently only a test.',ready:'Sandbox: no real money is charged.',busy:'Opening Montonio…',failed:'The test request failed. Please refresh the page and try again.',consent:'Confirm the terms and immediate service provision for this test order.',pickBank:'Choose a bank for the test payment.',paid:'Test payment confirmed. The test package has been credited.',pending:'The test order is awaiting payment or confirmation. You can continue from the history.',declined:'Test payment was not completed. No traffic credited.',checking:'Checking the test payment…',history:'Test payments',empty:'No test orders yet.',reference:'Order',status:'Status',amount:'Amount',trial:'Trial activation is not available yet. You can test a 50, 200 or 500 GB purchase.',resume:'Continue',invalid:'The return result could not be validated. Checking server-side order data.',unknown:'The request outcome is not yet known. Check the history before paying again.',statuses:{CREATING:'Creating',UNKNOWN:'Checking',PENDING:'Awaiting payment',PAID:'Paid — test',ABANDONED:'Abandoned',VOIDED:'Voided',DECLINED:'Declined',CANCELLED:'Cancelled',EXPIRED:'Expired',AUTHORIZED:'Authorized'}},
lv:{pricingChanged:'Cena ir mainījusies. Pirms apmaksas atsvaidziniet lapu.',banner:'Montonio testa režīms. Reāla nauda netiek iekasēta. Testa gigabaitus nevar izmantot VPN.',balance:'Testa datu atlikums',balanceHelp:'Atsevišķs testa atlikums. Reālie konta dati netiek mainīti.',methods:'Montonio testa veikalam pieejamie maksājumu veidi.',country:'Bankas valsts',bank:'Banka',chooseBank:'Izvēlieties banku',termsBefore:'Es piekrītu ',terms:'pakalpojuma noteikumiem',termsAfter:' šim testa pasūtījumam.',early:'Es pieprasu sākt pakalpojumu nekavējoties. Ja izmantoju atteikuma tiesības 14 dienu laikā, par jau sniegto daļu var ieturēt maksu proporcionāli izmantotajam apjomam. Pašlaik tas ir tikai tests.',ready:'Sandbox: reāla nauda netiek iekasēta.',busy:'Atveram Montonio…',failed:'Testa pieprasījums neizdevās. Atsvaidziniet lapu un mēģiniet vēlreiz.',consent:'Apstipriniet noteikumus un tūlītēju pakalpojuma sākšanu testa pasūtījumam.',pickBank:'Izvēlieties banku testa maksājumam.',paid:'Testa maksājums apstiprināts. Testa paka ir ieskaitīta.',pending:'Testa pasūtījums gaida apmaksu vai apstiprinājumu. Apmaksu var turpināt vēsturē.',declined:'Testa maksājums nav pabeigts. Dati nav ieskaitīti.',checking:'Pārbaudām testa maksājumu…',history:'Testa maksājumi',empty:'Testa pasūtījumu vēl nav.',reference:'Pasūtījums',status:'Statuss',amount:'Summa',trial:'Izmēģinājuma aktivizēšana vēl nav pieejama. Var pārbaudīt 50, 200 vai 500 GB pirkumu.',resume:'Turpināt',invalid:'Atgriešanās rezultāts nav apstiprināts. Pārbaudām servera datus.',unknown:'Pieprasījuma rezultāts vēl nav zināms. Pirms atkārtotas apmaksas pārbaudiet vēsturi.',statuses:{CREATING:'Tiek veidots',UNKNOWN:'Pārbaude',PENDING:'Gaida apmaksu',PAID:'Apmaksāts — tests',ABANDONED:'Nav pabeigts',VOIDED:'Atcelts',DECLINED:'Noraidīts',CANCELLED:'Atcelts',EXPIRED:'Beidzies',AUTHORIZED:'Autorizēts'}}
};
const liveText={
ru:{pricingChanged:'Цена обновилась. Обновите страницу перед оплатой.',banner:'Реальная оплата Montonio. Доступна только администраторам. Будут списаны реальные деньги.',balance:'Остаток оплаченного трафика',balanceHelp:'Оплаченный объём за вычетом использованного трафика.',methods:'Доступные способы оплаты Montonio.',termsAfter:'.',early:'Прошу начать оказание услуги сразу. При отказе в течение 14 дней стоимость уже оказанной части может удерживаться пропорционально использованному объёму.',ready:'Реальная оплата. После подтверждения пакет будет начислен на ваш аккаунт.',failed:'Не удалось выполнить запрос. Проверьте историю перед повторной оплатой.',consent:'Подтвердите условия и начало оказания услуги.',pickBank:'Выберите банк.',paid:'Оплата подтверждена. Пакет начислен.',pending:'Заказ ожидает оплаты или подтверждения.',declined:'Платёж не выполнен. Трафик не начислен.',checking:'Проверяем оплату…',history:'Платежи',empty:'Платежей пока нет.',paidStatus:'Оплачен',notConfigured:'Реальная оплата для администраторов подготовлена. Ожидается установка LIVE-ключей Montonio.'},
en:{pricingChanged:'Pricing has changed. Refresh the page before paying.',banner:'Live Montonio payments. Administrators only. Real money will be charged.',balance:'Paid traffic balance',balanceHelp:'Purchased traffic less usage.',methods:'Available Montonio payment methods.',termsAfter:'.',early:'I request immediate service provision. If I withdraw within 14 days, the part already supplied may be charged proportionately to usage.',ready:'Live payment. Your package is credited after payment confirmation.',failed:'Request failed. Check your history before paying again.',consent:'Confirm the terms and immediate service provision.',pickBank:'Choose a bank.',paid:'Payment confirmed. Package credited.',pending:'Awaiting payment or confirmation.',declined:'Payment was not completed. No traffic credited.',checking:'Checking payment…',history:'Payments',empty:'No payments yet.',paidStatus:'Paid',notConfigured:'Administrator-only live payments are prepared. Montonio LIVE keys still need to be installed.'},
lv:{pricingChanged:'Cena ir mainījusies. Pirms apmaksas atsvaidziniet lapu.',banner:'Reāli Montonio maksājumi. Tikai administratoriem. Tiks iekasēta reāla nauda.',balance:'Apmaksāto datu atlikums',balanceHelp:'Iegādātais datu apjoms, atskaitot patēriņu.',methods:'Pieejamie Montonio maksājumu veidi.',termsAfter:'.',early:'Es pieprasu sākt pakalpojumu nekavējoties. Ja izmantoju atteikuma tiesības 14 dienu laikā, par jau sniegto daļu var ieturēt maksu proporcionāli izmantotajam apjomam.',ready:'Reāls maksājums. Paka tiks ieskaitīta pēc maksājuma apstiprinājuma.',failed:'Pieprasījums neizdevās. Pirms atkārtotas apmaksas pārbaudiet vēsturi.',consent:'Apstipriniet noteikumus un tūlītēju pakalpojuma sākšanu.',pickBank:'Izvēlieties banku.',paid:'Maksājums apstiprināts. Paka ieskaitīta.',pending:'Gaida apmaksu vai apstiprinājumu.',declined:'Maksājums nav pabeigts. Dati nav ieskaitīti.',checking:'Pārbaudām maksājumu…',history:'Maksājumi',empty:'Maksājumu vēl nav.',paidStatus:'Apmaksāts',notConfigured:'Reālie maksājumi administratoriem ir sagatavoti. Jāuzstāda Montonio LIVE atslēgas.'}
};
const paymentHosts=()=>cap?.mode==='live'?['stargate.montonio.com','checkout.montonio.com','gateway.montonio.com']:['sandbox-stargate.montonio.com','sandbox-checkout.montonio.com','sandbox-gateway.montonio.com'];
let enabled=false,busy=false,cap=null,methods=null,account=null,messageKey='',pollTimer=null;
let attempt=null;
const lang=()=>document.documentElement.lang in text?document.documentElement.lang:'en';
const t=()=>cap?.mode==='live'?{...text[lang()],...liveText[lang()],statuses:{...text[lang()].statuses,PAID:liveText[lang()].paidStatus}}:text[lang()];
const sku=()=>window.TolfBillingVolume?.getVolume()?.toString();
const method=()=>document.querySelector('[name="payment"]:checked')?.value;
const mapping={card:'cardPayments',bank:'paymentInitiation'};
const returnUrl=new URL(location.href);
const returnToken=returnUrl.searchParams.get('order-token');
const returnEnvironment=returnUrl.searchParams.has('sandboxOrder')?'sandbox':null;
const returnReference=returnUrl.searchParams.get('liveOrder')||returnUrl.searchParams.get('sandboxOrder');
// Consume return parameters once. A refresh must not replay an old payment result.
if(returnToken||returnReference){
 returnUrl.searchParams.delete('order-token');returnUrl.searchParams.delete('sandboxOrder');returnUrl.searchParams.delete('liveOrder');
 history.replaceState(null,'',returnUrl);
}
async function request(path,body,signal){
 if(cap?.mode==='live')path=path.replace('/billing/sandbox/','/billing/live/');
 const response=await fetch(API+path,{method:body?'POST':'GET',credentials:'include',cache:'no-store',headers:body?{'Content-Type':'application/json'}:{'Accept':'application/json'},...(body?{body:JSON.stringify(body)}:{}),...(signal?{signal}:{})});
 let data;try{data=await response.json();}catch{throw Error('invalid_response');}
 if(!response.ok)throw Error(data.detail||'request_failed');
 return data;
}

const recordsText={
ru:{invoice:'Нужен документ с реквизитами',invoiceHelp:'В тестовом режиме формируется подтверждение покупки с реквизитами, а не налоговый счёт.',kind:'Покупатель',individual:'Частное лицо',company:'Компания',name:'Имя и фамилия / название компании',address:'Адрес для счёта',billingCountry:'Страна в реквизитах',registration:'Регистрационный номер компании',vat:'Номер НДС (при наличии)',chooseCountry:'Выберите страну',pdf:'Скачать PDF',remaining:'Осталось',export:'Бухгалтерская выгрузка TOLF — тестовые данные',purchases:'Покупки и возвраты',movements:'Движение трафика',balances:'Остатки пакетов',fees:'Комиссии Montonio',exportNote:'Месяц по UTC. Оценка стоимости расхода не является бухгалтерской проводкой. Отсутствующая комиссия не считается нулевой.',downloadError:'Не удалось скачать документ. Повторите попытку.',refunded:'Возвращён — тест',partial:'Частично возвращён — тест'},
en:{invoice:'Add billing details to the document',invoiceHelp:'Test mode produces a purchase confirmation with billing details, not a VAT invoice.',kind:'Buyer',individual:'Individual',company:'Company',name:'Full name / company name',address:'Billing address',billingCountry:'Billing country',registration:'Company registration number',vat:'VAT number (if applicable)',chooseCountry:'Choose a country',pdf:'Download PDF',remaining:'Remaining',export:'TOLF accounting export — test data',purchases:'Purchases and refunds',movements:'Traffic movements',balances:'Package balances',fees:'Montonio fees',exportNote:'UTC month. Usage value estimates are not accounting entries. An unavailable fee is not zero.',downloadError:'Could not download the document. Please try again.',refunded:'Refunded — test',partial:'Partially refunded — test'},
lv:{invoice:'Pievienot dokumentam pircēja rekvizītus',invoiceHelp:'Testa režīmā tiek sagatavots pirkuma apstiprinājums ar rekvizītiem, nevis PVN rēķins.',kind:'Pircējs',individual:'Privātpersona',company:'Uzņēmums',name:'Vārds un uzvārds / uzņēmuma nosaukums',address:'Rēķina adrese',billingCountry:'Valsts rekvizītos',registration:'Uzņēmuma reģistrācijas numurs',vat:'PVN numurs (ja ir)',chooseCountry:'Izvēlieties valsti',pdf:'Lejupielādēt PDF',remaining:'Atlikums',export:'TOLF grāmatvedības eksports — testa dati',purchases:'Pirkumi un atmaksas',movements:'Datu kustība',balances:'Paku atlikumi',fees:'Montonio komisijas',exportNote:'Mēnesis pēc UTC. Izmantotā apjoma vērtības aplēses nav grāmatvedības ieraksti. Nezināma komisija nav nulle.',downloadError:'Dokumentu neizdevās lejupielādēt. Mēģiniet vēlreiz.',refunded:'Atmaksāts — tests',partial:'Daļēji atmaksāts — tests'}
};
const postDocumentText={
ru:{pdf:'Счёт с реквизитами (PDF)',get:'Получить счёт с реквизитами',save:'Сформировать документ',cancel:'Отмена',busy:'Формируем…',issued:'Документ с реквизитами уже выдан. Для исправления обратитесь в поддержку.',failed:'Не удалось сформировать документ. Повторите попытку.'},
en:{pdf:'Billing details document (PDF)',get:'Get an invoice with billing details',save:'Create document',cancel:'Cancel',busy:'Creating…',issued:'A document with billing details has already been issued. Contact support for corrections.',failed:'Could not create the document. Please try again.'},
lv:{pdf:'Dokuments ar rekvizītiem (PDF)',get:'Saņemt rēķinu ar rekvizītiem',save:'Sagatavot dokumentu',cancel:'Atcelt',busy:'Sagatavojam…',issued:'Dokuments ar rekvizītiem jau ir izsniegts. Labojumiem sazinieties ar atbalstu.',failed:'Dokumentu neizdevās sagatavot. Mēģiniet vēlreiz.'}
};
const historyText={
ru:{bill:'Скачать счёт',details:'Скачать счёт с реквизитами',refund:'Скачать возврат',resume:'Продолжить оплату',check:'Проверить статус',pending:'Оплата не подтверждена. Нажмите «Продолжить оплату», чтобы вернуться в Montonio и завершить её.',checking:'Проверяем подтверждение платежа. Нажмите «Проверить статус» для обновления.',closed:'Этот заказ уже нельзя оплатить. Для новой покупки выберите пакет выше.',unavailable:'Не удалось проверить статус. Повторите проверку, прежде чем оплачивать заново.',paid:'Оплата подтверждена. Пакет начислен.'},
en:{bill:'Download invoice',details:'Download invoice with billing details',refund:'Download refund document',resume:'Continue payment',check:'Check status',pending:'Payment is not confirmed. Select “Continue payment” to return to Montonio and complete it.',checking:'Awaiting payment confirmation. Select “Check status” to refresh.',closed:'This order can no longer be paid. Select a package above to start a new purchase.',unavailable:'Could not check the status. Check again before paying a second time.',paid:'Payment confirmed. The package has been credited.'},
lv:{bill:'Lejupielādēt rēķinu',details:'Lejupielādēt rēķinu ar rekvizītiem',refund:'Lejupielādēt atmaksas dokumentu',resume:'Turpināt apmaksu',check:'Pārbaudīt statusu',pending:'Apmaksa nav apstiprināta. Nospiediet “Turpināt apmaksu”, lai atgrieztos Montonio un to pabeigtu.',checking:'Gaidām maksājuma apstiprinājumu. Nospiediet “Pārbaudīt statusu”, lai atjauninātu.',closed:'Šo pasūtījumu vairs nevar apmaksāt. Jaunam pirkumam izvēlieties paku augstāk.',unavailable:'Statusu neizdevās pārbaudīt. Pirms atkārtotas apmaksas mēģiniet vēlreiz.',paid:'Apmaksa apstiprināta. Paka ir ieskaitīta.'}
};
let historyFeedbackKey='';
const paidStatuses=['PAID','PARTIALLY_REFUNDED','REFUNDED'];
const hiddenStatuses=['ABANDONED','VOIDED','DECLINED','CANCELLED','EXPIRED'];
const rt=()=>recordsText[lang()];
const trafficGb=bytes=>(bytes/1e9).toLocaleString(lang(),{minimumFractionDigits:3,maximumFractionDigits:3});
function readBuyer(){
 if(!$('billingBuyerEnabled')?.checked)return null;
 return {kind:$('billingBuyerKind').value,name:$('billingBuyerName').value.trim(),address:$('billingBuyerAddress').value.trim(),country:$('billingBuyerCountry').value,registration:$('billingBuyerRegistration').value.trim(),vatNumber:$('billingBuyerVat').value.trim()};
}
function buyerValid(){return !$('billingBuyerEnabled')?.checked||[...$('billingBuyerFields').querySelectorAll('input,select')].every(el=>el.checkValidity());}
function ensureRecordsUI(){
 const wrap=document.createElement('div');wrap.id='billingBuyer';wrap.className='billing-buyer';
 wrap.innerHTML='<label class="sandbox-check"><input id="billingBuyerEnabled" type="checkbox"><span id="billingBuyerToggle"></span></label><div id="billingBuyerFields" class="billing-buyer-fields" hidden><p id="billingBuyerHelp" class="muted"></p><label><span id="billingBuyerKindLabel"></span><select id="billingBuyerKind"><option value="individual"></option><option value="company"></option></select></label><label><span id="billingBuyerNameLabel"></span><input id="billingBuyerName" maxlength="160" autocomplete="billing name"></label><label class="billing-buyer-wide"><span id="billingBuyerAddressLabel"></span><input id="billingBuyerAddress" maxlength="400" autocomplete="billing street-address"></label><label><span id="billingBuyerCountryLabel"></span><select id="billingBuyerCountry" autocomplete="billing country"><option value=""></option></select></label><label><span id="billingBuyerRegistrationLabel"></span><input id="billingBuyerRegistration" maxlength="50"></label><label><span id="billingBuyerVatLabel"></span><input id="billingBuyerVat" maxlength="50"></label></div>';
 $('sandboxTerms').closest('label').before(wrap);
 const select=$('billingBuyerCountry');
 for(const code of methods.billingCountries||['LV','EE','LT']){const o=document.createElement('option');o.value=code;select.append(o);}
 wrap.addEventListener('input',()=>{attempt=null;update();});
 wrap.addEventListener('change',()=>{attempt=null;update();});
 if(cap.accountingExport){
  const section=document.createElement('section');section.id='billingExports';section.className='billing-card billing-exports';
  section.innerHTML='<h2 id="billingExportTitle"></h2><input id="billingExportMonth" type="month" min="2020-01" max="2099-12"><div id="billingExportLinks"></div><p id="billingExportHelp" class="muted"></p>';
  document.querySelector('.billing-history').after(section);
  $('billingExportMonth').value=new Date().toISOString().slice(0,7);
  $('billingExportMonth').addEventListener('change',renderRecordsUI);
 }
}
function renderRecordsUI(){
 if(!$('billingBuyer'))return;
 const x=rt(),buyerOn=$('billingBuyerEnabled').checked,company=$('billingBuyerKind').value==='company';
 $('billingBuyerToggle').textContent=x.invoice;$('billingBuyerHelp').textContent=x.invoiceHelp;
 $('billingBuyerFields').hidden=!buyerOn;
 for(const [id,key] of [['Kind','kind'],['Name','name'],['Address','address'],['Country','billingCountry'],['Registration','registration'],['Vat','vat']]){
  $('billingBuyer'+id+'Label').textContent=x[key];
 }
 for(const id of ['Name','Address','Country'])$('billingBuyer'+id).required=buyerOn;
 $('billingBuyerRegistration').required=buyerOn&&company;
 $('billingBuyerRegistration').closest('label').hidden=!company;
 $('billingBuyerKind').options[0].textContent=x.individual;$('billingBuyerKind').options[1].textContent=x.company;
 const country=$('billingBuyerCountry');country.options[0].textContent=x.chooseCountry;
 let names;try{names=new Intl.DisplayNames([lang()],{type:'region'});}catch{}
 for(const option of [...country.options].slice(1))option.textContent=names?names.of(option.value):option.value;
 if($('billingExports')){
  $('billingExportTitle').textContent=x.export;$('billingExportMonth').setAttribute('aria-label',x.export);
  $('billingExportHelp').textContent=x.exportNote;
  const links=$('billingExportLinks');links.replaceChildren();
  const month=$('billingExportMonth').value;
  for(const kind of ['purchases','movements','balances','fees']){
   const group=document.createElement('div');group.className='billing-export-group';
   const title=document.createElement('h3');title.textContent=x[kind];group.append(title);
   const actions=document.createElement('div');actions.className='billing-export-actions';
   for(const format of ['pdf','csv']){
    const b=document.createElement('button');b.type='button';b.className='billing-secondary secondary';b.textContent=format.toUpperCase();
    b.setAttribute('aria-label',x[kind]+' — '+format.toUpperCase());
    b.disabled=!/^20[0-9]{2}-(0[1-9]|1[0-2])$/.test(month);
    b.addEventListener('click',()=>download('/billing/sandbox/admin/export.'+format+'?month='+encodeURIComponent(month)+'&kind='+kind+(format==='pdf'?'&locale='+lang():''),'tolf-sandbox-'+month+'-'+kind+'.'+format,b));
    actions.append(b);
   }
   group.append(actions);links.append(group);
  }
 }
}
async function download(path,filename,button){
 button.disabled=true;
 try{
  const response=await fetch(API+path,{credentials:'include',cache:'no-store'});
  if(!response.ok)throw Error('download_failed');
  const blob=await response.blob(),url=URL.createObjectURL(blob),a=document.createElement('a');
  a.href=url;a.download=filename;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),30000);
 }catch{messageKey='';$('checkoutAvailability').textContent=rt().downloadError;}
 finally{button.disabled=false;}
}

function openBillingDocument(order){
 const x=rt(),px=postDocumentText[lang()];
 let dialog=$('postDocumentDialog');
 if(dialog)dialog.remove();
 dialog=document.createElement('dialog');dialog.id='postDocumentDialog';dialog.className='post-document-dialog';dialog.setAttribute('aria-labelledby','postDocumentTitle');
 const form=document.createElement('form');form.innerHTML='<h2 id="postDocumentTitle"></h2><p id="postDocumentOrder" class="muted"></p><p id="postDocumentNote" class="muted"></p><p id="postDocumentError" role="alert"></p><div class="post-document-actions"><button type="button" id="postDocumentCancel" class="billing-secondary secondary"></button><button type="submit" id="postDocumentSave" class="billing-primary primary"></button></div>';
 const fields=$('billingBuyerFields').cloneNode(true);fields.id='postBuyerFields';fields.hidden=false;
 for(const el of fields.querySelectorAll('[id]'))el.id=el.id.replace('billingBuyer','postBuyer');
 for(const el of fields.querySelectorAll('input'))el.value='';
 fields.querySelector('#postBuyerCountry').value='';fields.querySelector('#postBuyerKind').value='individual';
 fields.querySelector('#postBuyerHelp').remove();
 form.querySelector('.post-document-actions').before(fields);
 dialog.append(form);document.body.append(dialog);
 $('postDocumentTitle').textContent=px.get;$('postDocumentOrder').textContent=order.reference;
 $('postDocumentNote').textContent=x.invoiceHelp;$('postDocumentCancel').textContent=px.cancel;$('postDocumentSave').textContent=px.save;
 const close=()=>{if(dialog.close)dialog.close();dialog.remove();};
 $('postDocumentCancel').addEventListener('click',close);
 dialog.addEventListener('cancel',event=>{event.preventDefault();if(!$('postDocumentSave').disabled)close();});
 const validateKind=()=>{
  for(const id of ['Name','Address','Country'])$('postBuyer'+id).required=true;
  const company=$('postBuyerKind').value==='company';
  $('postBuyerRegistration').required=company;$('postBuyerRegistration').closest('label').hidden=!company;
 };
 $('postBuyerKind').addEventListener('change',validateKind);validateKind();
 form.addEventListener('submit',async event=>{
  event.preventDefault();if(!form.reportValidity())return;
  const save=$('postDocumentSave'),cancel=$('postDocumentCancel'),error=$('postDocumentError');
  save.disabled=true;cancel.disabled=true;save.textContent=px.busy;error.textContent='';
  const buyer={kind:$('postBuyerKind').value,name:$('postBuyerName').value.trim(),address:$('postBuyerAddress').value.trim(),country:$('postBuyerCountry').value,registration:$('postBuyerRegistration').value.trim(),vatNumber:$('postBuyerVat').value.trim()};
  try{
   const doc=await request('/billing/sandbox/orders/'+encodeURIComponent(order.reference)+'/billing-document',{buyer});
   await refreshAccount();close();
   const button=document.createElement('button');await download('/billing/sandbox/documents/'+encodeURIComponent(doc.number)+'.pdf',doc.number+'.pdf',button);
  }catch(e){error.textContent=e.message==='billing_document_already_issued'?px.issued:px.failed;save.disabled=false;cancel.disabled=false;save.textContent=px.save;}
 });
 if(dialog.showModal)dialog.showModal();else dialog.setAttribute('open','');
 $('postBuyerName').focus();
}

function ensureUI(){
 if($('sandboxConsent'))return;
 const box=document.createElement('div');box.id='sandboxConsent';box.className='sandbox-consent';
 box.innerHTML='<div id="sandboxBankFields"><label><span id="sandboxCountryLabel"></span><select id="sandboxCountry"></select></label><label><span id="sandboxBankLabel"></span><select id="sandboxBank"></select></label></div><label class="sandbox-check"><input type="checkbox" id="sandboxTerms"><span><span id="sandboxTermsBefore"></span><a id="sandboxTermsLink"></a><span id="sandboxTermsAfter"></span></span></label><label class="sandbox-check"><input type="checkbox" id="sandboxEarly"><span id="sandboxEarlyText"></span></label>';
 document.querySelector('.checkout-action').before(box);
 $('sandboxCountry').addEventListener('change',()=>{fillBanks();attempt=null;update();});
 $('sandboxBank').addEventListener('change',()=>{attempt=null;update();});
 for(const id of ['sandboxTerms','sandboxEarly'])$(id).addEventListener('change',update);
 const countries=Object.keys(methods.banks).sort();
 for(const country of countries){const o=document.createElement('option');o.value=country;o.textContent=country;$('sandboxCountry').append(o);}
 if(countries.includes('LV'))$('sandboxCountry').value='LV';
 fillBanks();ensureRecordsUI();
}
function fillBanks(){
 const select=$('sandboxBank'),previous=select.value;select.replaceChildren();
 const placeholder=document.createElement('option');placeholder.value='';placeholder.textContent=t().chooseBank;select.append(placeholder);
 for(const bank of methods.banks[$('sandboxCountry').value]||[]){const o=document.createElement('option');o.value=bank.code;o.textContent=bank.name;select.append(o);}
 if([...select.options].some(o=>o.value===previous))select.value=previous;
}
function paymentUrl(value){
 try{const u=new URL(value);if(u.protocol==='https:'&&!u.username&&!u.password&&(!u.port||u.port==='443')&&paymentHosts().includes(u.hostname))return u.href;}catch{}
 return null;
}
async function resumeOrder(order,button,continuePayment){
 button.disabled=true;
 try{
  const latest=await request('/billing/sandbox/orders/'+encodeURIComponent(order.reference)+(continuePayment?'?resume=true':''));
  if(paidStatuses.includes(latest.status))historyFeedbackKey='paid';
  else if(hiddenStatuses.includes(latest.status))historyFeedbackKey='closed';
  else historyFeedbackKey='checking';
  await refreshAccount();
  if(continuePayment&&latest.status==='PENDING'){
   const url=paymentUrl(latest.paymentUrl);
   if(url){location.assign(url);return;}
  }
 }catch{historyFeedbackKey='unavailable';showHistory();}
 finally{button.disabled=false;}
}
function renderBalance(bytes){
 const value=document.querySelector('.balance-value');value.replaceChildren();
 const parts=new Intl.NumberFormat(lang(),{minimumFractionDigits:3,maximumFractionDigits:3}).formatToParts(bytes/1e9);
 const whole=document.createElement('span');whole.className='traffic-whole';
 const fraction=document.createElement('span');fraction.className='traffic-fraction';
 for(const part of parts)(['decimal','fraction'].includes(part.type)?fraction:whole).append(document.createTextNode(part.value));
 value.append(whole,fraction,document.createTextNode(' '+(lang()==='ru'?'ГБ':'GB')));
}
function showHistory(){
 if(!account)return;
 const x=historyText[lang()];
 const section=document.querySelector('.billing-history');section.querySelector('h2').textContent=t().history;
 const old=section.querySelector('.muted');if(old)old.hidden=true;
 let feedback=$('sandboxHistoryFeedback');if(!feedback){feedback=document.createElement('p');feedback.id='sandboxHistoryFeedback';feedback.setAttribute('role','status');section.append(feedback);}
 feedback.textContent=historyFeedbackKey?x[historyFeedbackKey]:'';feedback.hidden=!historyFeedbackKey;
 let list=$('sandboxHistory');if(!list){list=document.createElement('div');list.id='sandboxHistory';section.append(list);}list.replaceChildren();
 const orders=account.orders.filter(o=>!hiddenStatuses.includes(o.status));
 if(!orders.length){list.textContent=t().empty;return;}
 for(const order of orders){
  const row=document.createElement('div');row.className='sandbox-history-row';
  const ref=document.createElement('span');ref.textContent=order.reference;
  const status=document.createElement('span');status.textContent=order.status==='REFUNDED'?rt().refunded:order.status==='PARTIALLY_REFUNDED'?rt().partial:t().statuses[order.status]||order.status;
  const amount=document.createElement('strong');amount.textContent=order.amount+' €';
  const description=document.createElement('span');description.className='sandbox-order-description';
  description.textContent=new Date(order.createdAt*1000).toLocaleString(lang())+' · '+order.gb+' GB'+(order.remainingBytes!=null?' · '+rt().remaining+': '+trafficGb(order.remainingBytes)+' GB':'');
  ref.append(document.createElement('br'),description);row.append(ref,status,amount);
  if(order.bankInvoice){
   const B=window.TolfBank,invoice=order.bankInvoice,actions=document.createElement('div');actions.className='sandbox-history-actions';
   for(const [url,label,suffix] of [[invoice.pdfUrl,B.t('download'),'.pdf'],[invoice.receiptUrl,B.t('receipt'),'-paid.pdf']]){
    if(!url)continue;const b=document.createElement('button');b.type='button';b.className='sandbox-document secondary';b.textContent=label;b.addEventListener('click',()=>download(url,invoice.number+suffix,b));actions.append(b);
   }
   status.textContent=B.t(order.status==='PAID'?'paid':'pending');ref.firstChild.textContent=invoice.number;
   const note=document.createElement('p');note.className='sandbox-pending-note';note.textContent=B.t('reference')+': '+invoice.paymentReference;
   row.append(note,actions);list.append(row);continue;
  }
  const original=(order.documents||[]).find(d=>d.kind==='purchase');
  if(original&&paidStatuses.includes(order.status)){
   const actions=document.createElement('div');actions.className='sandbox-history-actions';
   const base=document.createElement('button');base.type='button';base.className='sandbox-document secondary';base.textContent=x.bill;
   base.addEventListener('click',()=>download('/billing/sandbox/documents/'+encodeURIComponent(original.number)+'.pdf',original.number+'.pdf',base));
   const details=document.createElement('button');details.type='button';details.className='sandbox-document secondary';details.textContent=x.details;
   if(order.billingDocumentNumber)details.addEventListener('click',()=>download('/billing/sandbox/documents/'+encodeURIComponent(order.billingDocumentNumber)+'.pdf',order.billingDocumentNumber+'.pdf',details));
   else{details.classList.add('post-document-request');details.addEventListener('click',()=>openBillingDocument(order));}
   actions.append(base,details);row.append(actions);
   for(const doc of (order.documents||[]).filter(d=>d.kind==='refund')){
    const b=document.createElement('button');b.type='button';b.className='sandbox-document secondary';b.textContent=x.refund;
    b.addEventListener('click',()=>download('/billing/sandbox/documents/'+encodeURIComponent(doc.number)+'.pdf',doc.number+'.pdf',b));row.append(b);
   }
  }else if(!paidStatuses.includes(order.status)){
   const note=document.createElement('p');note.className='sandbox-pending-note';
   const resumable=order.status==='PENDING'&&paymentUrl(order.paymentUrl);
   note.textContent=resumable?x.pending:x.checking;
   const b=document.createElement('button');b.type='button';b.className='sandbox-document secondary sandbox-resume';b.textContent=resumable?x.resume:x.check;
   b.addEventListener('click',()=>resumeOrder(order,b,!!resumable));row.append(note,b);
  }
  list.append(row);
 }
}

function update(){
 if(!enabled)return;
 const x=t(),isTrial=window.TolfBillingVolume.isTrial();renderRecordsUI();
 document.documentElement.classList.add('billing-sandbox');
 document.querySelector('.preview-note').textContent=x.banner;

 $('balanceTitle').textContent=x.balance;
 renderBalance((cap?.mode==='live'?account?.balanceBytes:account?.testBalanceBytes)||0);
 if($('billingBuyer'))$('billingBuyer').hidden=cap?.mode==='live';
 document.querySelector('.balance-card .muted').textContent=x.balanceHelp;
 $('paymentPreviewNote').textContent=x.methods;
 $('sandboxConsent').hidden=isTrial;
 $('sandboxBankFields').hidden=method()!=='bank';
 $('sandboxCountryLabel').textContent=x.country;$('sandboxBankLabel').textContent=x.bank;
 $('sandboxBank').options[0].textContent=x.chooseBank;
 $('sandboxTermsBefore').textContent=x.termsBefore;$('sandboxTermsLink').textContent=x.terms;$('sandboxTermsLink').href='../terms.html?lang='+lang();
 $('sandboxTermsAfter').textContent=x.termsAfter;$('sandboxEarlyText').textContent=x.early;
 const btn=$('checkoutButton');
 btn.disabled=busy||isTrial||!sku()||!buyerValid()||!$('sandboxTerms').checked||!$('sandboxEarly').checked||!methods.methods.includes(mapping[method()])||(method()==='bank'&&!$('sandboxBank').value);
 for(const el of document.querySelectorAll('#volumeNumber,#volumeRange,[data-volume],#selectTrial,#returnToPaid'))el.disabled=busy;
 if($('bankInvoiceButton'))$('bankInvoiceButton').disabled=busy||!window.TolfBillingVolume.isValid();
 if(busy)btn.textContent=x.busy;
 $('checkoutAvailability').textContent=x[isTrial?'trial':messageKey||(busy?'busy':'ready')]||x.failed;
 for(const radio of document.querySelectorAll('[name="payment"]')){
  const available=methods.methods.includes(mapping[radio.value]);radio.closest('label').hidden=!available;radio.disabled=!available;
 }
 if(!methods.methods.includes(mapping[method()])){
  const first=document.querySelector('[name="payment"]:not(:disabled)');if(first)first.checked=true;
 }
 showHistory();
}
let accountRefreshVersion=0,activeAccountRequests=0,balanceRefreshTimer=null;
let balanceUpdatesStarted=false,balancePageActive=true;
const balanceBytes=data=>(cap?.mode==='live'?data?.balanceBytes:data?.testBalanceBytes)||0;
async function refreshAccount({quiet=false}={}){
 const version=++accountRefreshVersion,controller=new AbortController();
 const timeout=setTimeout(()=>controller.abort(),12000);
 activeAccountRequests++;
 try{
  const next=await request('/billing/sandbox/account',undefined,controller.signal);
  if(version!==accountRefreshVersion)return;
  const previous=account;account=next;
  if(!quiet){update();return;}
  // Keep checkout inputs and selection intact during background refreshes.
  if(balanceBytes(previous)!==balanceBytes(next))renderBalance(balanceBytes(next));
  if(JSON.stringify(previous?.orders)!==JSON.stringify(next.orders))showHistory();
 }finally{clearTimeout(timeout);activeAccountRequests--;}
}
function scheduleBalanceRefresh(){
 clearTimeout(balanceRefreshTimer);balanceRefreshTimer=null;
 if(!balanceUpdatesStarted||!balancePageActive||document.hidden)return;
 balanceRefreshTimer=setTimeout(refreshVisibleBalance,15000);
}
async function refreshVisibleBalance(){
 clearTimeout(balanceRefreshTimer);balanceRefreshTimer=null;
 if(!balanceUpdatesStarted||!balancePageActive||document.hidden)return;
 try{
  if(!busy&&!activeAccountRequests)await refreshAccount({quiet:true});
 }catch{
  // A network error must not replace the last confirmed balance with zero.
 }finally{scheduleBalanceRefresh();}
}
function startBalanceUpdates(){
 if(balanceUpdatesStarted)return;
 balanceUpdatesStarted=true;
 document.addEventListener('visibilitychange',refreshVisibleBalance);
 window.addEventListener('focus',refreshVisibleBalance);
 window.addEventListener('online',refreshVisibleBalance);
 window.addEventListener('pagehide',()=>{balancePageActive=false;clearTimeout(balanceRefreshTimer);balanceRefreshTimer=null;});
 window.addEventListener('pageshow',()=>{balancePageActive=true;refreshVisibleBalance();});
 scheduleBalanceRefresh();
}
async function checkOrder(reference,tries=0){
 try{
  const order=await request('/billing/sandbox/orders/'+encodeURIComponent(reference));

  messageKey=order.status==='PAID'?'paid':['ABANDONED','VOIDED','DECLINED','CANCELLED','EXPIRED'].includes(order.status)?'declined':'pending';
  await refreshAccount();
  if(messageKey==='pending'&&tries<12){clearTimeout(pollTimer);pollTimer=setTimeout(()=>checkOrder(reference,tries+1),5000);}
 }catch{messageKey='failed';update();}
}
async function checkout(){
 if(!enabled||busy||!sku())return;
 if(!$('sandboxTerms').checked||!$('sandboxEarly').checked){messageKey='consent';update();return;}
 if(method()==='bank'&&!$('sandboxBank').value){messageKey='pickBank';update();return;}
 const buyer=readBuyer();
 if(!buyerValid())return;
 const chosenVolume=sku(),quoted=window.TolfPricingCurve.quote(Number(chosenVolume));
 const signature=[chosenVolume,method(),$('sandboxCountry').value,$('sandboxBank').value,JSON.stringify(buyer)].join(':');
 if(!attempt||attempt.signature!==signature)attempt={signature,id:crypto.randomUUID()};
 busy=true;messageKey='';update();
 try{
  const order=await request('/billing/sandbox/orders',{package:chosenVolume,pricingVersion:cap.pricingVersion,method:mapping[method()],locale:lang(),bankCountry:$('sandboxCountry').value,bankCode:$('sandboxBank').value,requestId:attempt.id,termsVersion:cap.termsVersion,acceptTerms:true,startNow:true,...(buyer?{buyer}:{})});
  if(order.gb!==Number(chosenVolume)||Math.round(order.amount*100)!==quoted.cents)throw Error('pricing_changed');
  const url=new URL(order.paymentUrl);
  if(!paymentUrl(order.paymentUrl))throw Error('unsafe_payment_url');
  location.assign(url.href);
 }catch(error){
  messageKey=error.message==='pricing_changed'?'pricingChanged':error.message==='order_already_created'?'unknown':'failed';busy=false;update();refreshAccount().catch(()=>{});
 }
}
window.addEventListener('tolf:bank-invoice-created',()=>refreshAccount().catch(()=>{}));
window.addEventListener('tolf:billing-render',()=>{messageKey='';update();});
window.addEventListener('pageshow',event=>{if(event.persisted){messageKey='';historyFeedbackKey='';update();}});
for(const radio of document.querySelectorAll('[name="payment"]'))radio.addEventListener('change',()=>{messageKey='';update();});
$('checkoutButton').addEventListener('click',checkout);
(async()=>{
 try{
  cap=returnEnvironment==='sandbox'?await request('/billing/capabilities'):await request('/billing/live/capabilities');
  if(cap.mode==='live'&&!cap.enabled){document.querySelector('.preview-note').textContent=liveText[lang()].notConfigured;return;}
  if(cap.mode!=='live')cap=await request('/billing/capabilities');
  if(!cap.enabled||!['sandbox','live'].includes(cap.mode))return;
  methods=await request('/billing/sandbox/methods');
  enabled=true;ensureUI();
  // Availability comes from Montonio, not from browser sniffing.
  for(const radio of document.querySelectorAll('[name="payment"]'))radio.closest('label').hidden=!methods.methods.includes(mapping[radio.value]);
  await refreshAccount();update();startBalanceUpdates();
  if(returnToken){
   messageKey='checking';update();
   try{const checked=await request('/billing/sandbox/validate-return',{orderToken:returnToken});await checkOrder(checked.reference);}
   catch{messageKey='invalid';update();if(returnReference)await checkOrder(returnReference);}
  }else if(returnReference)await checkOrder(returnReference);
 }catch{if(enabled){messageKey='failed';update();}}
})();
})();

