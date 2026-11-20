import glob,json,os,collections,re
SINCE='2026-11-13'; CAP=int(os.environ.get('CAP','4000'))
tot=0; saved=0; bycmd=collections.Counter(); cnt=collections.Counter(); T=0
for d in glob.glob(os.path.expanduser('~/.claude/projects/-home-rustam-develop-simbioz-team-*')):
  for f in glob.glob(d+'/*/subagents/**/*.jsonl',recursive=True):
    try: meta=json.load(open(f[:-6]+'.meta.json'))
    except: meta={}
    if 'implementer' not in (meta.get('agentType') or ''): continue
    ev=[];names={};first=None;seen=set()
    for line in open(f,errors='replace'):
        try:o=json.loads(line)
        except:continue
        if first is None: first=o.get('timestamp','')
        if o.get('type')=='assistant':
            m=o.get('message') or {}
            if m.get('usage') and m.get('id') not in seen:
                seen.add(m.get('id')); u=m['usage']; ctx=u.get('input_tokens',0)+u.get('cache_read_input_tokens',0)+u.get('cache_creation_input_tokens',0)
                ev.append(('req',ctx,0.1 if 'sonnet' in m.get('model','') else 0.2))
            for c in m.get('content') or []:
                if isinstance(c,dict) and c.get('type')=='tool_use':
                    cmd=(c.get('input') or {}).get('command') or ''
                    cmd=re.sub(r'^\s*cd\s+\S+\s*(&&|;)\s*','',cmd)
                    names[c['id']]=c['name']+':'+(cmd.split()[0] if cmd.split() else '')
        elif o.get('type')=='user':
            for c in (o.get('message') or {}).get('content') or []:
                if isinstance(c,dict) and c.get('type')=='tool_result':
                    x=c.get('content'); L=len(x) if isinstance(x,str) else sum(len(y.get('text','')) for y in x if isinstance(y,dict)) if isinstance(x,list) else 0
                    ev.append(('out',L,names.get(c.get('tool_use_id'),'?')))
    if not first or first<SINCE: continue
    # rereads: for each output, count following reqs until compaction (ctx drop >40%)
    for i,e in enumerate(ev):
        if e[0]!='out': continue
        L=e[1]; k=e[2]; tok=L/3.5; ex=max(0,L-CAP)/3.5; rr=0; prev=None; price=0
        for e2 in ev[i+1:]:
            if e2[0]!='req': continue
            if prev and e2[1]<prev*0.6: break
            prev=e2[1]; rr+=1; price=e2[2]
        c=tok*rr*price/1e6; s=ex*rr*price/1e6
        tot+=c; saved+=s; bycmd[k]+=c; cnt[k]+=L
print(f'cost of carrying tool output (cache reads) ${tot:.0f}; saving if each output capped at {CAP} chars: ${saved:.0f}')
for k,v in bycmd.most_common(12): print(f'  {k:28} ${v:6.0f}  {cnt[k]/1e6:5.1f}M chars')
