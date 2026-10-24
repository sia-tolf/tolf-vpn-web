"""Intermediate AnyConnect counters collected by the UK control plane."""
import json
import re
import sqlite3
import subprocess
from datetime import datetime, timezone

SCHEMA = """
CREATE TABLE IF NOT EXISTS oc_traffic_samples (
 node_id TEXT NOT NULL, session_id TEXT NOT NULL, user_id TEXT NOT NULL,
 username TEXT NOT NULL, connected_at TEXT NOT NULL, observed_at TEXT NOT NULL,
 upload_bytes INTEGER NOT NULL CHECK(upload_bytes>=0),
 download_bytes INTEGER NOT NULL CHECK(download_bytes>=0),
 PRIMARY KEY(node_id,session_id,observed_at)
);
CREATE INDEX IF NOT EXISTS oc_samples_user_time ON oc_traffic_samples(user_id,observed_at);
"""
REMOTE = r"""python3 - <<'PY'
import json,re,sqlite3,subprocess
p=subprocess.run(['/usr/libexec/tolf-oc-users'],capture_output=True,text=True,timeout=15,check=True)
users=json.loads(p.stdout)
assert isinstance(users,list)
rows=[]
if users:
 p=subprocess.run(['nft','-j','list','table','inet','tolf_accounting'],capture_output=True,text=True,timeout=15,check=True)
 counters={v['counter']['name']:v['counter']['bytes'] for v in json.loads(p.stdout)['nftables'] if 'counter' in v}
 c=sqlite3.connect('file:/etc/tolf-traffic/anyconnect.db?mode=ro',uri=True,timeout=10)
 for u in users:
  user=u.get('Username');sid=str(u.get('ID',''));ip=u.get('IPv4')
  if not isinstance(user,str) or not re.fullmatch(r'tolf-oc-[0-9a-f]{32}',user) or not sid.isdigit(): continue
  row=c.execute('SELECT connected_at FROM active_sessions WHERE session_id=? AND username=? AND vpn_ip=?',(sid,user,ip)).fetchone()
  up=counters.get('oc_up_'+sid);down=counters.get('oc_down_'+sid)
  if row and type(up) is int and type(down) is int and min(up,down)>=0:
   rows.append(dict(sessionId=sid,username=user,connectedAt=row[0],upload=up,download=down))
 c.close()
print(json.dumps({'sessions':rows,'connected':len(users)}))
PY
"""

def record(con,node,items,observed):
    stored=0
    for item in items:
        sid=item.get('sessionId'); username=item.get('username')
        up=item.get('upload');down=item.get('download');started=item.get('connectedAt')
        if (node not in ('moscow','riga') or not isinstance(sid,str) or not re.fullmatch(r'[0-9]{1,20}',sid)
            or not isinstance(username,str) or not re.fullmatch(r'tolf-oc-[0-9a-f]{32}',username)
            or type(started) is not int or type(up) is not int or type(down) is not int
            or min(up,down)<0 or max(up,down,up+down)>2**63-1):
            raise ValueError('Invalid live counters')
        start=datetime.fromtimestamp(started,timezone.utc).isoformat()
        if start>observed: raise ValueError('Invalid live time')
        device=con.execute('SELECT user_id FROM oc_devices WHERE username=?',(username,)).fetchone()
        if not device: raise ValueError('Unknown AnyConnect device')
        if con.execute('SELECT 1 FROM oc_traffic_sessions WHERE node_id=? AND session_id=?',(node,sid)).fetchone(): continue
        con.execute('INSERT OR IGNORE INTO oc_traffic_samples VALUES (?,?,?,?,?,?,?,?)',
                    (node,sid,device[0],username,start,observed,up,down))
        stored+=1
    return stored

def usage(con,start):
    """Merge intermediate and final counters by session; count each byte once."""
    groups={}
    for r in con.execute('SELECT node_id,session_id,user_id,connected_at,observed_at,upload_bytes,download_bytes FROM oc_traffic_samples ORDER BY observed_at'):
        node,sid,uid,connected,observed,up,down=r
        g=groups.setdefault((node,sid),dict(uid=uid,node=node,connected=connected,points=[],final=None))
        g['points'].append((observed,up,down))
    for r in con.execute('SELECT node_id,session_id,user_id,connected_at,disconnected_at,upload_bytes,download_bytes,completion_type FROM oc_traffic_sessions'):
        node,sid,uid,connected,ended,up,down,completion=r
        g=groups.setdefault((node,sid),dict(uid=uid,node=node,connected=connected,points=[],final=None))
        g['final']=(ended,up,down,completion)
    result={}
    for g in groups.values():
        points=g['points'];final=g['final']
        if not points:
            if final is None or final[0]<start: continue
            up,down=final[1:3]
        else:
            if final:
                # Ignore observations after a final record, and let the final
                # counters supersede a snapshot at the same timestamp.
                points=[p for p in points if p[0]<final[0]]+[final[:3]]
            points.sort()
            prev=None;up=down=0
            for observed,upload,download in points:
                if prev is None:
                    delta=(upload,download) if g['connected']>=start else (0,0)
                    prev=(upload,download)
                else:
                    delta=(max(0,upload-prev[0]),max(0,download-prev[1]))
                    prev=(max(prev[0],upload),max(prev[1],download))
                if observed>=start:
                    up+=delta[0];down+=delta[1]
            if not any(p[0]>=start for p in points): continue
        u=result.setdefault(g['uid'],dict(sessions=0,upload=0,download=0,total=0,recovered=0,nodes={}))
        u['sessions']+=1;u['upload']+=up;u['download']+=down;u['total']+=up+down
        if final and final[3]=='recovered':u['recovered']+=1
        n=u['nodes'].setdefault(g['node'],dict(node=g['node'],sessions=0,bytes=0))
        n['sessions']+=1;n['bytes']+=up+down
    return result

def final_record(con,node,item,observed):
    # Validate a final record with the same rules as a live snapshot.
    if item.get('state')!='stopped' or item.get('completion') not in ('normal','recovered'):
        raise ValueError('Invalid final state')
    ended=item.get('disconnectedAt')
    if type(ended) is not int or ended<item['connectedAt']:raise ValueError('Invalid final time')
    end=datetime.fromtimestamp(ended,timezone.utc).isoformat()
    if end>observed:raise ValueError('Future final time')
    device=con.execute('SELECT id,user_id FROM oc_devices WHERE username=?',(item['username'],)).fetchone()
    if not device:raise ValueError('Unknown AnyConnect device')
    con.execute("""
      INSERT OR IGNORE INTO oc_traffic_sessions(
       node_id,session_id,device_id,user_id,username,connected_at,disconnected_at,
       upload_bytes,download_bytes,total_bytes,completion_type,received_at)
      VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
    """,(node,item['sessionId'],device[0],device[1],item['username'],
         datetime.fromtimestamp(item['connectedAt'],timezone.utc).isoformat(),end,
         item['upload'],item['download'],item['upload']+item['download'],item['completion'],observed))

def collect(db='/var/lib/tolf-api/tolf.db',node='moscow'):
    targets={
      'moscow':('/opt/tolf-mcp/moscow_ed25519','root@92.243.66.204',REMOTE),
      'riga':('/opt/tolf-mcp/riga_ed25519','root@188.214.39.114','/usr/local/libexec/tolf-oc-riga-accounting export\n'),
    }
    if node not in targets:raise ValueError('Invalid node')
    identity,host,script=targets[node]
    ssh=['/usr/bin/ssh','-T','-i',identity,
         '-o','IdentitiesOnly=yes','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes',
         '-o','UserKnownHostsFile=/opt/tolf-api/.ssh/known_hosts','-o','ConnectTimeout=10',
         host,'/bin/sh','-s']
    p=subprocess.run(ssh,input=script,capture_output=True,text=True,timeout=45,check=True)
    data=json.loads(p.stdout)
    if not isinstance(data,dict) or not isinstance(data.get('sessions'),list):raise ValueError('Invalid node response')
    now=datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(db,timeout=30) as con:
        con.executescript(SCHEMA)
        n=0
        for item in data['sessions']:
            if node=='riga':
                ts=item.get('observedAt')
                if type(ts) is not int:raise ValueError('Invalid snapshot time')
                observed=datetime.fromtimestamp(ts,timezone.utc).isoformat()
                if observed>now:raise ValueError('Future snapshot')
            else:observed=now
            n+=record(con,node,[item],observed)
            if node=='riga' and item.get('state')=='stopped':
                final_record(con,node,item,now)
            elif node=='riga' and item.get('state')!='active':
                raise ValueError('Invalid state')
    print('OK: %s AnyConnect: snapshots=%s'%(node,n))

if __name__=='__main__':
    import sys
    collect(node=sys.argv[1] if len(sys.argv)>1 else 'moscow')
