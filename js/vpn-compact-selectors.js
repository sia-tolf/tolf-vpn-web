// Compact VPN selectors: protocol and entry point.
(() => {
  const oldTransport = document.getElementById("vpnTransportSelector");
  const ike = document.getElementById("vpnTransportIkev2");
  const any = document.getElementById("vpnTransportAnyConnect");
  const serverBox = document.querySelector("#serverSection .server-selector");
  const heading = document.getElementById("entryPointHeading");
  if (!oldTransport || !ike || !any || !serverBox || !heading) return;

  const lang = () => (document.documentElement.lang || "en").toLowerCase();
  const copy = {
    en:{protocol:"Protocol",entry:"VPN Entry Point",riga:"Riga",moscow:"Moscow"},
    ru:{protocol:"Протокол",entry:"Точка входа VPN",riga:"Рига",moscow:"Москва"},
    lv:{protocol:"Protokols",entry:"VPN ieejas punkts",riga:"Rīga",moscow:"Maskava"}
  };
  const tr = () => copy[lang()] || copy.en;

  const protocolField = document.createElement("label");
  protocolField.className = "vpn-compact-field vpn-protocol-field";
  const protocolLabel = document.createElement("span");
  const protocol = document.createElement("select");
  protocol.id = "vpnProtocolSelect";
  protocol.append(new Option("IKEv2","ikev2"), new Option("AnyConnect","anyconnect"));
  protocolField.append(protocolLabel, protocol);
  oldTransport.insertAdjacentElement("afterend", protocolField);

  const entryField = document.createElement("label");
  entryField.className = "vpn-compact-field vpn-entry-field";
  const entryLabel = document.createElement("span");
  const entry = document.createElement("select");
  entry.id = "vpnEntrySelect";
  entryField.append(entryLabel, entry);
  heading.insertAdjacentElement("afterend", entryField);

  function radio(value) {
    return document.querySelector('input[name="vpnServer"][value="'+value+'"]');
  }
  function rebuildEntry() {
    const current = window.getVpnTransport?.() === "anyconnect"
      ? (window.ocAccess?.ingress?.().id || "moscow")
      : (document.querySelector('input[name="vpnServer"]:checked')?.value || "riga");
    const points = window.getVpnTransport?.() === "anyconnect"
      ? (window.ocAccess?.ingresses?.() || [{id:"moscow"}]).map(x=>x.id)
      : ["riga","moscow"];
    entry.replaceChildren();
    for (const id of ["riga","moscow"]) {
      if (!points.includes(id)) continue;
      entry.append(new Option(id === "riga" ? tr().riga : tr().moscow,id));
    }
    if ([...entry.options].some(o=>o.value===current)) entry.value=current;
  }
  function sync() {
    protocolLabel.textContent=tr().protocol;
    entryLabel.textContent=tr().entry;
    const transport=window.getVpnTransport?.() || "ikev2";
    protocol.value=transport;
    for (const [value,button] of [["ikev2",ike],["anyconnect",any]]) {
      const option=[...protocol.options].find(o=>o.value===value);
      if (option) option.disabled=button.disabled || button.classList.contains("hidden");
    }
    rebuildEntry();
  }
  protocol.addEventListener("change",()=>{
    (protocol.value==="anyconnect"?any:ike).click();
    setTimeout(sync,0);
  });
  entry.addEventListener("change",()=>{
    const input=radio(entry.value);
    if (!input || input.disabled) return;
    input.checked=true;
    input.dispatchEvent(new Event("change",{bubbles:true}));
    setTimeout(sync,0);
  });
  window.addEventListener("vpntransportchange",sync);
  new MutationObserver(sync).observe(document.documentElement,{attributes:true,attributeFilter:["lang","data-vpn-transport"]});
  new MutationObserver(sync).observe(oldTransport,{subtree:true,attributes:true,attributeFilter:["class","disabled"]});
  sync();
})();