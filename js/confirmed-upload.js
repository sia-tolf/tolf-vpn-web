// Use in-memory bytes from the page, avoiding the worker/Blob upload path.
// Only successful server responses count; progress events never count as receipt.
async function measureConfirmedUpload(server, {signal, onprogress = () => {}, duration = 15000,
  streams = 4, fetcher = fetch, now = () => performance.now()} = {}) {
  const controller = new AbortController();
  const abort = () => controller.abort();
  if (signal?.aborted) throw new Error('upload_cancelled');
  signal?.addEventListener('abort', abort, {once:true});
  const started = now();
  let bytes = 0, completed = 0, failures = 0, lastError = '', expired = false;
  const payload = new Uint8Array(4 * 1024 * 1024);
  for (let offset = 0; offset < payload.length; offset += 65536) {
    crypto.getRandomValues(payload.subarray(offset, offset + 65536));
  }
  const timer = setTimeout(() => { expired = true; controller.abort(); }, duration);
  const report = () => onprogress({mbps: bytes * 8 / Math.max(1, now() - started) / 1000,
    acknowledgedBytes:bytes, completed, failures});
  const ticker = setInterval(report, 250);
  async function stream() {
    let size = 65536, consecutiveFailures = 0;
    while (!controller.signal.aborted && now() - started < duration) {
      const sentAt = now();
      try {
        const response = await fetcher(server + 'empty.php?cors=true&r=' + Math.random(), {
          method:'POST', body:payload.subarray(0, size), credentials:'omit',
          cache:'no-store', signal:controller.signal
        });
        if (!response.ok) throw new Error('upload_http_' + response.status);
        await response.arrayBuffer();
        if (controller.signal.aborted || now() - started >= duration) break;
        bytes += size; completed++; consecutiveFailures = 0;
        const elapsed = now() - sentAt;
        size = Math.min(payload.length, Math.max(16384,
          elapsed < 750 ? size * 2 : elapsed > 2000 ? size / 2 : size));
      } catch (error) {
        if (controller.signal.aborted) break;
        failures++; consecutiveFailures++;
        lastError = /^upload_http_\d+$/.test(error.message) ? error.message : 'upload_network';
        size = 16384;
        if (consecutiveFailures >= 2) return;
      }
    }
  }
  try {
    await Promise.all(Array.from({length:streams}, stream));
    if (signal?.aborted) throw new Error('upload_cancelled');
    // Do not present an interrupted/all-failed test as a measured rate.
    if (!bytes || (!expired && now() - started < duration)) throw new Error(lastError || 'upload_no_response');
    const result = {mbps:bytes * 8 / Math.max(duration, now()-started) / 1000,
      acknowledgedBytes:bytes, completed, failures};
    onprogress(result);
    return result;
  } finally {
    clearTimeout(timer); clearInterval(ticker); controller.abort();
    signal?.removeEventListener('abort', abort);
  }
}
