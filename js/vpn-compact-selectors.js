// VPN protocol and entry-point dropdowns.
(() => {
  const oldTransport=document.getElementById("vpnTransportSelector");
  const ike=document.getElementById("vpnTransportIkev2");
  const any=document.getElementById("vpnTransportAnyConnect");
  const heading=document.getElementById("entryPointHeading");
  if(!oldTransport||!ike||!any||!heading)return;

  const lang=()=>((document.documentElement.lang||"en").toLowerCase());
  const COPY={
    en:{protocol:"Protocol",entry:"VPN Entry Point",riga:"Riga",moscow:"Moscow"},
    ru:{protocol:"Протокол",entry:"Точка входа VPN",riga:"Рига",moscow:"Москва"},
    lv:{protocol:"Protokols",entry:"VPN ieejas punkts",riga:"Rīga",moscow:"Maskava"}
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
        const opt=document.createElement("button"); opt.type="button"; opt.className="vpn-dropdown-option"; opt.setAttribute("role","option"); opt.dataset.value=item.value; const mark=document.createElement("span"); mark.className="vpn-dropdown-check"; mark.textContent=active?"✓":""; const txt=document.createElement("span"); txt.textContent=item.label; opt.append(mark,txt);
        const active=item.value===selected; opt.classList.toggle("selected",active); opt.setAttribute("aria-selected",String(active)); opt.disabled=!!item.disabled;
        opt.addEventListener("click",()=>{if(opt.disabled)return;selected=item.value;value.textContent=item.label;close();onChange(item.value);});
        menu.append(opt);
      }
      const current=options.find(x=>x.value===selected)||options.find(x=>!x.disabled);
      value.textContent=current?.label||"";
    }
    document.addEventListener("pointerdown",e=>{if(!dd.contains(e.target))close();});
    document.addEventListener("keydown",e=>{if(e.key==="Escape")close();});
    return {field,label,render,close};
  }

  const protocolDD=makeDropdown("vpnProtocolDropdown",tr().protocol,[],value=>{
    (value==="anyconnect"?any:ike).click(); setTimeout(sync,0);
  });
  protocolDD.field.classList.add("vpn-protocol-field");
  oldTransport.insertAdjacentElement("afterend",protocolDD.field);

  const entryDD=makeDropdown("vpnEntryDropdown",tr().entry,[],value=>{
    const input=document.querySelector('input[name="vpnServer"][value="'+value+'"]');
    if(!input||input.disabled)return;
    input.checked=true; input.dispatchEvent(new Event("change",{bubbles:true})); setTimeout(sync,0);
  });
  entryDD.field.classList.add("vpn-entry-field");
  heading.insertAdjacentElement("afterend",entryDD.field);

  function sync(){
    document.getElementById("serverSection")?.classList.remove("hidden");
    protocolDD.label.textContent=tr().protocol; entryDD.label.textContent=tr().entry;
    const transport=window.getVpnTransport?.()||"ikev2";
    protocolDD.render([
      {value:"ikev2",label:"IKEv2",disabled:ike.disabled||ike.classList.contains("hidden")},
      {value:"anyconnect",label:"AnyConnect",disabled:any.disabled||any.classList.contains("hidden")}
    ],transport);
    const current=transport==="anyconnect"?(window.ocAccess?.ingress?.().id||"moscow"):(document.querySelector('input[name="vpnServer"]:checked')?.value||"riga");
    const allowed=transport==="anyconnect"?(window.ocAccess?.ingresses?.()||[{id:"moscow"}]).map(x=>x.id):["riga","moscow"];
    entryDD.render(["riga","moscow"].filter(x=>allowed.includes(x)).map(x=>({value:x,label:x==="riga"?tr().riga:tr().moscow})),current);
  }
  window.addEventListener("vpntransportchange",sync);
  new MutationObserver(sync).observe(document.documentElement,{attributes:true,attributeFilter:["lang","data-vpn-transport"]});
  new MutationObserver(sync).observe(oldTransport,{subtree:true,attributes:true,attributeFilter:["class","disabled"]});
  sync();
})();