import glob,json,os,statistics
SINCE='2026-11-13'; BASE=58e3
def load():
  for d in glob.glob(os.path.expanduser('~/.claude/projects/-home-rustam-develop-simbioz-team-*')):
    for f in glob.glob(d+'/*/subagents/**/*.jsonl',recursive=True):
      try: meta=json.load(open(f[:-6]+'.meta.json'))
      except: meta={}
      if 'implementer' not in (meta.get('agentType') or ''): continue
      seen={};first=None
      for line in open(f,errors='replace'):
        try:o=json.loads(line)
        except:continue
        if first is None: first=o.get('timestamp','')
        m=o.get('message') if o.get('type')=='assistant' else None
        if isinstance(m,dict) and m.get('usage') and m.get('id') not in seen:
          u=m['usage']; seen[m['id']]=(u.get('input_tokens',0)+u.get('cache_read_input_tokens',0)+u.get('cache_creation_input_tokens',0),0.1 if 'sonnet' in m.get('model','') else 0.2)
      if first and first>=SINCE and seen: yield list(seen.values())
A=list(load())
cur=sum(c*p for r in A for c,p in r)/1e6
comp=sum(1 for r in A for i in range(1,len(r)) if r[i][0]<r[i-1][0]*0.6)
print('agents',len(A),'read-equivalent context cost now $%.0f'%cur,'compactions',comp)
for CH in (150,100,80):
  new=0; extra=0
  for r in A:
    start=None
    for i,(c,p) in enumerate(r):
      if i%CH==0:
        start=c
        if i>0: extra+=int(0.15*CH)*(BASE+40e3)*p  # re-orientation
      if i>0 and c<r[i-1][0]*0.6: start=c-BASE  # compaction resets
      new+=max(BASE,BASE+c-start)*p if i%CH else BASE*p
  new=(new+extra)/1e6
  print(f'chunk {CH}: ${new:.0f} incl overhead ${extra/1e6:.0f}  saving {1-new/cur:.0%}')
