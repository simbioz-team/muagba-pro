import glob,json,os,collections,re
from datetime import datetime
SINCE='2026-11-13'
P={'opus':(5,.2),'sonnet':(2.5,.1)}
def ts(s): return datetime.fromisoformat(s.replace('Z','+00:00'))
cause=collections.Counter(); money=collections.Counter(); gaps=collections.Counter(); ex=collections.defaultdict(list); role=collections.Counter()
for d in glob.glob(os.path.expanduser('~/.claude/projects/-home-rustam-develop-simbioz-team-*')):
  for f in glob.glob(d+'/*/subagents/**/*.jsonl',recursive=True):
    try: meta=json.load(open(f[:-6]+'.meta.json'))
    except: meta={}
    ev=[]; first=None; names={}
    for line in open(f,errors='replace'):
        try:o=json.loads(line)
        except:continue
        t=o.get('timestamp')
        if not t: continue
        first=first or t
        typ=o.get('type')
        if typ=='assistant':
            m=o.get('message') or {}
            u=m.get('usage') or {}
            for c in m.get('content') or []:
                if isinstance(c,dict) and c.get('type')=='tool_use':
                    i=c.get('input') or {}
                    cmd=(i.get('command') or '')
                    cmd=re.sub(r'^\s*cd\s+\S+\s*(&&|;)\s*','',cmd)
                    k=c['name']+(':bg' if i.get('run_in_background') else '')+':'+' '.join(cmd.split()[:2])[:40]
                    ev.append(('tool',ts(t),k))
            if u: ev.append(('req',ts(t),(u.get('cache_creation_input_tokens',0),u.get('cache_read_input_tokens',0),'sonnet' if 'sonnet' in m.get('model','') else 'opus')))
        elif typ=='user':
            c=(o.get('message') or {}).get('content')
            txt=c if isinstance(c,str) else ' '.join(x.get('text','') for x in c if isinstance(x,dict) and x.get('type')=='text') if isinstance(c,list) else ''
            if 'Stop hook' in txt or 'SubagentStop' in txt or 'check.sh' in txt[:300] and 'hook' in txt[:300].lower(): ev.append(('gate',ts(t),''))
            elif '<task-notification' in txt: ev.append(('notif',ts(t),''))
            elif txt.strip() and not any(isinstance(x,dict) and x.get('type')=='tool_result' for x in (c if isinstance(c,list) else [])): ev.append(('msg',ts(t),''))
    if not first or first<SINCE: continue
    last_req=None; last_tool=None; between=[]
    for e in ev:
        if e[0]=='tool': last_tool=e[2]
        if e[0] in('gate','notif','msg'): between.append(e[0])
        if e[0]=='req':
            cw,cr,mo=e[2]
            if last_req and (e[1]-last_req).total_seconds()>300 and cw>20000:
                k='gate (SubagentStop/Stop hook)' if 'gate' in between else 'msg from coordinator (resume/SendMessage)' if 'msg' in between else 'bg task notification' if 'notif' in between else (last_tool or '?')
                k=re.sub(r'(Bash:)([^:]*)',lambda m:m.group(1)+m.group(2),k)
                cause[k]+=1; money[k]+=cw*(P[mo][0]-P[mo][1])/1e6; gaps[k]+=(e[1]-last_req).total_seconds()
                role[(meta.get('agentType') or '?')]+=cw*(P[mo][0]-P[mo][1])/1e6
            last_req=e[1]; between=[]
T=sum(money.values())
print('events',sum(cause.values()),'extra cost $%.0f'%T)
for k,v in money.most_common(18): print(f'  ${v:5.0f} {cause[k]:4} med~{gaps[k]/cause[k]/60:5.1f}m  {k}')
print({k:round(v) for k,v in role.most_common(6)})
