(() => {
'use strict';
const API='https://api.tolf.is', $=id=>document.getElementById(id);
const text={
ru:{banner:'Тестовый режим Montonio. Реальные деньги не списываются. Тестовые гигабайты не используются для VPN.',balance:'Тестовый остаток трафика',balanceHelp:'Отдельный тестовый баланс. Рабочий трафик аккаунта не изменяется.',methods:'Способы оплаты получены от Montonio для тестового магазина.',country:'Страна банка',bank:'Банк',chooseBank:'Выберите банк',termsBefore:'Я принимаю ',terms:'условия сервиса',termsAfter:' для тестового заказа.',early:'Прошу начать оказание услуги сразу. При отказе в течение 14 дней стоимость уже оказанной части может удерживаться пропорционально использованному объёму. Сейчас это только тест.',ready:'Sandbox: платёж без списания реальных денег.',busy:'Открываем Montonio…',failed:'Не удалось выполнить тестовый запрос. Попробуйте обновить страницу.',consent:'Подтвердите условия и начало оказания услуги для тестового заказа.',pickBank:'Выберите банк для тестового платежа.',paid:'Тестовый платёж подтверждён. Тестовый пакет начислен.',pending:'Ожидаем подтверждение тестового платежа.',declined:'Тестовый платёж не выполнен. Трафик не начислен.',checking:'Проверяем результат тестового платежа…',history:'Тестовые платежи',empty:'Тестовых заказов пока нет.',reference:'Заказ',status:'Статус',amount:'Сумма',trial:'Пробный пакет пока не активируется. Можно проверить оплату пакета 50, 200 или 500 ГБ.',resume:'Продолжить',invalid:'Результат возврата не подтверждён. Проверяем заказ по серверным данным.',unknown:'Результат запроса пока неизвестен. Проверьте историю перед повторной оплатой.',statuses:{CREATING:'Создаётся',UNKNOWN:'Проверяется',PENDING:'Ожидает оплаты',PAID:'Оплачен — тест',ABANDONED:'Не завершён',VOIDED:'Отменён',DECLINED:'Отклонён',CANCELLED:'Отменён',EXPIRED:'Истёк',AUTHORIZED:'Авторизован'}},
en:{banner:'Montonio test mode. No real money is charged. Test gigabytes cannot be used for VPN.',balance:'Test traffic balance',balanceHelp:'Separate test balance. Your live traffic is not affected.',methods:'Payment methods supplied by Montonio for the sandbox store.',country:'Bank country',bank:'Bank',chooseBank:'Choose a bank',termsBefore:'I accept the ',terms:'terms of service',termsAfter:' for this test order.',early:'I request immediate service provision. If I withdraw within 14 days, the part already supplied may be charged proportionately to usage. This is currently only a test.',ready:'Sandbox: no real money is charged.',busy:'Opening Montonio…',failed:'The test request failed. Please refresh the page and try again.',consent:'Confirm the terms and immediate service provision for this test order.',pickBank:'Choose a bank for the test payment.',paid:'Test payment confirmed. The test package has been credited.',pending:'Waiting for test payment confirmation.',declined:'Test payment was not completed. No traffic credited.',checking:'Checking the test payment…',history:'Test payments',empty:'No test orders yet.',reference:'Order',status:'Status',amount:'Amount',trial:'Trial activation is not available yet. You can test a 50, 200 or 500 GB purchase.',resume:'Continue',invalid:'The return result could not be validated. Checking server-side order data.',unknown:'The request outcome is not yet known. Check the history before paying again.',statuses:{CREATING:'Creating',UNKNOWN:'Checking',PENDING:'Awaiting payment',PAID:'Paid — test',ABANDONED:'Abandoned',VOIDED:'Voided',DECLINED:'Declined',CANCELLED:'Cancelled',EXPIRED:'Expired',AUTHORIZED:'Authorized'}},
lv:{banner:'Montonio testa režīms. Reāla nauda netiek iekasēta. Testa gigabaitus nevar izmantot VPN.',balance:'Testa datu atlikums',balanceHelp:'Atsevišķs testa atlikums. Reālie konta dati netiek mainīti.',methods:'Montonio testa veikalam pieejamie maksājumu veidi.',country:'Bankas valsts',bank:'Banka',chooseBank:'Izvēlieties banku',termsBefore:'Es piekrītu ',terms:'pakalpojuma noteikumiem',termsAfter:' šim testa pasūtījumam.',early:'Es pieprasu sākt pakalpojumu nekavējoties. Ja izmantoju atteikuma tiesības 14 dienu laikā, par jau sniegto daļu var ieturēt maksu proporcionāli izmantotajam apjomam. Pašlaik tas ir tikai tests.',ready:'Sandbox: reāla nauda netiek iekasēta.',busy:'Atveram Montonio…',failed:'Testa pieprasījums neizdevās. Atsvaidziniet lapu un mēģiniet vēlreiz.',consent:'Apstipriniet noteikumus un tūlītēju pakalpojuma sākšanu testa pasūtījumam.',pickBank:'Izvēlieties banku testa maksājumam.',paid:'Testa maksājums apstiprināts. Testa paka ir ieskaitīta.',pending:'Gaidām testa maksājuma apstiprinājumu.',declined:'Testa maksājums nav pabeigts. Dati nav ieskaitīti.',checking:'Pārbaudām testa maksājumu…',history:'Testa maksājumi',empty:'Testa pasūtījumu vēl nav.',reference:'Pasūtījums',status:'Statuss',amount:'Summa',trial:'Izmēģinājuma aktivizēšana vēl nav pieejama. Var pārbaudīt 50, 200 vai 500 GB pirkumu.',resume:'Turpināt',invalid:'Atgriešanās rezultāts nav apstiprināts. Pārbaudām servera datus.',unknown:'Pieprasījuma rezultāts vēl nav zināms. Pirms atkārtotas apmaksas pārbaudiet vēsturi.',statuses:{CREATING:'Tiek veidots',UNKNOWN:'Pārbaude',PENDING:'Gaida apmaksu',PAID:'Apmaksāts — tests',ABANDONED:'Nav pabeigts',VOIDED:'Atcelts',DECLINED:'Noraidīts',CANCELLED:'Atcelts',EXPIRED:'Beidzies',AUTHORIZED:'Autorizēts'}}
};
let enabled=false,busy=false,cap=null,methods=null,account=null,messageKey='',pollTimer=null;
let attempt=null;
const lang=()=>document.documentElement.lang in text?document.documentElement.lang:'en';
const t=()=>text[lang()];
const sku=()=>document.querySelector('[name="package"]:checked')?.value;
const method=()=>document.querySelector('[name="payment"]:checked')?.value;
const mapping={card:'cardPayments',bank:'paymentInitiation',apple:'applePay',google:'googlePay'};
const backMapping={cardPayments:'card',paymentInitiation:'bank',applePay:'apple',googlePay:'google'};
const returnUrl=new URL(location.href);
const returnToken=returnUrl.searchParams.get('order-token');
const returnReference=returnUrl.searchParams.get('sandboxOrder');
// Do not leave signed order data in browser history or outgoing referrers.
if(returnToken){returnUrl.searchParams.delete('order-token');history.replaceState(null,'',returnUrl);}
async function request(path,body){
 const response=await fetch(API+path,{method:body?'POST':'GET',credentials:'include',cache:'no-store',headers:body?{'Content-Type':'application/json'}:{'Accept':'application/json'},...(body?{body:JSON.stringify(body)}:{})});
 let data;try{data=await response.json();}catch{throw Error('invalid_response');}
 if(!response.ok)throw Error(data.detail||'request_failed');
 return data;
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
 fillBanks();
}
function fillBanks(){
 const select=$('sandboxBank'),previous=select.value;select.replaceChildren();
 const placeholder=document.createElement('option');placeholder.value='';placeholder.textContent=t().chooseBank;select.append(placeholder);
 for(const bank of methods.banks[$('sandboxCountry').value]||[]){const o=document.createElement('option');o.value=bank.code;o.textContent=bank.name;select.append(o);}
 if([...select.options].some(o=>o.value===previous))select.value=previous;
}
function showHistory(){
 if(!account)return;
 const section=document.querySelector('.billing-history');section.querySelector('h2').textContent=t().history;
 const old=section.querySelector('.muted');if(old)old.hidden=true;
 let list=$('sandboxHistory');if(!list){list=document.createElement('div');list.id='sandboxHistory';section.append(list);}list.replaceChildren();
 if(!account.orders.length){list.textContent=t().empty;return;}
 for(const order of account.orders){
  const row=document.createElement('div');row.className='sandbox-history-row';
  const ref=document.createElement('span');ref.textContent=order.reference;
  const status=document.createElement('span');status.textContent=t().statuses[order.status]||order.status;
  const amount=document.createElement('strong');amount.textContent=order.amount+' €';
  row.append(ref,status,amount);
  if(order.paymentUrl){try{const u=new URL(order.paymentUrl);if(u.protocol==='https:'&&['sandbox-stargate.montonio.com','sandbox-checkout.montonio.com'].includes(u.hostname)){const link=document.createElement('a');link.href=u.href;link.textContent=t().resume;row.append(link);}}catch{}}
  list.append(row);
 }
}
function update(){
 if(!enabled)return;
 const x=t(),isTrial=!sku();
 document.documentElement.classList.add('billing-sandbox');
 document.querySelector('.preview-note').textContent=x.banner;
 $('balanceTitle').textContent=x.balance;
 document.querySelector('.balance-value').textContent=((account?.testBalanceBytes||0)/1e9).toLocaleString(lang())+' '+(lang()==='ru'?'ГБ':'GB');
 document.querySelector('.balance-card .muted').textContent=x.balanceHelp;
 $('paymentPreviewNote').textContent=x.methods;
 $('sandboxConsent').hidden=isTrial;
 $('sandboxBankFields').hidden=method()!=='bank';
 $('sandboxCountryLabel').textContent=x.country;$('sandboxBankLabel').textContent=x.bank;
 $('sandboxBank').options[0].textContent=x.chooseBank;
 $('sandboxTermsBefore').textContent=x.termsBefore;$('sandboxTermsLink').textContent=x.terms;$('sandboxTermsLink').href='../terms.html?lang='+lang();
 $('sandboxTermsAfter').textContent=x.termsAfter;$('sandboxEarlyText').textContent=x.early;
 const btn=$('checkoutButton');
 btn.disabled=busy||isTrial||!$('sandboxTerms').checked||!$('sandboxEarly').checked||!methods.methods.includes(mapping[method()])||(method()==='bank'&&!$('sandboxBank').value);
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
async function refreshAccount(){account=await request('/billing/sandbox/account');update();}
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
 const signature=[sku(),method(),$('sandboxCountry').value,$('sandboxBank').value].join(':');
 if(!attempt||attempt.signature!==signature)attempt={signature,id:crypto.randomUUID()};
 busy=true;messageKey='';update();
 try{
  const order=await request('/billing/sandbox/orders',{package:sku(),method:mapping[method()],locale:lang(),bankCountry:$('sandboxCountry').value,bankCode:$('sandboxBank').value,requestId:attempt.id,termsVersion:cap.termsVersion,acceptTerms:true,startNow:true});
  const url=new URL(order.paymentUrl);
  if(url.protocol!=='https:'||!['sandbox-stargate.montonio.com','sandbox-checkout.montonio.com'].includes(url.hostname))throw Error('unsafe_payment_url');
  location.assign(url.href);
 }catch(error){
  messageKey=error.message==='order_already_created'?'unknown':'failed';busy=false;update();refreshAccount().catch(()=>{});
 }
}
window.addEventListener('tolf:billing-render',update);
for(const radio of document.querySelectorAll('[name="payment"]'))radio.addEventListener('change',()=>{messageKey='';update();});
$('checkoutButton').addEventListener('click',checkout);
(async()=>{
 try{
  cap=await request('/billing/capabilities');
  if(!cap.enabled||cap.mode!=='sandbox')return;
  methods=await request('/billing/sandbox/methods');
  enabled=true;ensureUI();
  // Availability comes from Montonio, not from browser sniffing.
  for(const radio of document.querySelectorAll('[name="payment"]'))radio.closest('label').hidden=!methods.methods.includes(mapping[radio.value]);
  await refreshAccount();update();
  if(returnToken){
   messageKey='checking';update();
   try{const checked=await request('/billing/sandbox/validate-return',{orderToken:returnToken});await checkOrder(checked.reference);}
   catch{messageKey='invalid';update();if(returnReference)await checkOrder(returnReference);}
  }else if(returnReference)await checkOrder(returnReference);
 }catch{if(enabled){messageKey='failed';update();}}
})();
})();
