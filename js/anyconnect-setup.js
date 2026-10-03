// Guest delivery: the fragment is a bearer secret; no account or browser storage.
(() => {
  const root = document.getElementById("anyConnectAccess");
  const language = document.getElementById("setupLanguage");
  const token = window.location.hash.slice(1);
  const endpoint = "https://api.tolf.is/oc/access/setup/" + encodeURIComponent(token);
  const TEXT = {
    ru: {title:"Настройка доступа", intro:"Вход в аккаунт не требуется. Выполните шаги на устройстве, где будет работать VPN.", loading:"Загружаем доступ…", failed:"Ссылка истекла, уже использована или доступ отозван. Попросите отправителя создать новую ссылку.", retry:"Не удалось связаться с сервером. Повторите попытку.", install:"Установите Cisco Secure Client", app:"Установить Cisco Secure Client", connect:"Добавьте соединение", control:"В настройках Cisco Secure Client выберите External Control → Prompt. Затем вернитесь сюда и добавьте соединение. VPN пока не включайте.", add:"Добавить в AnyConnect", cert:"Получите сертификат для импорта в AnyConnect", prepare:"Получить сертификат", before:"После добавления соединения вернитесь сюда и получите сертификат.", password:"Пароль импорта", passwordHelp:"Этот пароль понадобится при импорте данного сертификата в приложение Cisco Secure Client (AnyConnect).", copy:"Скопировать пароль", copied:"Пароль скопирован", import:"Импортировать в AnyConnect", download:"Скачать сертификат .p12", expires:"На импорт отведено 2 часа. Используйте либо импорт в приложение, либо скачивание файла. Страницу пока не обновляйте: установочная ссылка уже использована.", manual:"Для ручного импорта на iPhone или iPad откройте файл .p12 в «Файлах» и через «Поделиться» передайте в Cisco Secure Client. На Windows импортируйте файл в сертификаты текущего пользователя → Личное. Используйте пароль импорта.", enable:"Включите VPN", finish:"Включите созданное соединение в Cisco Secure Client. Если предлагается группа, оставьте группу по умолчанию. Маршрутизация уже задана владельцем доступа.", expired:"Время импорта истекло. Попросите отправителя создать новую ссылку."},
    en: {title:"Access setup", intro:"No sign-in is required. Follow these steps on the device that will use VPN.", loading:"Loading access…", failed:"The link expired, was already used or access was revoked. Ask the sender for a new link.", retry:"Unable to reach the server. Please try again.", install:"Install Cisco Secure Client", app:"Install Cisco Secure Client", connect:"Add the connection", control:"In Cisco Secure Client settings select External Control → Prompt. Return here and add the connection. Do not enable VPN yet.", add:"Add to AnyConnect", cert:"Get the certificate for import into AnyConnect", prepare:"Get certificate", before:"After adding the connection, return here and get the certificate.", password:"Import password", passwordHelp:"Use this password when importing this certificate into Cisco Secure Client (AnyConnect).", copy:"Copy password", copied:"Password copied", import:"Import into AnyConnect", download:"Download .p12 certificate", expires:"Import within 2 hours. Choose either app import or file download. Do not reload yet: the setup link has already been used.", manual:"For manual import on iPhone or iPad, open the .p12 file in Files and share it to Cisco Secure Client. On Windows import it into Current User → Personal certificates. Use the import password.", enable:"Enable VPN", finish:"Enable the new connection in Cisco Secure Client. Keep the default group if asked. Routing is already configured by the access owner.", expired:"The import time expired. Ask the sender for a new link."},
    lv: {title:"Piekļuves iestatīšana", intro:"Nav jāpiesakās kontā. Veiciet šīs darbības ierīcē, kurā izmantosiet VPN.", loading:"Ielādē piekļuvi…", failed:"Saite ir beigusies, jau izmantota vai piekļuve atsaukta. Lūdziet sūtītājam jaunu saiti.", retry:"Neizdevās sazināties ar serveri. Mēģiniet vēlreiz.", install:"Instalējiet Cisco Secure Client", app:"Instalēt Cisco Secure Client", connect:"Pievienojiet savienojumu", control:"Cisco Secure Client iestatījumos izvēlieties External Control → Prompt. Atgriezieties šeit un pievienojiet savienojumu. VPN vēl neieslēdziet.", add:"Pievienot AnyConnect", cert:"Saņemiet sertifikātu importēšanai AnyConnect", prepare:"Saņemt sertifikātu", before:"Pēc savienojuma pievienošanas atgriezieties šeit un saņemiet sertifikātu.", password:"Importēšanas parole", passwordHelp:"Šī parole būs vajadzīga, importējot šo sertifikātu lietotnē Cisco Secure Client (AnyConnect).", copy:"Kopēt paroli", copied:"Parole nokopēta", import:"Importēt AnyConnect", download:"Lejupielādēt .p12 sertifikātu", expires:"Importējiet 2 stundu laikā. Izvēlieties importu lietotnē vai faila lejupielādi. Nepārlādējiet lapu: instalēšanas saite jau izmantota.", manual:"iPhone vai iPad atveriet .p12 failu lietotnē Files un kopīgojiet to ar Cisco Secure Client. Windows importējiet failu pašreizējā lietotāja personīgajos sertifikātos. Izmantojiet importēšanas paroli.", enable:"Ieslēdziet VPN", finish:"Ieslēdziet jauno savienojumu Cisco Secure Client. Ja tiek prasīta grupa, atstājiet noklusējuma grupu. Maršrutēšanu jau iestatījis piekļuves īpašnieks.", expired:"Importēšanas laiks beidzies. Lūdziet sūtītājam jaunu saiti."}
  };
  const ua = navigator.userAgent || "";
  const platform = /Android/i.test(ua) ? "android" : /Windows/i.test(ua) ? "windows" : "ios";
  let info = null, grant = null, busy = false, message = "", feedback = false, cached = null, timer = null;
  const c = () => TEXT[language.value] || TEXT.ru;
  let connectionConfirmed = false;
  let certificateImported = false;
  let ingressId = 'moscow';
  const INGRESS_TEXT = {
    ru:{label:'Точка входа',moscow:'Москва',riga:'Рига',help:'Соединения Москвы и Риги используют один сертификат этого доступа. Для смены точки входа выключите VPN в Cisco Secure Client, выберите другое соединение и включите VPN.'},
    en:{label:'Entry point',moscow:'Moscow',riga:'Riga',help:'Moscow and Riga connections use the same access certificate. To switch entry points, disconnect VPN in Cisco Secure Client, select the other connection and reconnect.'},
    lv:{label:'Ieejas punkts',moscow:'Maskava',riga:'Rīga',help:'Maskavas un Rīgas savienojumi izmanto vienu šīs piekļuves sertifikātu. Lai mainītu ieejas punktu, Cisco Secure Client atvienojiet VPN, izvēlieties otru savienojumu un pievienojieties vēlreiz.'}
  };
  const connections = () => {
    const points = Array.isArray(info?.connections) ? info.connections.filter(item => item.id === 'moscow' && item.host === 'oc.tolf.is:4443' || item.id === 'riga' && item.host === 'oc-riga.tolf.is:443') : [];
    return points.length ? points : [{id:'moscow',host:info?.server || 'oc.tolf.is:4443',connectionUri:info?.connectionUri}];
  };
  const connection = () => connections().find(item => item.id === ingressId) || connections()[0];
  const CERTIFICATE_TEXT = {
    ru:{already:"Сертификат уже импортирован", done:"✓ Сертификат уже импортирован", help:"Если сертификат этого доступа уже установлен в Cisco Secure Client, повторный импорт не нужен. Выберите его в настройках нового соединения."},
    en:{already:"Certificate already imported", done:"✓ Certificate already imported", help:"If this access certificate is already installed in Cisco Secure Client, no new import is needed. Select it in the new connection settings."},
    lv:{already:"Sertifikāts jau importēts", done:"✓ Sertifikāts jau importēts", help:"Ja šīs piekļuves sertifikāts jau ir instalēts Cisco Secure Client, atkārtota importēšana nav vajadzīga. Izvēlieties to jaunā savienojuma iestatījumos."}
  };
  const STEP_TEXT = {
    ru:{confirm:"Соединение добавлено", blocked:"Сначала добавьте соединение в AnyConnect и подтвердите завершение предыдущего шага."},
    en:{confirm:"Connection added", blocked:"First add the connection in AnyConnect and confirm completion of the previous step."},
    lv:{confirm:"Savienojums pievienots", blocked:"Vispirms pievienojiet savienojumu AnyConnect un apstipriniet iepriekšējā soļa pabeigšanu."}
  };
  const el = (tag, text, cls) => { const node=document.createElement(tag); if(text!=null)node.textContent=text; if(cls)node.className=cls; return node; };
  function button(text, action, primary=false) { const node=el("button",text,"oc-action "+(primary?"primary":"secondary"));node.type="button";node.disabled=busy;node.addEventListener("click",action);return node; }
  function link(text, href, primary=true) { const node=el("a",text,"button-link oc-action "+(primary?"primary":"secondary")+" oc-full");node.href=href;node.referrerPolicy="no-referrer";return node; }
  async function request(url, method="GET") {
    const controller=new AbortController(), timeout=setTimeout(()=>controller.abort(),30000);
    try { const response=await fetch(url,{method,credentials:"omit",cache:"no-store",signal:controller.signal,headers:{Accept:"application/json"}});if(!response.ok){const error=new Error("HTTP");error.status=response.status;throw error;}return await response.json(); }
    finally { clearTimeout(timeout); }
  }
  function clearPackage() { if(cached)URL.revokeObjectURL(cached);cached=null; }
  async function claim() {
    if(busy||grant||!connectionConfirmed)return;certificateImported=false;busy=true;message="";render();
    try { grant=await request(endpoint+"/claim","POST"); }
    catch(error) { message=error.status===410?c().failed:c().retry; }
    finally { busy=false;render(); }
  }
  async function download() {
    if(busy||!grant)return;const current=grant;busy=true;message="";render();
    try {
      if(!cached){const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),30000);
        try { const response=await fetch(current.certificateUrl,{credentials:"omit",cache:"no-store",signal:controller.signal});if(!response.ok)throw Error("Download");const bytes=await response.arrayBuffer();if(grant!==current)return;cached=URL.createObjectURL(new Blob([bytes],{type:"application/octet-stream"})); }
        finally { clearTimeout(timeout); }
      }
      if(grant!==current)return;const a=el("a");a.href=cached;a.download="TOLF-AnyConnect.p12";a.style.display="none";document.body.append(a);a.click();a.remove();
    } catch {message=c().retry;} finally {busy=false;render();}
  }
  async function copyPassword() {
    const current=grant;if(!current)return;
    try {await navigator.clipboard.writeText(current.password);if(grant!==current)return;feedback=true;render();clearTimeout(timer);timer=setTimeout(()=>{feedback=false;render();},2000);}
    catch {message=c().retry;render();}
  }
  function render() {
    document.documentElement.lang=language.value;root.replaceChildren();const t=c();
    if(!info){root.append(el("p",message||t.loading,"oc-note"));if(message===t.retry)root.append(button(t.prepare,load));return;}
    root.append(el("h3",t.title+" — «"+info.label+"»"),el("p",t.intro,"oc-note"));
    root.append(el("h4","1. "+t.install));
    const app=platform==="ios"?"https://apps.apple.com/app/id1135064690":platform==="android"?"https://play.google.com/store/apps/details?id=com.cisco.anyconnect.vpn.android.avf":"https://www.cisco.com/c/en/us/support/security/secure-client-5/model.html";
    root.append(link(t.app,app,false));root.append(el("h4","2. "+t.connect));
    if(connections().length>1){
      const copy=INGRESS_TEXT[language.value]||INGRESS_TEXT.en,field=el('div',null,'oc-ingress-field'),label=el('label',copy.label),select=el('select');
      label.htmlFor='ocIngress';select.id='ocIngress';select.disabled=busy;
      for(const point of connections()){const option=el('option',copy[point.id]);option.value=point.id;select.append(option);}
      select.value=connection().id;select.addEventListener('change',()=>{if(busy)return;ingressId=select.value;connectionConfirmed=false;render();});
      field.append(label,select);root.append(field,el('p',copy.help));
    }
    if(connectionConfirmed){
      const doneText={ru:["✓ Соединение добавлено","Добавить заново"],en:["✓ Connection added","Add again"],lv:["✓ Savienojums pievienots","Pievienot vēlreiz"]}[language.value]||["✓ Connection added","Add again"];
      const completed=el("div",null,"oc-connection-completed"),status=el("div",doneText[0],"oc-connection-done");status.setAttribute("role","status");
      const again=button(doneText[1],()=>{connectionConfirmed=false;certificateImported=false;render();});again.className="oc-action oc-retry-link";completed.append(status,again);root.append(completed);
    }
    const step=STEP_TEXT[language.value]||STEP_TEXT.ru;
    if(!connectionConfirmed){
      const actions=el("div",null,"oc-actions oc-connection-actions");
      if(platform!=="windows"){root.append(el("p",t.control));actions.append(link(t.add,connection().connectionUri));}
      else root.append(el("p",connection().host));
      actions.append(button(step.confirm,()=>{connectionConfirmed=true;render();}));root.append(actions);
    }
    const certificateText=CERTIFICATE_TEXT[language.value]||CERTIFICATE_TEXT.en;
    root.append(el("h4","3. "+t.cert+" — «"+info.label+"»"),el("p",connectionConfirmed?certificateText.help:step.blocked,"oc-note"));
    if(certificateImported&&connectionConfirmed){root.append(el("p",certificateText.done,"oc-certificate-done"));const prepare=button(t.prepare,claim,true);prepare.className+=" oc-prepare";root.append(prepare);}
    else if(!grant||!connectionConfirmed){
      const actions=el("div",null,"oc-actions oc-certificate-actions"),prepare=button(t.prepare,claim,true);prepare.className+=" oc-prepare";prepare.disabled ||= !connectionConfirmed;
      const already=button(certificateText.already,()=>{if(!connectionConfirmed)return;certificateImported=true;grant=null;clearPackage();feedback=false;clearTimeout(timer);render();});already.disabled ||= !connectionConfirmed;actions.append(prepare,already);root.append(actions);
    }
    else {
      root.append(el("p",t.password),el("p",t.passwordHelp));const row=el("div",null,"oc-password-row");row.append(el("span",grant.password,"oc-secret"));
      const control=el("span",null,"oc-copy-control"),icon=button("",copyPassword);icon.className="oc-copy";icon.setAttribute("aria-label",t.copy);icon.title=t.copy;
      const glyph=el("span",null,"oc-copy-glyph");glyph.setAttribute("aria-hidden","true");icon.append(glyph);control.append(icon);
      if(feedback){const note=el("span",t.copied,"oc-copy-feedback");note.setAttribute("role","status");control.append(note);}row.append(control);root.append(row);
      const actions=el("div",null,"oc-actions oc-import-actions");if(platform!=="windows")actions.append(link(t.import,grant.importUri));actions.append(button(t.download,download));root.append(actions,el("p",t.expires,"oc-note"));
    }
    if(!certificateImported)root.append(el("p",t.manual,"oc-note"));root.append(el("h4","4. "+t.enable),el("p",t.finish));
    if(message){const note=el("p",message,"oc-error");note.setAttribute("role","status");root.append(note);}
  }
  async function load() { if(!/^[A-Za-z0-9_-]{43}$/.test(token)){message=c().failed;render();return;}message="";render();try {info=await request(endpoint);}catch(error){message=error.status===410||error.status===404?c().failed:c().retry;}render(); }
  language.value=(navigator.language||"ru").slice(0,2);if(!TEXT[language.value])language.value="en";
  language.addEventListener("change",render);
  setInterval(()=>{if(grant&&Date.parse(grant.expiresAt)<=Date.now()){grant=null;info=null;clearPackage();message=c().expired;render();}},1000);
  window.addEventListener("pagehide",()=>{grant=null;connectionConfirmed=false;certificateImported=false;clearPackage();feedback=false;clearTimeout(timer);});
  window.addEventListener("pageshow",render);
  load();
})();
