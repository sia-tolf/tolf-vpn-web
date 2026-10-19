// Use in-memory bytes from the page, avoiding the worker/Blob upload path.
// Only successful server responses count; progress events never count as receipt.
async function measureConfirmedUpload(server, {signal, onprogress = () => {}, duration = 15000,
  warmup = 3000, streams = 4, fetcher = fetch, now = () => performance.now()} = {}) {
  const controller = new AbortController();
  const abort = () => controller.abort();
  if (signal?.aborted) throw new Error('upload_cancelled');
  signal?.addEventListener('abort', abort, {once:true});
  const started = now();
  const measurementStarted = started + Math.max(0, warmup);
  const stopAt = measurementStarted + duration;
  let bytes = 0, completed = 0, failures = 0, lastError = '';
  const payload = new Uint8Array(4 * 1024 * 1024);
  for (let offset = 0; offset < payload.length; offset += 65536) {
    crypto.getRandomValues(payload.subarray(offset, offset + 65536));
  }
  const timer = setTimeout(() => controller.abort(), Math.max(0, warmup) + duration);
  const report = () => onprogress({
    mbps: bytes * 8 / Math.max(1, now() - measurementStarted) / 1000,
    acknowledgedBytes:bytes, completed, failures,
    warmingUp:now() < measurementStarted
  });
  const ticker = setInterval(report, 250);
  async function stream() {
    let size = 65536, consecutiveFailures = 0;
    while (!controller.signal.aborted && now() < stopAt) {
      const sentAt = now();
      try {
        const response = await fetcher(server + 'empty.php?cors=true&r=' + Math.random(), {
          method:'POST', body:payload.subarray(0, size), credentials:'omit',
          cache:'no-store', signal:controller.signal
        });
        if (!response.ok) throw new Error('upload_http_' + response.status);
        await response.arrayBuffer();
        const receivedAt = now();
        if (controller.signal.aborted || receivedAt >= stopAt) break;
        // Warm-up requests tune the block size but never inflate the measured rate.
        if (sentAt >= measurementStarted) {
          bytes += size; completed++;
        }
        consecutiveFailures = 0;
        const elapsed = receivedAt - sentAt;
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
    if (!bytes) throw new Error(lastError || 'upload_no_response');
    const result = {mbps:bytes * 8 / Math.max(1, duration) / 1000,
      acknowledgedBytes:bytes, completed, failures, warmingUp:false};
    onprogress(result);
    return result;
  } finally {
    clearTimeout(timer); clearInterval(ticker); controller.abort();
    signal?.removeEventListener('abort', abort);
  }
}
