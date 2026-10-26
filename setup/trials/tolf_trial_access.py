#!/usr/bin/python3
"""Forwarding gate for exhausted trial identities only; no credential changes."""
import hashlib
import fcntl
import ipaddress
import json
import math
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
import time

from vici_readonly import Vici

CONFIG=Path('/etc/tolf-trials/blocked.json')
STATE=Path('/var/run/tolf-trial-access.json')
TABLE='tolf_trial_budget'
SOCKETS=('/run/ocserv-riga/occtl.socket','/run/occtl-riga.socket','/run/occtl-moscow.socket','/run/occtl-ny-moscow.socket','/run/occtl-node.socket','/run/occtl.socket')


def principal(row):
    # An authenticated EAP identity takes precedence over the caller's IKE ID.
    value=row.get('remote-eap-id') or row.get('remote-id')
    if not isinstance(value,bytes):return None
    try:return value.decode('utf-8')
    except UnicodeError:return None


def ike_spis(rows,blocked):
    incoming=set();outgoing=set()
    for row in rows:
        if row.get('state')!=b'ESTABLISHED' or principal(row) not in blocked:continue
        peer=str(ipaddress.ip_address(row.get('remote-host',b'').decode('ascii')))
        children=row.get('child-sas',{})
        if not isinstance(children,dict):raise ValueError('invalid_child_inventory')
        for child in children.values():
            if not isinstance(child,dict) or child.get('state')!=b'INSTALLED':continue
            for field,target in [('spi-in',incoming),('spi-out',outgoing)]:
                raw=child.get(field,b'').decode('ascii').removeprefix('0x')
                if not re.fullmatch('[0-9a-fA-F]{8}',raw) or int(raw,16)==0:raise ValueError('invalid_child_spi')
                target.add((int(raw,16),peer))
    return incoming,outgoing


def inventory():
    if not Path('/var/run/charon.vici').exists():return []
    with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as s:
        s.settimeout(2);s.connect('/var/run/charon.vici')
        client=Vici(s.fileno(),s.fileno());client.deadline=time.monotonic()+4
        return client.inventory()


def oc_users(path):
    result=subprocess.run([shutil.which('occtl') or '/usr/bin/occtl','-s',path,'-j','show','users'],capture_output=True,timeout=4)
    if result.returncode:raise ValueError('oc_inventory_unavailable')
    raw=json.loads(result.stdout)
    if isinstance(raw,dict):raw=next((v for k,v in raw.items() if k.lower()=='users'),None)
    if not isinstance(raw,list) or len(raw)>10000:raise ValueError('invalid_oc_inventory')
    return raw


def oc_ifindices(first,second,blocked,indices):
    # Read the interface index before re-validating the same authenticated worker.
    stable={(str(r.get('ID')),r.get('Username'),r.get('Device')) for r in second if r.get('State')=='connected'}
    result=set()
    for row in first:
        device=row.get('Device')
        if row.get('State')!='connected' or row.get('Username') not in blocked:continue
        if not isinstance(device,str) or not re.fullmatch('vpns[0-9]{1,10}',device):raise ValueError('invalid_tunnel_device')
        key=(str(row.get('ID')),row.get('Username'),device)
        index=indices.get(device)
        if key in stable and type(index) is int and index>0:result.add(index)
    return result


def oc_interfaces(blocked):
    result=set()
    for path in SOCKETS:
        if not Path(path).exists():continue
        first=oc_users(path);indices={}
        for row in first:
            device=row.get('Device')
            if row.get('Username') in blocked and isinstance(device,str) and re.fullmatch('vpns[0-9]{1,10}',device):
                try:indices[device]=int((Path('/sys/class/net')/device/'ifindex').read_text())
                except FileNotFoundError:pass
        if indices:result.update(oc_ifindices(first,oc_users(path),blocked,indices))
    return result


def rules(incoming,outgoing,interfaces,control,exists):
    lines=['delete table inet '+TABLE] if exists else []
    if not incoming and not outgoing and not interfaces:return '\n'.join(lines)+'\n' if lines else ''
    def numbers(values,hexadecimal=False):return '{ '+', '.join(hex(v) if hexadecimal else str(v) for v in sorted(values))+' }'
    allow='{ '+', '.join(str(ipaddress.IPv4Address(v)) for v in sorted(control))+' }'
    lines+=['table inet '+TABLE+' {',' chain trial_forward { type filter hook forward priority -10; policy accept;']
    matches=[]
    if interfaces:
        matches += [('meta iif '+numbers(interfaces),'in'),('meta oif '+numbers(interfaces),'out')]
    for direction,values in [('in',incoming),('out',outgoing)]:
        for spi,peer in sorted(values):
            family='ip' if ipaddress.ip_address(peer).version==4 else 'ip6'
            field='saddr' if direction=='in' else 'daddr'
            matches.append(('ipsec '+direction+' spi '+hex(spi)+' ipsec '+direction+' '+family+' '+field+' '+peer,direction))
    for match,direction in matches:
        if control:
            address='daddr' if direction=='in' else 'saddr';port='dport' if direction=='in' else 'sport'
            lines.append('  '+match+' ip '+address+' '+allow+' tcp '+port+' 443 accept')
        lines.append('  '+match+' counter drop')
    lines+=[' }','}']
    return '\n'.join(lines)+'\n'


def _apply():
    if not CONFIG.exists():config={'version':1,'principals':[],'controlIPv4':[]}
    else:
        if CONFIG.stat().st_size>2_000_000:raise ValueError('manifest_too_large')
        config=json.loads(CONFIG.read_text())
    if config.get('version')!=1 or not isinstance(config.get('principals'),list) or len(config['principals'])>20000:raise ValueError('invalid_manifest')
    blocked=set(config['principals'])
    enrolled=config.get('allTrialPrincipals',[])
    expires=config.get('validUntil',0)
    if not isinstance(enrolled,list) or len(enrolled)>20000 or type(expires) not in (int,float) or not math.isfinite(expires) or expires<0:raise ValueError('invalid_lease')
    if enrolled and expires<time.time():blocked.update(enrolled)
    if any(not isinstance(v,str) or not re.fullmatch('[A-Za-z0-9_.@=,: -]{1,256}',v) for v in blocked):raise ValueError('invalid_principal')
    control=config.get('controlIPv4',[])
    if not isinstance(control,list) or len(control)>16:raise ValueError('invalid_control_addresses')
    control=[str(ipaddress.IPv4Address(v)) for v in control]
    nft=shutil.which('nft') or '/usr/sbin/nft'
    exists=subprocess.run([nft,'list','table','inet',TABLE],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0
    if blocked:
        incoming,outgoing=ike_spis(inventory(),blocked);interfaces=oc_interfaces(blocked)
    else:incoming=outgoing=interfaces=set()
    script=rules(incoming,outgoing,interfaces,control,exists)
    signature=hashlib.sha256(script.encode()).hexdigest()
    try:previous=json.loads(STATE.read_text())
    except (OSError,ValueError):previous={}
    # The observed kernel table is checked as well: a firewall reload may have removed it.
    wanted=bool(incoming or outgoing or interfaces)
    if previous.get('rulesSha256')!=signature or exists!=wanted:
        if script:
            check=subprocess.run([nft,'-c','-f','-'],input=script.encode(),capture_output=True,timeout=4)
            if check.returncode:raise ValueError('nft_validation_failed')
            result=subprocess.run([nft,'-f','-'],input=script.encode(),capture_output=True,timeout=4)
            if result.returncode:raise ValueError('nft_application_failed')
    status={'at':time.time(),'rulesSha256':signature,'blockedPrincipals':len(blocked),'ikeInboundSPIs':len(incoming),'ikeOutboundSPIs':len(outgoing),'ocInterfaces':len(interfaces),'manifestSha256':hashlib.sha256(json.dumps(config,sort_keys=True,separators=(',',':')).encode()).hexdigest()}
    STATE.write_text(json.dumps(status));os.chmod(STATE,0o600)
    return status


def apply():
    with open('/var/run/tolf-trial-access.lock','a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        return _apply()


def main():
    if os.geteuid()!=0:raise SystemExit('root_required')
    watch=sys.argv[1:]==['--watch']
    if sys.argv[1:] not in ([],['--watch']):raise SystemExit('invalid_arguments')
    while True:
        try:
            result=apply()
            if not watch:print(json.dumps(result));return
        except Exception as error:
            # A failed inventory never clears a previously applied gate.
            print(json.dumps({'status':'error','error':str(error) if isinstance(error,ValueError) else 'trial_gate_unavailable'}),flush=True)
            if not watch:raise SystemExit(1)
        time.sleep(5)


if __name__=='__main__':main()
