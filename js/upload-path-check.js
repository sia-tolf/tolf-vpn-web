// Short sequential probes; never report their rates as connection speed.
async function checkUploadPath(onresult = () => {}, {fetcher = fetch, timeout = 4000} = {}) {
  const bytes = new Uint8Array(524288);
  for (let offset=0;offset<bytes.length;offset+=65536) crypto.getRandomValues(bytes.subarray(offset,offset+65536));
  const probes = [
    ['ikev2-us.tolf.is · Нью-Йорк', 'https://ikev2-us.tolf.is/', 65536],
    ['dns-us.tolf.is · тот же Нью-Йорк', 'https://dns-us.tolf.is/', 65536],
    ['dns-us.tolf.is · тот же Нью-Йорк', 'https://dns-us.tolf.is/', 524288],
    ['ikev2-us.tolf.is · повторно', 'https://ikev2-us.tolf.is/', 65536],
    ['Рига · контроль', 'https://ikev2-riga.tolf.is:8443/', 65536]
  ];
  const results = [];
  for (let i = 0; i < probes.length; i++) {
    const [city, server, size] = probes[i];
    const controller = new AbortController();
    let expired = false;
    const timer = setTimeout(() => { expired = true; controller.abort(); }, timeout);
    const started = performance.now();
    onresult({step:i+1, city, bytes:size, pending:true});
    let result;
    try {
      const response = await fetcher(server + 'empty.php?cors=true&probe=' + i + '&r=' + Math.random(), {
        method:'POST', body:bytes.subarray(0,size), credentials:'omit',
        cache:'no-store', signal:controller.signal
      });
      await response.arrayBuffer();
      result = {step:i+1, city, bytes:size, status:response.status,
        result:response.ok ? (['https://ikev2-us.tolf.is/', 'https://dns-us.tolf.is/'].includes(server) ? (response.headers.get('X-Tolf-Received-Bytes') === String(size) ? 'получение подтверждено сервером' : 'число полученных байтов не подтверждено') : 'принято') : 'ошибка HTTP'};
    } catch (error) {
      result = {step:i+1, city, bytes:size, result:expired ? 'тайм-аут' : 'ошибка сети'};
    } finally { clearTimeout(timer); }
    result.ms = Math.round(performance.now() - started);
    results.push(result); onresult(result);
  }
  return results;
}
