"""Расписание плана f3-A: HLFET, K исполнителей, пул ревью R, вливание 3 мин.
deps: старт после вливания предка; stack: старт после сдачи предка;
mafter: вливание только после вливания указанных (старт по контракту).
Монте-Карло: отказ ревью p -> доработка 0.5w + повторное ревью 5 мин (≤2 круга);
у задач с mafter при вливании интеграционный сбой с вероятностью qi -> доработка 0.5w."""
import random, sys, statistics as st
D=10
def w(deep,M): return D*(1.6 if deep else 1)*(1.5 if M else 1)
T={ # id: (kind, deep, M, deps, stack, mafter)
 'T001':('K',0,1,[],[],[]),
 'T002':('K',1,1,[],['T001'],[]),
 'T003':('K',0,1,[],['T001'],[]),
 'T004':('K',0,0,[],[],[]),
 'T005':('T',0,1,[],[],[]),
 'T006':('T',0,0,[],[],[]),
 'T007':('T',0,1,[],[],[]),
 'T008':('T',0,1,[],[],[]),
 'T009':('T',0,1,[],[],[]),
 'T010':('T',0,0,[],[],[]),
 'T011':('V',1,1,['T002','T003','T005'],[],[]),
 'T012':('V',0,1,['T003','T005'],[],[]),
 'T013':('V',1,1,['T002','T003','T006'],[],[]),
 'T014':('V',0,1,['T004'],[],[]),
 'T015':('S',1,1,['T002','T007'],[],[]),
 'T016':('V',1,0,['T002','T003','T010'],[],[]),
 'T017':('V',1,1,['T002','T003','T008'],[],['T011','T013']),
 'T018':('V',0,1,['T004'],[],[]),
 'T019':('V',1,1,['T004','T009'],[],[]),
 'T020':('V',0,1,['T004'],[],[]),
 'T021':('H',0,1,['T011','T012','T013','T014','T015','T016','T017','T018','T019','T020'],[],[]),
}
import os
V=os.environ.get('VAR','')
if 'nostack' in V:
    for k in ('T002','T003'): a=list(T[k]); a[3]=['T001']; a[4]=[]; T[k]=tuple(a)
if 'seq17' in V:
    a=list(T['T017']); a[3]=a[3]+['T011','T013']; a[5]=[]; T['T017']=tuple(a)
# [T] не блокирует старт среза (только вливание): переводим T-зависимости в mafter
for k,(kind,de,M,deps,stk,maf) in list(T.items()):
    td=[d for d in deps if T[d][0]=='T']
    T[k]=(kind,de,M,[d for d in deps if T[d][0]!='T'],stk,maf+td)
W={k:w(v[1],v[2]) for k,v in T.items()}
REV=8; MERGE=3
succ={k:[] for k in T}
for k,v in T.items():
    for d in v[3]+v[4]+v[5]: succ[d].append(k)
bl={}
def blev(k):
    if k not in bl: bl[k]=W[k]+REV+MERGE+max([blev(s) for s in succ[k]],default=0)
    return bl[k]
for k in T: blev(k)
STARTS={}
def run(K,R=3,p=0.0,qi=0.0,seed=0):
    rnd=random.Random(seed)
    t=0.0; submitted={}; merged={}; started=set(); busy=[] # (end,task,kind)
    revq=[]; revbusy=[]; pending=[] # submitted waiting merge
    rounds={k:0 for k in T}; rework=[]  # tasks needing rework
    integ_done=set(); occ=0.0; last=0.0; events=[]
    def ready(k):
        kind,de,M,deps,stk,maf=T[k]
        return all(d in merged for d in deps) and all(d in submitted for d in stk)
    while len(merged)<len(T):
        # free slots: rework first by rank, then new
        while len(busy)<K:
            cand=[(bl[k],k,'rw') for k in rework]+[(bl[k],k,'new') for k in T if k not in started and ready(k)]
            if not cand: break
            cand.sort(reverse=True); _,k,typ=cand[0]
            if typ=='rw': rework.remove(k); dur=0.5*W[k]
            else: started.add(k); dur=W[k]
            busy.append((t+dur,k,typ)); STARTS.setdefault(k,t)
        while len(revbusy)<R and revq:
            k=revq.pop(0); revbusy.append((t+(REV if rounds[k]==0 else 5),k))
        # merge pending
        progressed=True
        while progressed:
            progressed=False
            for k in list(pending):
                kind,de,M,deps,stk,maf=T[k]
                if all(d in merged for d in stk+maf):
                    if maf and k not in integ_done and T[k][0]!='T' and any(T[d][0]!='T' for d in maf):
                        integ_done.add(k)
                        if rnd.random()<qi:
                            pending.remove(k); rework.append(k); submitted.pop(k,None); progressed=True; continue
                    pending.remove(k); merged[k]=t+MERGE; events.append((t+MERGE,'merge',k)); progressed=True
        # next event
        nxt=[e for e,_,_ in busy]+[e for e,_ in revbusy]+[v for v in merged.values() if v>t]
        if not nxt and rework:
            continue
        if not nxt:
            if len(merged)<len(T) and not pending: raise SystemExit(f'deadlock {set(T)-set(merged)} started={"T017" in started} sub={submitted.get("T017")} rw={rework}')
            nxt=[t+0.01]
        t2=min(nxt); occ+=len(busy)*(t2-t); t=t2
        for e in list(busy):
            if e[0]<=t: busy.remove(e); submitted[e[1]]=t; revq.append(e[1])
        for e in list(revbusy):
            if e[0]<=t:
                revbusy.remove(e); k=e[1]
                if rounds[k]<2 and rnd.random()<p: rounds[k]+=1; rework.append(k); submitted.pop(k,None)
                else: pending.append(k)
        # merged timestamps in future: treat as merged now for readiness only when time reached
        for k,v in list(merged.items()):
            pass
        last=max(merged.values()) if merged else 0
    return max(merged.values()), occ/max(merged.values()), merged
if __name__=='__main__':
    Wt=sum(W.values())
    # span
    memo={}
    def sp(k):
        if k in memo: return memo[k]
        kind,de,M,deps,stk,maf=T[k]
        pre=[sp(d)+REV+MERGE for d in deps]+[sp(d) for d in stk]
        memo[k]=W[k]+max(pre,default=0); return memo[k]
    S=max(sp(k) for k in T)
    Spure={}
    def sp2(k):
        if k in Spure: return Spure[k]
        kind,de,M,deps,stk,maf=T[k]
        Spure[k]=W[k]+max([sp2(d) for d in deps+stk],default=0); return Spure[k]
    S2=max(sp2(k) for k in T)
    print(f"W={Wt:.0f} S(work only)={S2:.0f} P={Wt/S2:.2f}  S(with review+merge on links)={S:.0f}")
    print("K-phase share", sum(W[k] for k in T if T[k][0]=='K')/Wt)
    for K in (3,4,5):
        mk,occ,m=run(K)
        res=[]
        for p,qi in ((0.43,0.3),(0.3,0.2),(0.15,0.1)):
            xs=[run(K,R=max(3,K-1),p=p,qi=qi,seed=s) for s in range(300)]
            res.append(f"p={p}: {st.mean(x[0] for x in xs):.0f} (occ {st.mean(x[1] for x in xs):.2f})")
        print(f"K={K}: det {mk:.0f} occ {occ:.2f} | "+" | ".join(res))
    STARTS.clear(); mk,occ,m=run(4)
    print('starts', {k:round(v) for k,v in sorted(STARTS.items(), key=lambda x:x[1])})
    print('submitted', {k:round(STARTS[k]+W[k]) for k in sorted(STARTS, key=lambda x:STARTS[x])})
    for k,v in sorted(m.items(), key=lambda x:x[1]): print(k, f"{v:.0f}", end='; ')
    print()
