// VPN protocol and entry-point dropdowns.
(() => {
  const oldTransport=document.getElementById("vpnTransportSelector");
  const ike=document.getElementById("vpnTransportIkev2");
  const any=document.getElementById("vpnTransportAnyConnect");
  const heading=document.getElementById("entryPointHeading");
  if(!oldTransport||!ike||!any||!heading)return;

  const lang=()=>((document.documentElement.lang||"en").toLowerCase());
  const COPY={
    en:{protocol:"Protocol",chooseProtocol:"Choose a protocol",entry:"VPN Entry Point",riga:"Riga",moscow:"Moscow",us:"New York",recommended:"Recommended",measuring:"Measuring…",unavailable:"—",unsupported:"Available with AnyConnect or Windows",notReady:"Not available"},
    ru:{protocol:"Протокол",chooseProtocol:"Выберите протокол",entry:"Точка входа VPN",riga:"Рига",moscow:"Москва",us:"Нью-Йорк",recommended:"Рекомендуется",measuring:"Измерение…",unavailable:"—",unsupported:"Доступен в AnyConnect или Windows",notReady:"Недоступен"},
    lv:{protocol:"Protokols",chooseProtocol:"Izvēlieties protokolu",entry:"VPN ieejas punkts",riga:"Rīga",moscow:"Maskava",us:"Ņujorka",recommended:"Ieteicams",measuring:"Mērīšana…",unavailable:"—",unsupported:"Pieejams ar AnyConnect vai Windows",notReady:"Nav pieejams"}
  };
  const tr=()=>COPY[lang()]||COPY.en;

  function makeDropdown(id,labelText,items,onChange){
    const field=document.createElement("div"); field.className="vpn-compact-field";
    const label=document.createElement("div"); label.className="vpn-compact-label"; label.textContent=labelText;
    const dd=document.createElement("div"); dd.className="vpn-dropdown"; dd.id=id;
    const button=document.createElement("button"); button.type="button"; button.className="vpn-dropdown-button"; button.setAttribute("aria-haspopup","listbox"); button.setAttribute("aria-expanded","false");
    const value=document.createElement("span"); value.className="vpn-dropdown-value";
    const arrow=document.createElement("span"); arrow.className="vpn-dropdown-arrow"; arrow.setAttribute("aria-hidden","true");
    const menu=document.createElement("div"); menu.className="vpn-dropdown-menu"; menu.setAttribute("role","listbox"); menu.hidden=true;
    button.append(value,arrow); dd.append(button,menu); field.append(label,dd);
    let options=[],selected="";
    function close(){menu.hidden=true;dd.classList.remove("open");button.setAttribute("aria-expanded","false");}
    function open(){document.querySelectorAll(".vpn-dropdown.open").forEach(x=>{if(x!==dd)x.querySelector(".vpn-dropdown-button")?.click();});menu.hidden=false;dd.classList.add("open");button.setAttribute("aria-expanded","true");}
    button.addEventListener("click",e=>{e.stopPropagation();menu.hidden?open():close();});
    function render(nextItems,nextSelected){
      options=nextItems; selected=nextSelected;
      menu.replaceChildren();
      for(const item of options){
        const opt=document.createElement("button"); opt.type="button"; opt.className="vpn-dropdown-option"; opt.setAttribute("role","option"); opt.dataset.value=item.value;
        const active=item.value===selected;
        const mark=document.createElement("span"); mark.className="vpn-dropdown-check"; mark.textContent=active?"✓":"";
        const txt=document.createElement("span"); txt.className="vpn-dropdown-option-label"; txt.textContent=item.label;
        opt.append(mark,txt);
        if(item.meta){const meta=document.createElement("span");meta.className="vpn-dropdown-option-meta";meta.textContent=item.meta;opt.append(meta);}
        if(item.badge){const badge=document.createElement("span");badge.className="vpn-dropdown-option-badge";badge.textContent=item.badge;opt.append(badge);} opt.classList.toggle("selected",active); opt.setAttribute("aria-selected",String(active)); opt.disabled=!!item.disabled;
        opt.addEventListener("click",()=>{if(opt.disabled)return;selected=item.value;value.textContent=item.label;close();onChange(item.value);});
        menu.append(opt);
      }
      const current=options.find(x=>x.value===selected)||options.find(x=>!x.disabled);
      value.textContent=current?.label||"";
      if(current?.meta){const m=document.createElement("span");m.className="vpn-dropdown-value-meta";m.textContent=current.meta;value.append(" ",m);}
    }
    const outside=e=>{if(!dd.contains(e.target))close();};
    const escape=e=>{if(e.key==="Escape")close();};
    document.addEventListener("pointerdown",outside);
    document.addEventListener("keydown",escape);
    return {field,label,render,close,destroy(){
      document.removeEventListener("pointerdown",outside);
      document.removeEventListener("keydown",escape);
    }};
  }

  // Expose the existing dropdown renderer for Windows manual fields.
  window.makeVpnDropdown=makeDropdown;

  const protocolDD=makeDropdown("vpnProtocolDropdown",tr().protocol,[],value=>{
    (value==="anyconnect"?any:ike).click(); setTimeout(sync,0);
  });
  protocolDD.field.classList.add("vpn-protocol-field");
  document.getElementById("myVpnProtocolField").append(protocolDD.field);

  const entryDD=makeDropdown("vpnEntryDropdown",tr().entry,[],value=>{
    if(window.getVpnTransport?.()==="anyconnect"){window.ocAccess?.selectIngress?.(value);setTimeout(sync,0);return;}
    if(typeof currentPlatform!=="undefined" && currentPlatform==="windows"){
      const select=document.getElementById("windowsDeviceServer");
      const option=[...select.options].find(item=>item.value===value);
      if(!option||option.disabled||select.disabled)return;
      select.value=value;select.dispatchEvent(new Event("change",{bubbles:true}));setTimeout(sync,0);return;
    }
    const input=document.querySelector('input[name="vpnServer"][value="'+value+'"]');
    if(!input||input.disabled)return;
    input.checked=true; input.dispatchEvent(new Event("change",{bubbles:true})); setTimeout(sync,0);
  });
  entryDD.field.classList.add("vpn-entry-field");
  heading.insertAdjacentElement("afterend",entryDD.field);

  function sync(){
    document.getElementById("serverSection")?.classList.remove("hidden");
    protocolDD.label.textContent=tr().protocol; entryDD.label.textContent=tr().entry;
    const transport=window.getVpnTransport?.()||"";
    document.querySelectorAll("[data-protocol-summary]").forEach(el=>el.classList.toggle("hidden",el.dataset.protocolSummary!==transport));
    document.getElementById("quickSetupLink").classList.remove("hidden");
    document.getElementById("quickSetupLink").href="/quick/?protocol="+transport;
    document.getElementById("quickProtocolNote").classList.add("hidden");
    protocolDD.render([
      {value:"",label:tr().chooseProtocol,disabled:true},
      {value:"ikev2",label:"IKEv2",disabled:ike.disabled||ike.classList.contains("hidden")},
      {value:"anyconnect",label:"AnyConnect",disabled:any.disabled||any.classList.contains("hidden")}
    ],transport);
    const windowsIke=transport==="ikev2" && typeof currentPlatform!=="undefined" && currentPlatform==="windows";
    const winSelect=document.getElementById("windowsDeviceServer");
    const current=windowsIke?winSelect.value:transport==="anyconnect"?(window.ocAccess?.ingress?.().id||"moscow"):(document.querySelector('input[name="vpnServer"]:checked')?.value||"riga");
    const allowed=transport==="anyconnect"?(window.ocAccess?.ingresses?.()||[{id:"moscow"}]).map(x=>x.id):windowsIke?[...winSelect.options].filter(x=>!x.disabled).map(x=>x.value):["riga","moscow",...(window.tolfMobileIkev2Ready?["us"]:[])];
    const recommended=(typeof recommendedEntryPoint!=="undefined"?recommendedEntryPoint:null);
    const latency=(id)=>{
      if(typeof entryPointLatencyMeasuring!=="undefined"&&entryPointLatencyMeasuring)return tr().measuring;
      const v=(typeof entryPointLatencyValues!=="undefined"?entryPointLatencyValues[id]:null);
      return Number.isFinite(v)&&v>=0?Math.round(v)+" ms":tr().unavailable;
    };
    entryDD.render(["riga","moscow","us"].map(x=>({
      value:x,label:tr()[x],disabled:!allowed.includes(x),
      meta:allowed.includes(x)?latency(x):(x==="us"&&transport==="ikev2"&&!windowsIke?tr().unsupported:tr().notReady),
      badge:allowed.includes(x)&&x===recommended?"("+tr().recommended+")":""
    })),current);
    if(transport==="anyconnect")document.getElementById("quickSetupLink").href="/quick/?protocol=anyconnect&ingress="+encodeURIComponent(current);
  }
  window.addEventListener("vpncapabilitieschange",sync);
  window.addEventListener("vpntransportchange",sync);
  window.addEventListener("vpnplatformchange",sync);
  document.getElementById("windowsDeviceServer")?.addEventListener("change",sync);
  window.addEventListener("tolf:measurement-target-resolved",()=>setTimeout(sync,0));
  window.addEventListener("focus",()=>setTimeout(sync,0));
  setInterval(sync,2000);
  new MutationObserver(sync).observe(document.documentElement,{attributes:true,attributeFilter:["lang","data-vpn-transport"]});
  new MutationObserver(sync).observe(oldTransport,{subtree:true,attributes:true,attributeFilter:["class","disabled"]});
  sync();
})();
