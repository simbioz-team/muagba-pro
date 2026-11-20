import glob,json,os,csv,sys
P={'opus':(4,20,5,8,.2),'sonnet':(2,10,2.5,4,.1),'haiku':(.1,.5,.125,.2,.01),'fable':(10,50,12.5,20,.5)}
def fam(m):
    m=m or ''
    for k in P:
        if k in m: return k
    return 'opus'
w=csv.writer(open(sys.argv[1],'w'))
w.writerow(['proj','session','sub','type','desc','model','start','req','inp','cw5','cw1h','cr','out','cost'])
for d in glob.glob(os.path.expanduser('~/.claude/projects/-home-rustam-develop-simbioz-team-*')):
    proj=os.path.basename(d).replace('-home-rustam-develop-simbioz-team-','')
    for f in glob.glob(d+'/*/subagents/**/*.jsonl',recursive=True):
        mf=f[:-6]+'.meta.json'
        try: meta=json.load(open(mf))
        except: meta={}
        seen={};start=None;models=set()
        for line in open(f,errors='replace'):
            try:o=json.loads(line)
            except:continue
            if start is None and o.get('timestamp'): start=o['timestamp']
            m=o.get('message') if o.get('type')=='assistant' else None
            if isinstance(m,dict) and m.get('usage'): seen[m.get('id')]=(m.get('model'),m['usage'])
        if not seen: continue
        t=dict(inp=0,cw5=0,cw1h=0,cr=0,out=0);cost=0
        for mo,u in seen.values():
            if mo and 'synthetic' in mo: continue
            models.add(fam(mo));p=P[fam(mo)]
            cc=u.get('cache_creation') or {}
            c1=cc.get('ephemeral_1h_input_tokens',0); c5=u.get('cache_creation_input_tokens',0)-c1
            v=dict(inp=u.get('input_tokens',0),cw5=c5,cw1h=c1,cr=u.get('cache_read_input_tokens',0),out=u.get('output_tokens',0))
            for k in t:t[k]+=v[k]
            cost+=(v['inp']*p[0]+v['out']*p[1]+v['cw5']*p[2]+v['cw1h']*p[3]+v['cr']*p[4])/1e6
        sess=f.split('/subagents/')[0].split('/')[-1][:8]
        w.writerow([proj,sess,os.path.basename(f)[6:20],meta.get('agentType'),(meta.get('description') or '')[:80],'+'.join(sorted(models)),start,len(seen),t['inp'],t['cw5'],t['cw1h'],t['cr'],t['out'],round(cost,2)])
