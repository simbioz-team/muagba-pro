"""F2 team A plan: work/span probe + HLFET Monte Carlo (K slots, R reviewers, rework p, CI batches)."""
import random, statistics, sys
# id: (kind, weight, deps, stack_deps, merge_only, story)
T = {}
def t(i,k,w,deps=(),stack=(),mo=(),story=None): T[i]=dict(k=k,w=w,deps=list(deps),stack=list(stack),mo=list(mo),story=story)
K=('T001','T002','T003','T004')
t('T001','K',24); t('T002','K',15); t('T003','K',24); t('T004','K',15)
for i,s,w in [('T005','US1',10),('T006','US2',15),('T007','US3',15),('T008','US4',10),('T009','US5',15),('T010','US6',10),('T011','US7',10),('T012','US8',10)]:
    t(i,'T',w,mo=['T001','T002','T003','T004'],story=s)
TS={'US1':'T005','US2':'T006','US3':'T007','US4':'T008','US5':'T009','US6':'T010','US7':'T011','US8':'T012'}
L='T013'
t('T013','V',15,['T001','T002','T003'],story='US1')
t('T014','V',15,['T004'],story='US1')
t('T015','V',10,['T004'],story='US1')
t('T016','V',15,[],story='US2')
t('T017','V',24,['T002','T003'],story='US2')
t('T018','V',24,['T001','T002'],story='US2')
t('T019','V',24,['T002','T003'],mo=[L],story='US2')
t('T020','V',24,['T001','T002'],story='US3')
t('T021','V',24,['T001','T002'],story='US3')
t('T022','V',16,['T001','T002'],story='US3')
t('T023','S',24,['T001','T002'],story='US4')
t('T024','S',24,['T001'],stack=['T023'],story='US4')
t('T025','V',24,['T001','T003'],mo=[L],story='US4')
t('T026','V',10,['T001'],story='US3')
t('T027','V',24,['T004'],story='US4')
t('T028','V',15,['T002','T003'],mo=[L],story='US5')
t('T029','V',15,['T002'],story='US5')
t('T030','V',24,['T002','T003'],mo=[L],story='US5')
t('T031','V',24,['T001','T002','T003'],mo=[L],story='US6')
t('T032','V',10,['T004'],story='US6')
t('T033','V',15,['T001','T003'],mo=[L],story='US6')
t('T034','V',10,['T001'],story='US6')
t('T035','V',24,['T001'],story='US7')
t('T036','V',16,['T001'],story='US7')
t('T037','V',10,[],story='US7')
t('T038','V',10,[],story='US7')
t('T039','S',24,['T001','T002'],story='US8')
t('T040','S',16,[],stack=['T039'],story='US8')
t('T041','S',10,[],stack=['T040'],story='US8')
t('T042','V',10,[],story=None)
t('T043','H',15,[i for i in T if i!='T043'])
# probe
succ={i:[] for i in T}
for i,d in T.items():
    for p in d['deps']+d['stack']+d['mo']: succ[p].append(i)
rank={}
def r(i):
    if i in rank: return rank[i]
    rank[i]=T[i]['w']+max([r(s) for s in succ[i]] or [0]); return rank[i]
for i in T: r(i)
W=sum(d['w'] for d in T.values()); S=max(rank.values())
start=[i for i in T if not (T[i]['deps']+T[i]['stack']+T[i]['mo'])]
# critical path
cp=[max(start,key=lambda i:rank[i])]
while succ[cp[-1]]: cp.append(max(succ[cp[-1]],key=lambda i:rank[i]))
print(f"N={len(T)} W={W} S={S} P={W/S:.2f} Kphase={sum(T[k]['w'] for k in K)} ({sum(T[k]['w'] for k in K)/W:.0%})")
print("CP:", ' -> '.join(f"{c}({T[c]['w']})" for c in cp))
for k in (3,4,5): print(f"K={k}: bounds {max(W/k,S):.0f}..{W/k+S:.0f}")

def sim(Kslots,R,p,seed,rev=8,ci=21,batch_max=6,noise=0.3):
    rnd=random.Random(seed)
    dur={i:T[i]['w']*rnd.lognormvariate(0,noise) for i in T}
    state={i:'wait' for i in T}; submitted={}; merged={}; rounds={i:0 for i in T}
    ready_rework=[]; now=0.0; events=[]  # (time, type, id)
    busy=0; rq=[]; rbusy=0; busy_int=0.0; last=0.0
    accepted=set(); cinq=[]; ci_free=0.0; ci_end=0.0
    import heapq
    def can_start(i):
        d=T[i]
        if state[i]!='wait': return False
        if any(p not in merged for p in d['deps']): return False
        if any(p not in submitted for p in d['stack']): return False
        return True
    def can_merge(i):
        d=T[i]
        if i not in accepted or i in merged: return False
        pre=d['deps']+d['stack']+d['mo']
        if d['story'] and d['k'] in 'VS': pre=pre+[TS[d['story']]]
        return all(p in merged for p in pre)
    def dispatch():
        nonlocal busy,rbusy
        while busy<Kslots:
            cand=[(rank[i],1,i,'re') for i in ready_rework]+[(rank[i],0,i,'new') for i in T if can_start(i)]
            if not cand: break
            cand.sort(reverse=True); _,_,i,typ=cand[0]
            if typ=='re': ready_rework.remove(i); d=dur[i]*0.5
            else: state[i]='run'; d=dur[i]
            busy+=1; heapq.heappush(events,(now+d,'done',i))
        while rbusy<R and rq:
            i=rq.pop(0); rbusy+=1; heapq.heappush(events,(now+rev*(1.25 if T[i]['w']>=16 else 1),'rev',i))
    def try_merge():
        changed=True
        while changed:
            changed=False
            for i in T:
                if can_merge(i): merged[i]=now; cinq.append(i); changed=True
    dispatch()
    while events:
        tt,typ,i=heapq.heappop(events)
        busy_int+=busy*(tt-last); last=tt; now=tt
        if typ=='done':
            busy-=1; submitted.setdefault(i,now); rq.append(i)
        elif typ=='rev':
            rbusy-=1; rounds[i]+=1
            if T[i]['k']!='H' and rounds[i]<=2 and rnd.random()<(p if rounds[i]==1 else p/2): ready_rework.append(i)
            else: accepted.add(i); try_merge()
        dispatch()
    end_impl=now
    # CI: dynamic batches over merge times
    ms=sorted(merged.values()); t0=0; k=0; ci_runs=0
    while k<len(ms):
        t0=max(t0,ms[k]); n=0
        while k<len(ms) and ms[k]<=t0 and n<batch_max: k+=1; n+=1
        t0+=ci; ci_runs+=1
    return end_impl, t0, busy_int/end_impl, ci_runs
for Ks,R in ((3,2),(4,3),(5,4)):
  for p in (0.43,0.25,0.15):
    res=[sim(Ks,R,p,s) for s in range(300)]
    e=[x[0] for x in res]; c=[x[1] for x in res]; u=[x[2] for x in res]; n=[x[3] for x in res]
    print(f"K={Ks} R={R} p={p}: impl+review+merge med {statistics.median(e):.0f} (p90 {sorted(e)[270]:.0f}); with CI med {statistics.median(c):.0f}; busy {statistics.mean(u):.2f}; CI runs {statistics.mean(n):.1f}")
print("--- CI variants, K=4 R=3 p=0.43/0.25")
for p in (0.43,0.25):
  for bm,ci in ((4,21),(99,21)):
    res=[sim(4,3,p,s,ci=ci,batch_max=bm) for s in range(300)]
    print(f"p={p} batch_max={bm} ci={ci}: with CI med {statistics.median([x[1] for x in res]):.0f}, runs {statistics.mean([x[3] for x in res]):.1f}")
