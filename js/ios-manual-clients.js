/* iOS manual clients share the existing IKEv2/Cisco controls without cloning them. */
(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const parent = $('vpnCard')?.querySelector('.card-content');
  if (!parent || !globalThis.TolfShadowrocketConfig) return;
  const words = {
    ru:{native:'Встроенный VPN',nativeHelp:'IKEv2 · без отдельного приложения',ciscoHelp:'AnyConnect · Cisco Secure Client',srHelp:'AnyConnect · три сервера одним файлом',loading:'Проверяем данные аккаунта…',accessTitle:'Доступ VPN',accessHelp:'Сначала создайте доступ VPN в разделе встроенного VPN. Затем вернитесь к настройке Shadowrocket.',accessOpen:'Открыть встроенный VPN',accountTitle:'Создайте логин и пароль',accountHelp:'Вы вошли с ключом доступа. Добавьте логин и пароль к этому же аккаунту для подключения Shadowrocket.',username:'Логин личного кабинета',newUsername:'Логин',password:'Пароль личного кабинета',newPassword:'Пароль',repeat:'Повторите пароль',loginHelp:'3–32 символа: латинские буквы, цифры, точка, дефис или подчёркивание.',passwordHelp:'От 15 до 128 символов.',generate:'Сгенерировать пароль',show:'Показать',hide:'Скрыть',set:'Задать логин и пароль',saved:'Логин и пароль добавлены к вашему аккаунту.',saveCredentials:'Скачать логин и пароль',plain:'Необязательно. В файле будут адрес сайта, логин и пароль. Пароль записан открытым текстом — храните файл в защищённом месте.',configTitle:'Настройки Shadowrocket',installHelp:'Установите Shadowrocket из App Store. Приложение приобретается отдельно.',install:'Установить Shadowrocket',installed:'Shadowrocket установлен',configHelp:'В файл входят три сервера, DNS TOLF и готовые правила. Сервер выбирается на вкладке Home.',prepare:'Получить настройки Shadowrocket',ready:'Файл настроек готов',share:'Открыть или сохранить файл',download:'Скачать файл',back:'Изменить настройки файла',filePrivate:'Файл настроек содержит пароль. Передавайте его только на свои устройства.',sync:'После первого задания или изменения пароля его применение на серверах занимает до минуты.',manualPassword:'Для этого пароля автоматический перенос в конфигурацию не поддерживается. Можно импортировать файл без пароля и указать его в каждом из трёх серверов Shadowrocket.',manualAccept:'Подготовить файл без пароля; я введу его в Shadowrocket',manualStep:'Откройте ⓘ у каждого из трёх серверов и укажите пароль личного кабинета.',steps:['Сохраните TOLF_Shadowrocket.conf в «Файлы» и откройте через «Поделиться» → Shadowrocket. Также можно импортировать его из Config → «Из облака».','На вкладке Config выберите файл TOLF и нажмите «Использовать конфигурацию».','Установите Global Routing → Config.','На Home выберите TOLF_Moscow, TOLF_Riga или TOLF_New_York и включите соединение.'],working:'Подготовка…',mismatch:'Пароли не совпадают.',error:'Не удалось выполнить действие. Повторите попытку.',invalid_username:'Проверьте логин: 3–32 латинских символа, первый — буква или цифра.',invalid_password:'Длина пароля — от 15 до 128 символов.',weak_password:'Выберите менее предсказуемый пароль или сгенерируйте его.',username_taken:'Этот логин уже занят.',invalid_credentials:'Неверный пароль личного кабинета.',authentication_required:'Сеанс завершён. Войдите в аккаунт снова.',account_password_exists:'Логин и пароль уже заданы. Введите действующий пароль — он не был изменён.',account_changed:'Аккаунт изменился в другой вкладке. Обновите страницу.',too_many_attempts:'Слишком много попыток. Повторите через 15 минут.',try_later:'Повторите через несколько секунд.',unavailable:'Настройка временно недоступна. Повторите попытку позже.',fileRequested:'Открытие или сохранение файла запрошено.',retry:'Повторить'},
    en:{native:'Built-in VPN',nativeHelp:'IKEv2 · no separate app',ciscoHelp:'AnyConnect · Cisco Secure Client',srHelp:'AnyConnect · three servers in one file',loading:'Checking your account…',accessTitle:'VPN access',accessHelp:'First create VPN access under Built-in VPN, then return to Shadowrocket setup.',accessOpen:'Open built-in VPN',accountTitle:'Create a username and password',accountHelp:'You signed in with a passkey. Add a username and password to this same account to connect with Shadowrocket.',username:'Account username',newUsername:'Username',password:'Account password',newPassword:'Password',repeat:'Repeat password',loginHelp:'3–32 Latin letters, numbers, dots, hyphens or underscores.',passwordHelp:'15–128 characters.',generate:'Generate password',show:'Show',hide:'Hide',set:'Set username and password',saved:'Username and password added to your account.',saveCredentials:'Download username and password',plain:'Optional. The file contains the website address, username and password. The password is plain text; keep the file in a secure place.',configTitle:'Shadowrocket settings',installHelp:'Install Shadowrocket from the App Store. The app is purchased separately.',install:'Install Shadowrocket',installed:'Shadowrocket is installed',configHelp:'One file includes three servers, TOLF DNS and routing rules. Choose the server on Home.',prepare:'Get Shadowrocket settings',ready:'Configuration file is ready',share:'Open or save file',download:'Download file',back:'Edit file settings',filePrivate:'The configuration file contains your password. Transfer it only to your own devices.',sync:'After first setting or changing your password, allow up to one minute for it to apply on the servers.',manualPassword:'Automatic transfer of this password into the configuration is not supported. Import the file without a password and enter it in each of the three Shadowrocket servers.',manualAccept:'Prepare a file without a password; I will enter it in Shadowrocket',manualStep:'Open ⓘ for each of the three servers and enter your account password.',steps:['Save TOLF_Shadowrocket.conf in Files and open it with Share → Shadowrocket. You can also import it from Config → Import from Cloud.','In Config, select the TOLF file and choose Use Configuration.','Set Global Routing → Config.','On Home, select TOLF_Moscow, TOLF_Riga or TOLF_New_York and connect.'],working:'Preparing…',mismatch:'Passwords do not match.',error:'Could not complete the action. Please try again.',invalid_username:'Use 3–32 Latin letters, numbers, dots, hyphens or underscores; start with a letter or number.',invalid_password:'Use 15–128 characters.',weak_password:'Choose a less predictable password or generate one.',username_taken:'This username is already taken.',invalid_credentials:'Incorrect account password.',authentication_required:'Your session has expired. Sign in again.',account_password_exists:'A username and password already exist. Enter the current password; it has not been changed.',account_changed:'The account changed in another tab. Reload this page.',too_many_attempts:'Too many attempts. Try again in 15 minutes.',try_later:'Try again in a few seconds.',unavailable:'Setup is temporarily unavailable. Please try again later.',fileRequested:'Opening or saving the file was requested.',retry:'Retry'},
    lv:{native:'Iebūvētais VPN',nativeHelp:'IKEv2 · bez atsevišķas lietotnes',ciscoHelp:'AnyConnect · Cisco Secure Client',srHelp:'AnyConnect · trīs serveri vienā failā',loading:'Pārbaudām konta datus…',accessTitle:'VPN piekļuve',accessHelp:'Vispirms izveidojiet VPN piekļuvi sadaļā Iebūvētais VPN, pēc tam atgriezieties pie Shadowrocket iestatīšanas.',accessOpen:'Atvērt iebūvēto VPN',accountTitle:'Izveidojiet lietotājvārdu un paroli',accountHelp:'Jūs pieteicāties ar piekļuves atslēgu. Pievienojiet lietotājvārdu un paroli šim pašam kontam, lai savienotos ar Shadowrocket.',username:'Konta lietotājvārds',newUsername:'Lietotājvārds',password:'Konta parole',newPassword:'Parole',repeat:'Atkārtojiet paroli',loginHelp:'3–32 latīņu burti, cipari, punkti, defises vai pasvītrojumi.',passwordHelp:'15–128 rakstzīmes.',generate:'Ģenerēt paroli',show:'Rādīt',hide:'Slēpt',set:'Iestatīt lietotājvārdu un paroli',saved:'Lietotājvārds un parole pievienoti jūsu kontam.',saveCredentials:'Lejupielādēt lietotājvārdu un paroli',plain:'Pēc izvēles. Failā būs vietnes adrese, lietotājvārds un parole. Parole ir vienkāršā tekstā; glabājiet failu drošā vietā.',configTitle:'Shadowrocket iestatījumi',installHelp:'Instalējiet Shadowrocket no App Store. Lietotne jāiegādājas atsevišķi.',install:'Instalēt Shadowrocket',installed:'Shadowrocket ir instalēts',configHelp:'Vienā failā ir trīs serveri, TOLF DNS un maršrutēšanas noteikumi. Serveri izvēlieties cilnē Home.',prepare:'Saņemt Shadowrocket iestatījumus',ready:'Iestatījumu fails ir gatavs',share:'Atvērt vai saglabāt failu',download:'Lejupielādēt failu',back:'Mainīt faila iestatījumus',filePrivate:'Iestatījumu failā ir parole. Pārsūtiet to tikai uz savām ierīcēm.',sync:'Pēc paroles pirmās iestatīšanas vai maiņas tās piemērošana serveros aizņem līdz minūtei.',manualPassword:'Šīs paroles automātiska pārnešana konfigurācijā netiek atbalstīta. Importējiet failu bez paroles un ievadiet to katrā no trim Shadowrocket serveriem.',manualAccept:'Sagatavot failu bez paroles; ievadīšu to Shadowrocket',manualStep:'Atveriet ⓘ pie katra no trim serveriem un ievadiet konta paroli.',steps:['Saglabājiet TOLF_Shadowrocket.conf lietotnē Files un atveriet ar Share → Shadowrocket. To var arī importēt sadaļā Config → Import from Cloud.','Cilnē Config izvēlieties TOLF failu un nospiediet Use Configuration.','Iestatiet Global Routing → Config.','Cilnē Home izvēlieties TOLF_Moscow, TOLF_Riga vai TOLF_New_York un savienojieties.'],working:'Sagatavo…',mismatch:'Paroles nesakrīt.',error:'Darbība neizdevās. Mēģiniet vēlreiz.',invalid_username:'Izmantojiet 3–32 latīņu burtus, ciparus, punktus, defises vai pasvītrojumus; sāciet ar burtu vai ciparu.',invalid_password:'Izmantojiet 15–128 rakstzīmes.',weak_password:'Izvēlieties grūtāk uzminamu paroli vai ģenerējiet to.',username_taken:'Šis lietotājvārds jau ir aizņemts.',invalid_credentials:'Nepareiza konta parole.',authentication_required:'Sesija ir beigusies. Piesakieties vēlreiz.',account_password_exists:'Lietotājvārds un parole jau ir iestatīti. Ievadiet pašreizējo paroli; tā nav mainīta.',account_changed:'Konts mainījās citā cilnē. Pārlādējiet lapu.',too_many_attempts:'Pārāk daudz mēģinājumu. Mēģiniet pēc 15 minūtēm.',try_later:'Mēģiniet pēc dažām sekundēm.',unavailable:'Iestatīšana īslaicīgi nav pieejama. Mēģiniet vēlāk.',fileRequested:'Faila atvēršana vai saglabāšana ir pieprasīta.',retry:'Mēģināt vēlreiz'}
  };
  const tr = key => (words[document.documentElement.lang] || words.en)[key] || words.en[key] || key;
  const shared = document.createElement('div'); shared.id='iosManualShared';
  for (const item of [...parent.children]) if (!item.classList.contains('card-topline')) shared.append(item);
  const menu=document.createElement('div'); menu.id='iosManualClients'; menu.hidden=true;
  const panels={};
  for (const [id,title,description] of [['native','native','nativeHelp'],['cisco','Cisco Secure Client','ciscoHelp'],['shadowrocket','Shadowrocket','srHelp']]) {
    const section=document.createElement('section');section.className='ios-manual-client';section.dataset.iosClient=id;
    const button=document.createElement('button');button.type='button';button.className='ios-manual-client-head';button.dataset.iosClientSelect=id;
    button.setAttribute('aria-expanded','false');button.setAttribute('aria-controls','iosManualBody-'+id);
    const text=document.createElement('span');text.className='ios-manual-client-copy';
    const name=document.createElement('strong');name.dataset.srText=title;const help=document.createElement('small');help.dataset.srText=description;
    const arrow=document.createElement('span');arrow.className='ios-manual-chevron';arrow.setAttribute('aria-hidden','true');
    text.append(name,help);button.append(text,arrow);
    const body=document.createElement('div');body.id='iosManualBody-'+id;body.className='ios-manual-client-body';body.hidden=true;
    section.append(button,body);menu.append(section);panels[id]={button,body};
    button.addEventListener('click',()=>selectClient(client===id?null:id));
  }
  parent.append(menu,shared);
  const sr=document.createElement('section');sr.id='shadowrocketSetup';
  sr.innerHTML=`
    <p id="srLoading" role="status" data-sr-text="loading" hidden></p>
    <div id="srNeedsAccess" hidden><h3 data-sr-text="accessTitle"></h3><p data-sr-text="accessHelp"></p><button id="srOpenNative" class="secondary" type="button" data-sr-text="accessOpen"></button></div>
    <form id="srAccountForm" class="sr-form" hidden>
      <h3 data-sr-text="accountTitle"></h3><p class="sr-note" data-sr-text="accountHelp"></p>
      <label class="sr-field"><span data-sr-text="newUsername"></span><input id="srNewUsername" type="text" autocomplete="username" autocapitalize="none" spellcheck="false" required minlength="3" maxlength="32" pattern="[A-Za-z0-9][A-Za-z0-9_.-]{2,31}"><small class="sr-note" data-sr-text="loginHelp"></small></label>
      <label class="sr-field"><span data-sr-text="newPassword"></span><span class="sr-password-row"><input id="srNewPassword" type="password" autocomplete="new-password" required minlength="15" maxlength="128"><button type="button" class="secondary" data-sr-toggle="srNewPassword" data-sr-text="show"></button></span><small class="sr-note" data-sr-text="passwordHelp"></small></label>
      <div class="sr-actions"><button id="srGenerate" type="button" class="secondary" data-sr-text="generate"></button></div>
      <label class="sr-field"><span data-sr-text="repeat"></span><input id="srRepeatPassword" type="password" autocomplete="new-password" required minlength="15" maxlength="128"></label>
      <div class="sr-actions"><button class="primary" type="submit" data-sr-text="set"></button></div>
    </form>
    <div id="srConfigPanel" hidden>
      <div id="srSavedCredentials" class="sr-saved" hidden><p data-sr-text="saved"></p><div class="sr-actions"><button id="srSaveCredentials" type="button" class="secondary" data-sr-text="saveCredentials"></button></div><p class="sr-note" data-sr-text="plain"></p></div>
      <h3 data-sr-text="configTitle"></h3><p class="sr-note" data-sr-text="installHelp"></p>
      <div class="sr-actions"><a class="button-link secondary" href="https://apps.apple.com/app/id932747118" target="_blank" rel="noopener noreferrer" data-sr-text="install"></a></div>
      <label class="sr-check"><input id="srInstalled" type="checkbox"><span data-sr-text="installed"></span></label>
      <form id="srConfigForm" class="sr-form">
        <label class="sr-field"><span data-sr-text="username"></span><input id="srUsername" type="text" autocomplete="username" readonly></label>
        <label class="sr-field"><span data-sr-text="password"></span><span class="sr-password-row"><input id="srPassword" type="password" autocomplete="current-password" required minlength="15" maxlength="128"><button type="button" class="secondary" data-sr-toggle="srPassword" data-sr-text="show"></button></span></label>
        <div id="srManualPassword" hidden><p class="sr-note" data-sr-text="manualPassword"></p><label class="sr-check"><input id="srManualPasswordAccept" type="checkbox"><span data-sr-text="manualAccept"></span></label></div>
        <ul class="sr-servers"><li>TOLF_Moscow</li><li>TOLF_Riga</li><li>TOLF_New_York</li></ul>
        <p class="sr-note" data-sr-text="configHelp"></p><p class="sr-note" data-sr-text="sync"></p>
        <div class="sr-actions"><button id="srPrepare" class="primary" type="submit" disabled data-sr-text="prepare"></button></div>
      </form>
    </div>
    <div id="srReady" hidden><h3 data-sr-text="ready"></h3><p>TOLF_Shadowrocket.conf</p>
      <div class="sr-actions"><button id="srShareConfig" class="primary" type="button" data-sr-text="share"></button><button id="srDownloadConfig" class="secondary" type="button" data-sr-text="download"></button></div>
      <p id="srFilePrivate" class="sr-note" data-sr-text="filePrivate"></p><p id="srManualStep" data-sr-text="manualStep" hidden></p><ol id="srInstructions"></ol>
      <div class="sr-actions"><button id="srBack" type="button" class="secondary" data-sr-text="back"></button></div>
    </div>
    <p id="srMessage" class="sr-message" role="status" aria-live="polite"></p>
    <button id="srRetry" class="secondary" type="button" data-sr-text="retry" hidden></button>`;
  panels.shadowrocket.body.append(sr);
  let client=null, account=null, login=null, loaded=false, loading=false, busy=false, epoch=0;
  let savedCredentials=null, verifiedPassword=null, configFile=null, manualFile=false, messageKey='';
  const active=()=>currentPlatform==='ios'&&document.body.classList.contains('manual-setup-open');
  function announce(key,error=false) {messageKey=key;$('srMessage').textContent=key?tr(key):'';$('srMessage').classList.toggle('error',error);}
  function selectClient(id) {
    client=id;
    if (id) $(id==='native'?'vpnTransportIkev2':'vpnTransportAnyConnect').click();
    render();window.dispatchEvent(new Event('tolf:manual-client-change'));
    if(id==='shadowrocket'&&account&&!loaded&&!loading)loadPasswordAccount();
  }
  window.tolfIosManual={active,client:()=>client,select:selectClient};
  function render() {
    const isActive=active();document.body.classList.toggle('ios-manual-setup',isActive);
    document.body.dataset.iosManualClient=isActive?(client||''):'';
    menu.hidden=!isActive;
    if(isActive&&client&&client!=='shadowrocket') {if(shared.parentElement!==panels[client].body)panels[client].body.append(shared);}
    else if(shared.parentElement!==parent)parent.append(shared);
    shared.hidden=isActive&&(!client||client==='shadowrocket');
    for(const [id,panel] of Object.entries(panels)) {panel.body.hidden=!isActive||id!==client;panel.button.setAttribute('aria-expanded',String(isActive&&id===client));}
    menu.querySelectorAll('[data-sr-text]').forEach(el=>el.textContent=tr(el.dataset.srText));
    for(const button of sr.querySelectorAll('[data-sr-toggle]'))button.textContent=tr($(button.dataset.srToggle).type==='password'?'show':'hide');
    $('srInstructions').replaceChildren(...tr('steps').map(text=>{const li=document.createElement('li');li.textContent=text;return li;}));
    const configured=account&&typeof lastVpnState!=='undefined'&&lastVpnState?.configured;
    $('srLoading').hidden=!loading;
    $('srNeedsAccess').hidden=!account||Boolean(configured)||loading;
    $('srAccountForm').hidden=!configured||!loaded||Boolean(login)||Boolean(configFile);
    $('srConfigPanel').hidden=!configured||!loaded||!login||Boolean(configFile);
    $('srSavedCredentials').hidden=!savedCredentials;
    $('srReady').hidden=!configured||!configFile;
    const needsManual=$('srPassword').value.length>0&&!TolfShadowrocketConfig.supportsPassword($('srPassword').value);
    $('srManualPassword').hidden=!needsManual;
    $('srPrepare').disabled=busy||!$('srInstalled').checked||$('srPassword').value.length<15||(needsManual&&!$('srManualPasswordAccept').checked);
    let canShare=false;
    try {canShare=Boolean(configFile&&typeof navigator.share==='function'&&typeof navigator.canShare==='function'&&navigator.canShare({files:[configFile]}));} catch {}
    $('srShareConfig').hidden=!canShare;
    $('srFilePrivate').hidden=manualFile;
    $('srManualStep').hidden=!manualFile;
    if(messageKey)$('srMessage').textContent=tr(messageKey);
    for(const form of [$('srAccountForm'),$('srConfigForm')])for(const item of form.querySelectorAll('input,button'))if(item.id!=='srPrepare')item.disabled=busy;
  }
  async function loadPasswordAccount() {
    if(!account||loading)return;const token=epoch;loading=true;announce('');$('srRetry').hidden=true;render();
    try {
      const [caps,data]=await Promise.all([apiRequest('/password/capabilities',{cache:'no-store'}),apiRequest('/password/account',{cache:'no-store'})]);
      if(token!==epoch)return;
      if(!caps.verifyAccountPassword||!caps.createOnly)throw new Error('unavailable');
      if(typeof data.enabled!=='boolean'||data.enabled&&!/^[a-z0-9][a-z0-9_.-]{2,31}$/.test(data.username))throw new Error('unavailable');
      login=data.enabled?data.username:null;loaded=true;$('srUsername').value=login||'';
    }catch(error){if(token===epoch){announce(words.en[error.message]?error.message:'error',true);$('srRetry').hidden=false;}}
    finally{if(token===epoch){loading=false;render();}}
  }
  function clearSecrets() {
    savedCredentials=null;verifiedPassword=null;configFile=null;manualFile=false;
    for(const id of ['srNewUsername','srNewPassword','srRepeatPassword','srPassword','srUsername']){$(id).value='';if($(id).type==='text'&&id.includes('Password'))$(id).type='password';}
    $('srInstalled').checked=false;$('srManualPasswordAccept').checked=false;
  }
  function setAccount(data) {
    if(account?.userId===data?.userId&&account){account=data;render();return;}
    epoch++;clearSecrets();account=data?.authenticated?data:null;login=null;loaded=false;loading=false;busy=false;announce('');$('srRetry').hidden=true;render();
    if(account&&active()&&client==='shadowrocket')loadPasswordAccount();
  }
  function download(file) {
    const url=URL.createObjectURL(file),link=document.createElement('a');link.href=url;link.download=file.name;
    document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),10000);
  }
  $('srAccountForm').addEventListener('submit',async event=>{
    event.preventDefault();if(busy||!account||!loaded||login||!event.currentTarget.reportValidity())return;
    const password=$('srNewPassword').value;if(password!==$('srRepeatPassword').value){announce('mismatch',true);return;}
    const token=epoch;busy=true;announce('working');render();
    try{
      const data=await apiRequest('/password/set',{method:'POST',body:JSON.stringify({username:$('srNewUsername').value.toLowerCase(),password,createOnly:true})});
      if(token!==epoch)return;
      login=data.username;savedCredentials={username:login,password};verifiedPassword=password;
      $('srUsername').value=login;$('srPassword').value=password;$('srNewPassword').value='';$('srRepeatPassword').value='';announce('');
    }catch(error){if(token===epoch){if(error.message==='account_password_exists'){loaded=false;await loadPasswordAccount();}announce(words.en[error.message]?error.message:'error',true);}}
    finally{if(token===epoch){busy=false;render();}}
  });
  $('srConfigForm').addEventListener('submit',async event=>{
    event.preventDefault();if(busy||$('srPrepare').disabled||!event.currentTarget.reportValidity())return;
    const token=epoch,password=$('srPassword').value,username=login;
    busy=true;announce('working');render();
    try{
      const current=await apiRequest('/password/account',{cache:'no-store'});
      if(token!==epoch)return;if(!current.enabled||current.username!==username)throw new Error('account_changed');
      if(verifiedPassword!==password){const result=await apiRequest('/password/verify',{method:'POST',body:JSON.stringify({password})});if(token!==epoch)return;if(result.username!==username)throw new Error('account_changed');verifiedPassword=password;}
      manualFile=!TolfShadowrocketConfig.supportsPassword(password);
      const content=TolfShadowrocketConfig.build(username,password,manualFile);
      configFile=new File([content],'TOLF_Shadowrocket.conf',{type:'text/plain;charset=utf-8'});announce('');
    }catch(error){if(token===epoch)announce(words.en[error.message]?error.message:'error',true);}
    finally{if(token===epoch){busy=false;render();}}
  });
  $('srSaveCredentials').addEventListener('click',()=>{if(savedCredentials)download(new File(['\uFEFF',TolfShadowrocketConfig.credentialsText(savedCredentials.username,savedCredentials.password)],'TOLF_account.txt',{type:'text/plain;charset=utf-8'}));});
  $('srShareConfig').addEventListener('click',async()=>{if(!configFile)return;try{await navigator.share({files:[configFile]});}catch(error){if(error.name!=='AbortError')announce('error',true);}});
  $('srDownloadConfig').addEventListener('click',()=>{if(configFile){download(configFile);announce('fileRequested');}});
  $('srBack').addEventListener('click',()=>{configFile=null;announce('');render();});
  $('srRetry').addEventListener('click',loadPasswordAccount);
  $('srOpenNative').addEventListener('click',()=>selectClient('native'));
  $('srInstalled').addEventListener('change',render);$('srManualPasswordAccept').addEventListener('change',render);
  $('srPassword').addEventListener('input',()=>{$('srManualPasswordAccept').checked=false;render();});
  $('srGenerate').addEventListener('click',()=>{const chars='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_';const value=Array.from(crypto.getRandomValues(new Uint8Array(24)),n=>chars[n&63]).join('');$('srNewPassword').value=value;$('srRepeatPassword').value=value;$('srNewPassword').type='text';render();});
  for(const button of sr.querySelectorAll('[data-sr-toggle]'))button.addEventListener('click',()=>{const field=$(button.dataset.srToggle);field.type=field.type==='password'?'text':'password';render();});
  window.addEventListener('tolf:account-state',event=>setAccount(event.detail));
  window.addEventListener('tolf:vpn-state',render);
  window.addEventListener('vpnplatformchange',()=>{if(currentPlatform!=='ios')$('srInstalled').checked=false;render();window.dispatchEvent(new Event('tolf:manual-client-change'));});
  window.addEventListener('vpntransportchange',render);
  window.addEventListener('pagehide',()=>{epoch++;clearSecrets();loaded=false;login=null;loading=false;busy=false;render();});
  window.addEventListener('pageshow',event=>{if(event.persisted&&account&&active()&&client==='shadowrocket')loadPasswordAccount();});
  new MutationObserver(render).observe(document.body,{attributes:true,attributeFilter:['class']});
  new MutationObserver(render).observe(document.documentElement,{attributes:true,attributeFilter:['lang']});
  setAccount(window.tolfAccountState||null);render();
})();
