/* Import callbacks need verification on the target iOS version before rollout. */
(() => {
  'use strict';
  function https(value) {
    const url = new URL(value);
    if (url.protocol !== 'https:') throw new Error('HTTPS URL required');
    return url.href;
  }
  function build({on, off, success, cancel, error}) {
    const cancelled = https(cancel), failed = https(error);
    function step(file, name, next) {
      const url = new URL('shortcuts://x-callback-url/import-shortcut');
      url.searchParams.set('url', https(file));
      url.searchParams.set('name', name);
      url.searchParams.set('x-success', next);
      url.searchParams.set('x-cancel', cancelled);
      url.searchParams.set('x-error', failed);
      return url.href;
    }
    return step(on, 'TOLF ON', step(off, 'TOLF OFF', https(success)));
  }
  window.tolfShortcutImportChain = {build};
})();
