'use strict';
(() => {
const copy = {
 en:{title:'Administration',subtitle:'TOLF Network Suite',back:'Back to My VPN',signIn:'Sign in with Passkey',users:'Accounts',registry:'VPN registry',audit:'Activity log',refresh:'Refresh',inventoryNote:'This page shows records from the account database. Live VPN sessions and connection controls are not connected yet.',searchLabel:'Account number, VPN username or Windows device',search:'Search',previous:'Previous',next:'Next',close:'Close',loading:'Loading…',unavailable:'Administration is not available yet.',denied:'Administrator access has not been granted to this account.',accountNumber:'Your account number',auth:'Sign in on the main page, then return here.',error:'Could not load data. Try refreshing.',empty:'No records found.',account:'Account',created:'Created',vpn:'VPN access record',devices:'Windows devices',keys:'Passkeys',open:'Details',administrator:'Administrator',protected:'Protected user',none:'None',node:'Node',source:'Source',linked:'Account link',unlinked:'Not linked',provisioned:'VPN access record',yes:'Present',no:'Absent',when:'Time',actor:'Actor',action:'Action',target:'Account ID',grant:'Administrator granted',revoke:'Administrator revoked',root:'Server console',total:'Total',of:'of',accountId:'Account ID',deviceState:'Device record',active:'Configured',provisioning:'Preparing',deleting:'Deletion pending',deleted:'Deleted',riga:'Riga',moscow:'Moscow',unknown:'Unknown',names:'Passkey names'},
 ru:{title:'Администрирование',subtitle:'TOLF Network Suite',back:'Вернуться в «Мой VPN»',signIn:'Войти с Passkey',users:'Аккаунты',registry:'Реестр VPN',audit:'Журнал действий',refresh:'Обновить',inventoryNote:'Здесь показаны записи базы аккаунтов. Данные о текущих VPN-сеансах и управление соединениями ещё не подключены.',searchLabel:'Номер аккаунта, имя пользователя VPN или устройство Windows',search:'Найти',previous:'Назад',next:'Далее',close:'Закрыть',loading:'Загрузка…',unavailable:'Администрирование пока недоступно.',denied:'Этому аккаунту ещё не предоставлены права администратора.',accountNumber:'Номер вашего аккаунта',auth:'Войдите на основной странице, затем вернитесь сюда.',error:'Не удалось загрузить данные. Попробуйте обновить.',empty:'Записей не найдено.',account:'Аккаунт',created:'Создан',vpn:'Запись доступа VPN',devices:'Устройства Windows',keys:'Passkeys',open:'Подробнее',administrator:'Администратор',protected:'Защищённый пользователь',none:'Нет',node:'Узел',source:'Источник',linked:'Связь с аккаунтом',unlinked:'Не привязан',provisioned:'Запись доступа VPN',yes:'Есть',no:'Нет',when:'Время',actor:'Кто выполнил',action:'Действие',target:'ID аккаунта',grant:'Назначен администратор',revoke:'Сняты права администратора',root:'Консоль сервера',total:'Всего',of:'из',accountId:'ID аккаунта',deviceState:'Запись устройства',active:'Настроено',provisioning:'Подготовка',deleting:'Удаление ожидает завершения',deleted:'Удалено',riga:'Рига',moscow:'Москва',unknown:'Неизвестно',names:'Названия Passkey'},
 lv:{title:'Administrēšana',subtitle:'TOLF Network Suite',back:'Atgriezties pie mana VPN',signIn:'Pierakstīties ar Passkey',users:'Konti',registry:'VPN reģistrs',audit:'Darbību žurnāls',refresh:'Atjaunināt',inventoryNote:'Šeit redzami kontu datubāzes ieraksti. Pašreizējās VPN sesijas un savienojumu vadība vēl nav pievienota.',searchLabel:'Konta numurs, VPN lietotājvārds vai Windows ierīce',search:'Meklēt',previous:'Atpakaļ',next:'Tālāk',close:'Aizvērt',loading:'Ielāde…',unavailable:'Administrēšana vēl nav pieejama.',denied:'Šim kontam vēl nav piešķirtas administratora tiesības.',accountNumber:'Jūsu konta numurs',auth:'Pierakstieties galvenajā lapā un atgriezieties šeit.',error:'Neizdevās ielādēt datus. Mēģiniet atjaunināt.',empty:'Ieraksti nav atrasti.',account:'Konts',created:'Izveidots',vpn:'VPN piekļuves ieraksts',devices:'Windows ierīces',keys:'Passkeys',open:'Informācija',administrator:'Administrators',protected:'Aizsargāts lietotājs',none:'Nav',node:'Mezgls',source:'Avots',linked:'Saite ar kontu',unlinked:'Nav piesaistīts',provisioned:'VPN piekļuves ieraksts',yes:'Ir',no:'Nav',when:'Laiks',actor:'Izpildītājs',action:'Darbība',target:'Konta ID',grant:'Piešķirtas administratora tiesības',revoke:'Atceltas administratora tiesības',root:'Servera konsole',total:'Kopā',of:'no',accountId:'Konta ID',deviceState:'Ierīces ieraksts',active:'Iestatīta',provisioning:'Sagatavošana',deleting:'Dzēšana nav pabeigta',deleted:'Dzēsta',riga:'Rīga',moscow:'Maskava',unknown:'Nezināms',names:'Passkey nosaukumi'}
};
Object.assign(copy.en,{sessions:'VPN sessions',inventoryNote:'Account and VPN access records. Current connections are shown in VPN sessions.',sessionNote:'Snapshot at the time shown for each node. Refresh to retrieve current data.',nodeError:'Could not query this node. Session count is unknown.',noSessions:'No sessions at the time of this check.',checked:'Checked',peer:'Peer identity',addresses:'Client addresses',duration:'Duration',traffic:'Traffic',received:'Received by node',sent:'Sent by node',unmatched:'No unique registry match',sessionState:'State',ESTABLISHED:'Established',CONNECTING:'Connecting',REKEYING:'Rekeying',DELETING:'Disconnecting',trafficNote:'Traffic counters cover the current CHILD SAs; they may reset on rekey. This is not lifetime usage.',backendPending:'Update the London API to display sessions.',pollBusy:'A session check is already running. Try Refresh shortly.'});
Object.assign(copy.ru,{sessions:'VPN-сеансы',inventoryNote:'Здесь показаны аккаунты и записи доступа VPN. Текущие подключения — на вкладке «VPN-сеансы».',sessionNote:'Снимок состояния на указанное для каждого узла время. Кнопка «Обновить» запрашивает новые данные.',nodeError:'Не удалось опросить узел. Количество сеансов неизвестно.',noSessions:'На момент проверки сеансов нет.',checked:'Проверено',peer:'Идентификатор клиента',addresses:'Адреса клиента',duration:'Длительность',traffic:'Трафик',received:'Принято узлом',sent:'Отправлено узлом',unmatched:'Нет однозначного совпадения в реестре',sessionState:'Состояние',ESTABLISHED:'Установлено',CONNECTING:'Подключение',REKEYING:'Обновление ключей',DELETING:'Отключение',trafficNote:'Счётчики относятся к текущим CHILD SA и могут сбрасываться при обновлении ключей. Это не трафик за всё время.',backendPending:'Для отображения сеансов обновите API на Лондоне.',pollBusy:'Опрос сеансов уже выполняется. Чуть позже нажмите «Обновить».'});
Object.assign(copy.lv,{sessions:'VPN sesijas',inventoryNote:'Konti un VPN piekļuves ieraksti. Pašreizējie savienojumi redzami cilnē “VPN sesijas”.',sessionNote:'Stāvoklis katram mezglam norādītajā laikā. Lai iegūtu jaunus datus, nospiediet “Atjaunināt”.',nodeError:'Neizdevās pārbaudīt mezglu. Sesiju skaits nav zināms.',noSessions:'Pārbaudes brīdī sesiju nav.',checked:'Pārbaudīts',peer:'Klienta identifikators',addresses:'Klienta adreses',duration:'Ilgums',traffic:'Datu apjoms',received:'Mezgls saņēmis',sent:'Mezgls nosūtījis',unmatched:'Nav viennozīmīgas atbilstības reģistrā',sessionState:'Stāvoklis',ESTABLISHED:'Izveidota',CONNECTING:'Savienojas',REKEYING:'Atslēgu atjaunināšana',DELETING:'Atvienojas',trafficNote:'Skaitītāji attiecas uz pašreizējām CHILD SA un var atiestatīties, atjauninot atslēgas. Tas nav kopējais vēsturiskais datu apjoms.',backendPending:'Lai parādītu sesijas, atjauniniet Londonas API.',pollBusy:'Sesiju pārbaude jau notiek. Drīzumā nospiediet “Atjaunināt”.'});
Object.assign(copy.en,{cpuUsage:'CPU',memoryUsage:'Memory',diskUsage:'Disk',resourcesChecked:'Resource sample',resourcesUnavailable:'Resource usage is unavailable.'});
Object.assign(copy.ru,{cpuUsage:'Процессор',memoryUsage:'Память',diskUsage:'Диск',resourcesChecked:'Нагрузка измерена',resourcesUnavailable:'Не удалось получить показатели нагрузки.'});
Object.assign(copy.lv,{cpuUsage:'Procesors',memoryUsage:'Atmiņa',diskUsage:'Disks',resourcesChecked:'Resursi izmērīti',resourcesUnavailable:'Neizdevās iegūt resursu rādītājus.'});
Object.assign(copy.ru,{target:'Объект',disconnectTest:'Отключить Test',confirmDisconnect:'Отключить VPN-сеанс Test №26? Доступ сохранится: iPhone сможет подключиться снова.',disconnected:'Сеанс Test отключён.',reconnected:'Сеанс Test отключён. Устройство уже подключилось снова.',disconnectUnknown:'Результат отключения не подтверждён. Обновите список сеансов; команда автоматически не повторяется.',disconnectStale:'Сеанс изменился или уже завершён. Обновите список.',controlUnavailable:'Не удалось подготовить отключение. Соединение не изменено.', 'session.disconnect.requested':'Запрошено отключение сеанса', 'session.disconnect.ok':'Сеанс отключён', 'session.disconnect.stale':'Отключение отклонено: сеанс изменился', 'session.disconnect.unknown':'Результат отключения неизвестен'});
Object.assign(copy.en,{target:'Target',disconnectTest:'Disconnect Test',confirmDisconnect:'Disconnect the VPN session for Test #26? Access will remain enabled: the iPhone may reconnect.',disconnected:'Test session disconnected.',reconnected:'Test session disconnected. The device has already reconnected.',disconnectUnknown:'Disconnection was not confirmed. Refresh the session list; the command is not retried automatically.',disconnectStale:'The session has changed or ended. Refresh the list.',controlUnavailable:'Could not prepare disconnection. The connection was not changed.', 'session.disconnect.requested':'Session disconnection requested', 'session.disconnect.ok':'Session disconnected', 'session.disconnect.stale':'Disconnection rejected: session changed', 'session.disconnect.unknown':'Disconnection outcome unknown'});
Object.assign(copy.lv,{target:'Mērķis',disconnectTest:'Atvienot Test',confirmDisconnect:'Atvienot Test #26 VPN sesiju? Piekļuve saglabāsies: iPhone varēs izveidot savienojumu atkārtoti.',disconnected:'Test sesija atvienota.',reconnected:'Test sesija atvienota. Ierīce jau ir izveidojusi jaunu savienojumu.',disconnectUnknown:'Atvienošana nav apstiprināta. Atjauniniet sesiju sarakstu; komanda netiek automātiski atkārtota.',disconnectStale:'Sesija ir mainījusies vai beigusies. Atjauniniet sarakstu.',controlUnavailable:'Neizdevās sagatavot atvienošanu. Savienojums nav mainīts.', 'session.disconnect.requested':'Pieprasīta sesijas atvienošana', 'session.disconnect.ok':'Sesija atvienota', 'session.disconnect.stale':'Atvienošana noraidīta: sesija mainījusies', 'session.disconnect.unknown':'Atvienošanas rezultāts nav zināms'});
async function postControl(path,body){
 const r=await fetch('https://api.tolf.is/admin/'+path,{method:'POST',credentials:'include',cache:'no-store',headers:{'Content-Type':'application/json',Accept:'application/json'},body:JSON.stringify(body)});
 if(!r.ok){const error=new Error('control');error.status=r.status;throw error;}return r.json();
}
let controlBusy=false,testControl=false;
async function disconnectTest(nodeName,id,button){
 if(controlBusy||!allowed)return;
 controlBusy=true;button.disabled=true;const own=epoch;let sent=false;
 try{
  const prepared=await postControl('disconnect/prepare',{node:nodeName,id});
  if(own!==epoch||!allowed)return;
  if(!window.confirm(t('confirmDisconnect')+'\n'+t(nodeName)+' · #'+id))return;
  if(own!==epoch||!allowed)return;
  sent=true;
  const result=await postControl('disconnect',{ticket:prepared.ticket});
  if(own!==epoch||!allowed)return;
  await load();
  if(allowed)$('status').textContent=t(result.status==='ok'?(result.reconnected?'reconnected':'disconnected'):result.status==='stale'?'disconnectStale':'disconnectUnknown');
 }catch(e){
  if(own!==epoch||!allowed)return;
  if(e.status===401||e.status===403)fail(e);
  else $('status').textContent=t(sent?'disconnectUnknown':e.status===409?'disconnectStale':'controlUnavailable');
 }finally{controlBusy=false;button.disabled=false;}
}

Object.assign(copy.ru,{accessTitle:'Доступ Test №26',accessActive:'Разрешён на Риге и Москве',accessSuspended:'Приостановлен на Риге и Москве',accessSuspending:'Приостановка не завершена',accessResuming:'Возобновление не завершено',accessUnavailable:'Не удалось проверить состояние доступа.',suspendAccess:'Приостановить доступ',resumeAccess:'Возобновить доступ',finishSuspend:'Завершить приостановку',confirmSuspend:'Приостановить доступ Test №26 на Риге и Москве? Его VPN отключится, повторное подключение будет запрещено до возобновления доступа.',confirmResume:'Возобновить доступ Test №26 на Риге и Москве? Пароль и профиль останутся прежними.',accessDone:'Изменение доступа выполнено.',accessUnknown:'Операция не подтверждена. Обновите состояние перед следующим действием.',accessStale:'Состояние уже изменилось. Проверьте обновлённые данные.',accessNote:'Действие относится только к Test №26. Аккаунт, пароль и профиль сохраняются.'});
Object.assign(copy.en,{accessTitle:'Test #26 access',accessActive:'Enabled on Riga and Moscow',accessSuspended:'Suspended on Riga and Moscow',accessSuspending:'Suspension incomplete',accessResuming:'Resumption incomplete',accessUnavailable:'Could not check access status.',suspendAccess:'Suspend access',resumeAccess:'Resume access',finishSuspend:'Complete suspension',confirmSuspend:'Suspend Test #26 on Riga and Moscow? Its VPN will disconnect and reconnection will be denied until access is resumed.',confirmResume:'Resume Test #26 on Riga and Moscow? The password and profile will stay the same.',accessDone:'Access change completed.',accessUnknown:'The operation was not confirmed. Refresh the status before taking another action.',accessStale:'The state has already changed. Review the updated status.',accessNote:'Only Test #26 is affected. The account, password and profile are preserved.'});
Object.assign(copy.lv,{accessTitle:'Test #26 piekļuve',accessActive:'Atļauta Rīgā un Maskavā',accessSuspended:'Apturēta Rīgā un Maskavā',accessSuspending:'Apturēšana nav pabeigta',accessResuming:'Atjaunošana nav pabeigta',accessUnavailable:'Neizdevās pārbaudīt piekļuves stāvokli.',suspendAccess:'Apturēt piekļuvi',resumeAccess:'Atjaunot piekļuvi',finishSuspend:'Pabeigt apturēšanu',confirmSuspend:'Apturēt Test #26 piekļuvi Rīgā un Maskavā? VPN tiks atvienots, un atkārtots savienojums būs liegts līdz piekļuves atjaunošanai.',confirmResume:'Atjaunot Test #26 piekļuvi Rīgā un Maskavā? Parole un profils paliks nemainīgi.',accessDone:'Piekļuves izmaiņas pabeigtas.',accessUnknown:'Darbība nav apstiprināta. Pirms nākamās darbības atjauniniet stāvokli.',accessStale:'Stāvoklis jau ir mainījies. Pārskatiet atjauninātos datus.',accessNote:'Darbība attiecas tikai uz Test #26. Konts, parole un profils tiek saglabāti.'});
for(const locale of ['ru','en','lv'])for(const action of ['suspend','resume']){
 const names={ru:{suspend:'Приостановка доступа',resume:'Возобновление доступа',requested:'запрошено',ok:'выполнено',unknown:'результат неизвестен',stale:'состояние изменилось'},en:{suspend:'Access suspension',resume:'Access resumption',requested:'requested',ok:'completed',unknown:'outcome unknown',stale:'state changed'},lv:{suspend:'Piekļuves apturēšana',resume:'Piekļuves atjaunošana',requested:'pieprasīta',ok:'pabeigta',unknown:'rezultāts nav zināms',stale:'stāvoklis mainījies'}}[locale];
 for(const outcome of ['requested','ok','unknown','stale'])copy[locale]['access.'+action+'.'+outcome]=names[action]+' — '+names[outcome];
}
let testAccess=false;
async function accessPanel(target){
 const own=epoch;
 const section=node('section',undefined,'admin-access');section.append(node('h2',t('accessTitle')));
 const status=node('p',t('loading')),actions=node('div',undefined,'admin-access-actions');section.append(status,actions,node('p',t('accessNote'),'admin-muted'));target.append(section);
 try{
  const state=await api('test-access');if(own!==epoch||!allowed)return;
  if(state.status!=='ok'){status.textContent=t('accessUnavailable');return;}
  status.textContent=t({active:'accessActive',suspended:'accessSuspended',suspending:'accessSuspending',resuming:'accessResuming'}[state.state]||'accessUnavailable');
  for(const action of state.state==='active'?['suspend']:state.state==='suspended'?['resume']:['suspend','resume']){
   const button=node('button',t(action==='resume'?'resumeAccess':state.state==='active'?'suspendAccess':'finishSuspend'),action==='suspend'?'admin-access-suspend':'secondary');button.type='button';
   button.addEventListener('click',async()=>{
    if(controlBusy||own!==epoch||!allowed)return;
    if(!window.confirm(t(action==='suspend'?'confirmSuspend':'confirmResume')))return;
    controlBusy=true;actions.querySelectorAll('button').forEach(b=>b.disabled=true);status.textContent=t('loading');
    try{
     const result=await postControl('test-access',{action,revision:state.revision});
     if(own!==epoch||!allowed)return;
     await load();if(allowed)$('status').textContent=t(result.status==='ok'?'accessDone':result.status==='stale'?'accessStale':'accessUnknown');
    }catch(e){if(own===epoch&&allowed){if(e.status===401||e.status===403)fail(e);else status.textContent=t('accessUnknown');}}
    finally{controlBusy=false;}
   });actions.append(button);
  }
 }catch(e){if(own===epoch&&allowed){if(e.status===401||e.status===403)fail(e);else status.textContent=t('accessUnavailable');}}
}

const $ = id => document.getElementById(id);
let lang;
try { lang=localStorage.getItem('tolfLanguage'); } catch {}
if(!copy[lang])lang=navigator.language.toLowerCase().startsWith('ru')?'ru':navigator.language.toLowerCase().startsWith('lv')?'lv':'en';
let tab='users',offset=0,total=0,epoch=0,detailEpoch=0,allowed=false,hiddenSince=0;
const t=key=>copy[lang][key]||copy.en[key]||key;
const node=(tag,text,cls)=>{const el=document.createElement(tag);if(text!==undefined)el.textContent=String(text);if(cls)el.className=cls;return el;};
const date=value=>{const d=new Date(value);return Number.isNaN(d.valueOf())?'—':d.toLocaleString(lang==='ru'?'ru-RU':lang==='lv'?'lv-LV':'en-GB');};
async function api(path) {
 const r=await fetch('https://api.tolf.is/admin/'+path,{credentials:'include',cache:'no-store',headers:{Accept:'application/json'}});
 if(!r.ok){const e=new Error('request');e.status=r.status;throw e;}return r.json();
}
function clearData(){epoch++;detailEpoch++;$('results').replaceChildren();$('detailContent').replaceChildren();$('detail').hidden=true;$('status').textContent='';}
function gate(message){allowed=false;clearData();$('workspace').hidden=true;$('gate').hidden=false;$('gateMessage').textContent=message;}
function fail(e){if(e.status===401)gate(t('auth'));else if(e.status===403)gate(t('denied'));else $('status').textContent=t(e.status===429?'pollBusy':e.status===404&&tab==='sessions'?'backendPending':'error');}
function language(){document.documentElement.lang=lang;document.title='TOLF — '+t('title');document.querySelectorAll('[data-text]').forEach(el=>el.textContent=t(el.dataset.text));document.querySelectorAll('[data-lang]').forEach(el=>el.setAttribute('aria-pressed',String(el.dataset.lang===lang)));}
function table(headers, target=$('results')){const wrapper=node('div',undefined,'admin-table-wrap'),table=node('table',undefined,'admin-table'),head=node('thead'),row=node('tr');headers.forEach(k=>row.append(node('th',t(k))));head.append(row);const body=node('tbody');table.append(head,body);wrapper.append(table);target.append(wrapper);return body;}
function showUsers(data){const body=table(['account','vpn','devices','keys','created','open']);for(const u of data.users){const row=node('tr'),account=node('td',u.number==null?u.id:'#'+u.number);if(u.isAdmin)account.append(node('small',t('administrator')));if(u.protected)account.append(node('small',t('protected')));const access=node('td');if(!u.access.length)access.textContent=t('none');for(const a of u.access){access.append(node('div',a.username),node('small',t(a.server)));}const action=node('td'),button=node('button',t('open'),'secondary');button.type='button';button.addEventListener('click',()=>detail(u.id));action.append(button);row.append(account,access,node('td',u.windowsDevices),node('td',u.passkeys),node('td',date(u.createdAt)),action);body.append(row);}}
function showRegistry(data){const body=table(['account','vpn','linked','provisioned','source']);for(const u of data.records){const row=node('tr');row.append(node('td','#'+u.number),node('td',u.username||'—'),node('td',u.accountId||t('unlinked'),'admin-id'),node('td',u.provisioned?t('yes'):t('no')),node('td',u.source||'—'));body.append(row);}}
function showAudit(data){const body=table(['when','actor','action','target']);for(const e of data.events){const row=node('tr');row.append(node('td',date(e.createdAt)),node('td',e.actor==='root'?t('root'):e.actor),node('td',e.action==='admin.grant'?t('grant'):e.action==='admin.revoke'?t('revoke'):t(e.action)),node('td',e.target,'admin-id'));body.append(row);}}
function duration(value){if(value==null)return '—';const n=Math.floor(value);return Math.floor(n/3600)+':'+String(Math.floor(n/60)%60).padStart(2,'0')+':'+String(n%60).padStart(2,'0');}
function bytes(value){const units=['B','KiB','MiB','GiB','TiB'];let n=value,i=0;while(n>=1024&&i<units.length-1){n/=1024;i++;}return n.toLocaleString(lang,{maximumFractionDigits:i?1:0})+' '+units[i];}
function showNodeMetrics(metrics,section){
 if(metrics?.status!=='ok'){
  section.append(node('p',t('resourcesUnavailable'),'admin-muted'));
  return;
 }
 const used=(value,total)=>bytes(value)+' / '+bytes(total)+' ('+Math.round(value/total*100)+'%)';
 const items=[
  ['cpuUsage',metrics.cpuPercent+'%'],
  ['memoryUsage',used(metrics.memoryUsedBytes,metrics.memoryTotalBytes)],
  ['diskUsage',used(metrics.diskUsedBytes,metrics.diskTotalBytes)]
 ];
 const grid=node('div',undefined,'admin-resources');
 for(const [label,value] of items){
  const card=node('div',undefined,'admin-resource');
  card.append(node('span',t(label),'admin-resource-label'),node('strong',value));
  grid.append(card);
 }
 section.append(node('p',t('resourcesChecked')+': '+date(metrics.observedAt),'admin-muted'),grid);
}
function showSessions(data){
 if(testAccess)accessPanel($('results'));
 for(const result of data.nodes){
  const section=node('section',undefined,'admin-node');section.dataset.node=result.node;
  section.append(node('h2',t(result.node)));$('results').append(section);
  showNodeMetrics(result.metrics,section);
  if(result.status!=='ok'){section.append(node('p',t('nodeError'),'admin-node-error'));continue;}
  section.append(node('p',t('checked')+': '+date(result.observedAt),'admin-muted'));
  if(!result.sessions.length){section.append(node('p',t('noSessions')));continue;}
  const body=table(['account','peer','addresses','sessionState','duration','traffic'],section);
  for(const session of result.sessions){
   const row=node('tr');const match=session.account;
   const account=node('td',match?(match.number==null?match.accountId:'#'+match.number):t('unmatched'));
   if(match?.accountId){const button=node('button',t('open'),'secondary');button.type='button';button.addEventListener('click',()=>detail(match.accountId));account.append(button);}
   if(testControl&&match?.number===26&&match.accountId==='0888048c-ac6e-44d2-8aed-9857aa31e9ed'&&session.identity==='user_0888048cac6e44d28aed9857aa31e9ed'&&session.state==='ESTABLISHED'){
    const button=node('button',t('disconnectTest'),'admin-disconnect');button.type='button';button.addEventListener('click',()=>disconnectTest(result.node,session.id,button));account.append(button);
   }
   const peer=node('td',session.identity||'—');peer.append(node('small','#'+session.id));
   const addresses=node('td',session.remoteHost||'—');addresses.append(node('small',session.virtualAddresses.join(', ')));
   const traffic=node('td',t('received')+': '+bytes(session.bytesIn));traffic.append(node('small',t('sent')+': '+bytes(session.bytesOut)));
   row.append(account,peer,addresses,node('td',t(session.state||'unknown')),node('td',duration(session.establishedSeconds)),traffic);body.append(row);
  }
 }
 $('results').append(node('p',t('trafficNote'),'admin-muted'));
}
async function load(){if(!allowed)return;const own=++epoch;detailEpoch++;$('detail').hidden=true;$('detailContent').replaceChildren();$('results').replaceChildren();$('status').textContent=t('loading');$('pagination').hidden=true;$('searchForm').hidden=tab!=='users';$('inventoryNote').textContent=t(tab==='sessions'?'sessionNote':'inventoryNote');document.querySelectorAll('[data-tab]').forEach(el=>el.setAttribute('aria-pressed',String(el.dataset.tab===tab)));
 try{const query=new URLSearchParams({offset:String(offset),limit:'50'});if(tab==='users')query.set('q',$('search').value.trim());const data=await api(tab+(['audit','sessions'].includes(tab)?'':'?'+query));if(own!==epoch||!allowed)return;$('status').textContent='';if(tab==='sessions'){showSessions(data);return;}total=tab==='audit'?data.events.length:data.total;if(!total){$('results').append(node('p',t('empty')));return;}if(tab==='users')showUsers(data);else if(tab==='registry')showRegistry(data);else showAudit(data);$('pageLabel').textContent=tab==='audit'?t('total')+': '+total:(offset+1)+'–'+Math.min(offset+50,total)+' '+t('of')+' '+total;$('pagination').hidden=false;$('previous').hidden=tab==='audit';$('next').hidden=tab==='audit';$('previous').disabled=offset===0;$('next').disabled=offset+50>=total;
 }catch(e){if(own===epoch)fail(e);}}
async function detail(id){const own=++detailEpoch;$('detail').hidden=true;$('detailContent').replaceChildren();try{const u=await api('users/'+encodeURIComponent(id));if(own!==detailEpoch||!allowed)return;$('detailTitle').textContent=t('account')+' '+(u.number==null?u.id:'#'+u.number);const content=$('detailContent');content.append(node('p',t('accountId')+': '+u.id,'admin-id'),node('p',t('names')+': '+(u.passkeyNames.filter(Boolean).join(', ')||t('none'))),node('h3',t('devices')));if(!u.devices.length)content.append(node('p',t('none')));for(const d of u.devices){const box=node('div',undefined,'admin-device');box.append(node('strong',d.name),node('p',t(d.server)+' · '+(d.username||'—')),node('p',t('deviceState')+': '+t(d.state),'admin-muted'));content.append(box);}$('detail').hidden=false;$('detail').scrollIntoView({block:'nearest'});}catch(e){if(own===detailEpoch)fail(e);}}
async function start(){const own=++epoch;try{const me=await api('me');if(own!==epoch)return;if(!me.isAdmin){gate(t('denied')+(me.number==null?'':' '+t('accountNumber')+': '+me.number+'.'));return;}allowed=true;testAccess=me.features?.testAccess===true;testControl=me.features?.testDisconnect===true;const hasSessions=me.features?.sessions===true;$('sessionsTab').hidden=!hasSessions;if(tab==='sessions'&&!hasSessions)tab='users';$('gate').hidden=true;$('workspace').hidden=false;await load();}catch(e){if(own!==epoch)return;gate(e.status===401?t('auth'):e.status===404||e.status===503?t('unavailable'):t('error'));}}
document.querySelectorAll('[data-lang]').forEach(el=>el.addEventListener('click',()=>{lang=el.dataset.lang;try{localStorage.setItem('tolfLanguage',lang);}catch{}language();clearData();start();}));
document.querySelectorAll('[data-tab]').forEach(el=>el.addEventListener('click',()=>{tab=el.dataset.tab;offset=0;load();}));
$('searchForm').addEventListener('submit',e=>{e.preventDefault();offset=0;load();});$('refresh').addEventListener('click',()=>{clearData();start();});$('previous').addEventListener('click',()=>{offset=Math.max(0,offset-50);load();});$('next').addEventListener('click',()=>{offset+=50;load();});$('closeDetail').addEventListener('click',()=>{detailEpoch++;$('detail').hidden=true;$('detailContent').replaceChildren();});
// Revalidate the session after returning from another tab, including sign-out elsewhere.
document.addEventListener('visibilitychange',()=>{if(document.hidden){hiddenSince=Date.now();clearData();}else if(hiddenSince){hiddenSince=0;start();}});
window.addEventListener('pageshow',e=>{if(e.persisted){clearData();start();}});
language();$('gateMessage').textContent=t('loading');start();
})();
