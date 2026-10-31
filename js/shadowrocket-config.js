/* Browser-local file generation. Never send or persist generated files. */
(() => {
  'use strict';
  const nodes = Object.freeze([
    Object.freeze({name:'TOLF_Moscow', host:'oc.tolf.is', port:4443}),
    Object.freeze({name:'TOLF_Riga', host:'oc-riga.tolf.is', port:443}),
    Object.freeze({name:'TOLF_New_York', host:'oc-us-moscow.tolf.is', port:4443})
  ]);
  // Preserve the on-device-tested, unquoted node syntax. Do not guess escaping
  // for delimiters: those accounts import the same file and enter the password in-app.
  function supportsPassword(value) {
    return typeof value === 'string' && value.length > 0 && value === value.trim() &&
      !/[,;#"'\\\s\u0000-\u001f\u007f\u2028\u2029]/u.test(value);
  }
  function build(username, password, manualPassword = false) {
    if (!/^[a-z0-9][a-z0-9_.-]{2,31}$/.test(username)) throw new Error('invalid_username');
    if (!manualPassword && !supportsPassword(password)) throw new Error('manual_password_required');
    const lines = nodes.map(node => node.name+' = openconnect, '+node.host+', '+node.port+
      ', user='+username+', password='+(manualPassword?'':password)+', udp=1');
    return [
      '# TOLF Shadowrocket',
      manualPassword ? '# Enter the account password in each server before connecting.' : '# Contains your account password. Keep this file private.',
      '', '[General]', 'bypass-system = true',
      'skip-proxy = localhost, *.local, *.lan, *.home.arpa, 127.0.0.1, 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16',
      'tun-excluded-routes = 127.0.0.0/8, 169.254.0.0/16, 224.0.0.0/4, 255.255.255.255/32',
      'dns-server = 10.254.0.53#proxy', 'fallback-dns-server = 10.254.0.53#proxy',
      'proxy-dns-server = system', 'dns-direct-system = true',
      'ipv6 = false', 'prefer-ipv6 = false', 'private-ip-answer = true',
      'icmp-auto-reply = true', 'udp-policy-not-supported-behaviour = REJECT',
      '', '[Proxy]', ...lines, '', '[Rule]',
      'DOMAIN-SUFFIX,tolf.is,DIRECT',
      'IP-CIDR,10.254.0.53/32,PROXY,no-resolve',
      'DOMAIN-SUFFIX,local,DIRECT', 'DOMAIN-SUFFIX,lan,DIRECT', 'DOMAIN-SUFFIX,home.arpa,DIRECT',
      'IP-CIDR,127.0.0.0/8,DIRECT,no-resolve', 'IP-CIDR,169.254.0.0/16,DIRECT,no-resolve',
      'IP-CIDR,10.0.0.0/8,DIRECT,no-resolve', 'IP-CIDR,172.16.0.0/12,DIRECT,no-resolve',
      'IP-CIDR,192.168.0.0/16,DIRECT,no-resolve', 'IP-CIDR,224.0.0.0/4,DIRECT,no-resolve',
      'FINAL,PROXY', '', '[Host]', 'localhost = 127.0.0.1', '', '[MITM]', 'enable = false', ''
    ].join('\n');
  }
  function credentialsText(username, password) {
    return ['TOLF — https://vpn.tolf.is/auth/', 'Логин / Username: '+username,
      'Пароль / Password: '+password, ''].join('\r\n');
  }
  globalThis.TolfShadowrocketConfig = Object.freeze({nodes, supportsPassword, build, credentialsText});
})();
