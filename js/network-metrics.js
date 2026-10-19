// Each pair is stored once; orient both rates from the selected ingress.
function networkPairsForIngress(pairs, ingress) {
  return ['riga', 'moscow', 'us'].filter(id => id !== ingress).map(target => {
    const pair = pairs.find(p => (p.source === ingress && p.target === target) ||
      (p.target === ingress && p.source === target));
    if (!pair) return {source: ingress, target};
    return {...pair, source: ingress, target,
      forward_mbps: pair.source === ingress ? pair.forward_mbps : pair.reverse_mbps,
      reverse_mbps: pair.source === ingress ? pair.reverse_mbps : pair.forward_mbps};
  });
}

(() => {
  let pairs = [], unavailable = false;
  const copy = () => ({
    ru: {latency:'Задержка', speed:'Скорость', pair:'Соединение', forward:'Прямое направление', reverse:'Обратное направление', measured:'Замер', missing:'Нет замера', stale:'устарел', failed:'Измерения недоступны', riga:'Рига', moscow:'Москва', us:'Нью-Йорк'},
    en: {latency:'Latency', speed:'Speed', pair:'Connection', forward:'Forward direction', reverse:'Reverse direction', measured:'Measured', missing:'Not measured', stale:'outdated', failed:'Measurements unavailable', riga:'Riga', moscow:'Moscow', us:'New York'},
    lv: {latency:'Aizture', speed:'Ātrums', pair:'Savienojums', forward:'Tiešais virziens', reverse:'Pretējais virziens', measured:'Mērīts', missing:'Nav mērījuma', stale:'novecojis', failed:'Mērījumi nav pieejami', riga:'Rīga', moscow:'Maskava', us:'Ņujorka'}
  }[document.documentElement.lang] || {latency:'Latency', speed:'Speed', pair:'Connection', forward:'Forward direction', reverse:'Reverse direction', measured:'Measured', missing:'Not measured', stale:'outdated', failed:'Measurements unavailable', riga:'Riga', moscow:'Moscow', us:'New York'});
  const node = (tag, className, text) => {
    const el = document.createElement(tag); el.className = className;
    if (text !== undefined) el.textContent = text;
    return el;
  };
  function render() {
    const container = document.getElementById('networkMetrics');
    if (!container) return;
    const c = copy();
    const ingress = typeof getConnectionTestServerKey === 'function' ? getConnectionTestServerKey() : 'riga';
    const stamp = (value, maxAge) => {
      const date = new Date(value || '');
      if (!Number.isFinite(date.getTime())) return c.missing;
      const text = date.toLocaleString(document.documentElement.lang || 'en', {month:'2-digit', day:'2-digit', hour:'2-digit', minute:'2-digit'});
      return text + (Date.now() - date.getTime() > maxAge ? ` (${c.stale})` : '');
    };
    const metric = (value, unit, decimals) => Number.isFinite(value) && value >= 0 ? `${value.toFixed(decimals)} ${unit}` : c.missing;
    container.replaceChildren();
    const table = node('table', 'network-table');
    const caption = node('caption', 'network-table-caption', document.querySelector('[data-i18n="measurementNetworkHelp"]')?.textContent || '');
    table.appendChild(caption);
    const head = node('thead', '');
    const headings = node('tr', '');
    for (const label of [c.pair, c.latency, c.forward, c.reverse]) {
      const cell = node('th', '', label);
      cell.setAttribute('scope', 'col'); headings.appendChild(cell);
    }
    head.appendChild(headings); table.appendChild(head);
    const body = node('tbody', '');
    for (const p of networkPairsForIngress(pairs, ingress)) {
      const row = node('tr', 'network-table-row');
      const pair = node('th', 'network-table-pair', `${c[p.source]} ↔ ${c[p.target]}`);
      pair.setAttribute('scope', 'row'); row.appendChild(pair);
      const speedAge = (p.source === 'us' || p.target === 'us' ? 12 : 2)*3600000;
      for (const [direction, value, measuredAt, maxAge] of [
        ['', metric(p.rtt_ms, 'ms', 1), p.measured_at, 15*60000],
        [`${c[p.source]} → ${c[p.target]}`, metric(p.forward_mbps, 'Mbps', 1), p.throughput_measured_at, speedAge],
        [`${c[p.target]} → ${c[p.source]}`, metric(p.reverse_mbps, 'Mbps', 1), p.throughput_measured_at, speedAge]
      ]) {
        const cell = node('td', 'network-table-value');
        const directionLabel = node('span', 'network-table-direction', direction);
        if (!direction) directionLabel.setAttribute('aria-hidden', 'true');
        cell.appendChild(directionLabel);
        cell.appendChild(node('strong', '', value));
        cell.appendChild(node('small', 'network-table-time', `${c.measured}: ${stamp(measuredAt, maxAge)}`));
        row.appendChild(cell);
      }
      body.appendChild(row);
    }
    table.appendChild(body);
    container.appendChild(table);
    container.classList.remove('hidden');
    const status = document.getElementById('networkMetricMeasuredAt');
    if (status) status.textContent = unavailable ? c.failed : '';
  }
  async function load() {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 10000);
    try {
      const response = await fetch('https://api.tolf.is/network-metrics', {cache:'no-store', signal:controller.signal});
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      if (!Array.isArray(data.pairs)) throw new Error('Missing network pairs');
      pairs = data.pairs; unavailable = false;
    } catch (error) { unavailable = true; console.error('Network metrics failed:', error); }
    finally { clearTimeout(timer); render(); }
  }
  function start() {
    for (const event of ['vpntransportchange','vpnplatformchange','tolf:network-context-changed','tolf:ingress-changed','tolf:measurement-selection-changed']) window.addEventListener(event, render);
    document.getElementById('windowsDeviceServer')?.addEventListener('change', render);
    for (const input of typeof serverInputs !== 'undefined' ? serverInputs : []) input.addEventListener('change', render);
    new MutationObserver(render).observe(document.documentElement, {attributes:true, attributeFilter:['lang']});
    render(); load(); window.setInterval(load, 300000);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start);
  else setTimeout(start, 0);
})();
