"""Расписание плана f3-A круг 2: HLFET + «К первыми», K исполнителей, пул ревью R,
вливание 3 мин. deps — старт после вливания; stack — после сдачи (вливание после предка);
mafter — вливание после вливания указанных; BATCH — партия: вливаются только вместе.
Монте-Карло: отказ ревью p → доработка 0.5w новым запуском + ревью 5 мин (≤ 2 круга);
задача с mafter от [V]/[S] на rebase: сбой qi → доработка 0.5w без ревью;
партия: сбой сборки qb → доработка 0.5w случайного члена."""
import random, os, statistics as st
D=10
def w(deep,M,S16=False): return D*(1.6 if deep else 1)*(1.5 if M else 1)
T={ # id: (kind, deep, M, deps, stack, mafter)
 'T001c':('K',0,0,[],[],[]),          # контрактный коммит C0, 5 мин, скриптовая сверка
 'T001':('K',1,1,[],['T001c'],[]),    # остаток T001: 19 мин (24 - 5)
 'T002':('K',1,1,['T001c'],[],[]),
 'T003':('K',0,1,['T001c'],[],[]),
 'T004':('K',0,1,[],[],[]),
 'T005':('T',0,1,[],[],[]),
 'T006':('T',0,0,[],[],[]),
 'T007':('T',0,1,[],[],[]),
 'T008':('T',0,1,[],[],[]),
 'T009':('T',0,1,[],[],[]),
 'T010':('T',0,0,[],[],[]),
 'T011':('T',0,1,[],[],[]),
 'T012':('S',1,1,['T001','T002','T011'],[],[]),
 'T013':('S',1,1,['T001','T002','T003','T011'],[],[]),
 'T014':('V',1,1,['T003','T004','T012','T005'],[],[]),
 'T015':('V',0,1,['T004','T005'],[],[]),
 'T016':('S',1,0,['T003'],['T012','T013'],[]),
 'T017':('V',1,1,['T006'],['T016'],['T014']),
 'T018':('V',0,1,['T004','T006'],[],[]),
 'T019':('S',1,1,['T002','T003','T007'],[],[]),
 'T020':('V',1,0,['T001','T003','T013','T010'],[],['T017','T018','T019']),
 'T021':('V',0,1,['T003','T004','T012','T008'],[],['T014','T017','T018','T019']),
 'T022':('V',1,1,['T003','T004','T012','T013','T008'],[],['T014','T017','T018','T019']),
 'T023':('V',1,0,['T016','T008'],['T022'],['T017','T018','T019']),
 'T024':('V',0,1,['T004'],[],[]),
 'T025':('V',1,1,['T004','T009'],[],[]),
 'T026':('V',0,1,['T004'],[],[]),
}
BATCH={'T017','T018','T019'}
LOOK=float(os.environ.get('LOOK','0'))
RW=float(os.environ.get('RW','0.7'))
V=os.environ.get('VAR','')
if 'stackK' in V:  # вариант: T002/T003 стеком от сданного T001 целиком (П-1 круга 2)
    for k in ('T002','T003'): a=list(T[k]); a[3]=[]; a[4]=['T001']; T[k]=tuple(a)
if 'noC0' in V:  # без контрактного коммита: T002/T003 от влитого T001 (24)
    for k in ('T002','T003'): a=list(T[k]); a[3]=['T001']; T[k]=tuple(a)
if 'nobatch' in V: BATCH=set()
KFIRST=('nokfirst' not in V)
if 'qread' in V:  # T014 часть очереди обратно в T014 (как r2): T017 без mafter T014
    a=list(T['T017']); a[5]=[]; T['T017']=tuple(a)
names=sorted(T)
last='T027'
T[last]=('H',0,1,[k for k in names if T[k][0] in 'VS'],[],[])
for k,(kind,de,M,deps,stk,maf) in list(T.items()):
    td=[d for d in deps if T[d][0]=='T']
    T[k]=(kind,de,M,[d for d in deps if T[d][0]!='T'],stk,maf+td)
W={k:w(v[1],v[2]) for k,v in T.items()}
W['T001c']=5; W['T001']=19
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
def run(K,R=3,p=0.0,qi=0.0,qb=0.0,seed=0):
    rnd=random.Random(seed)
    t=0.0; submitted={}; merged={}; started=set(); busy=[]
    revq=[]; revbusy=[]; pending=[]; rounds={k:0 for k in T}; rework=[]
    integ=set(); bdone=False; occ=0.0
    def ready(k):
        kind,de,M,deps,stk,maf=T[k]
        return all(d in merged and merged[d]<=t for d in deps) and all(d in submitted for d in stk)
    def pr(k): return ((1 if (KFIRST and T[k][0]=='K') else 0), bl[k])
    while len(merged)<len(T):
        while len(busy)<K:
            cand=[(pr(k),k,'rw') for k in rework]+[(pr(k),k,'new') for k in T if k not in started and ready(k)]
            if not cand: break
            cand.sort(reverse=True); _,k,typ=cand[0]
            if LOOK:
                imm=[j for j in T if j not in started and not ready(j) and all(d in submitted for d in T[j][3]+T[j][4]) and bl[j]>bl[k]+LOOK]
                if len(imm)>=K-len(busy): break
            if typ=='rw': rework.remove(k); dur=RW*W[k]
            else: started.add(k); dur=W[k]
            busy.append((t+dur,k)); STARTS.setdefault(k,t)
        while len(revbusy)<R and revq:
            k=revq.pop(0); revbusy.append((t+(1 if k=='T001c' else (REV if rounds[k]==0 else 5)),k))
        prog=True
        while prog:
            prog=False
            for k in list(pending):
                kind,de,M,deps,stk,maf=T[k]
                if not all(d in merged and merged[d]<=t for d in stk+maf): continue
                if k in BATCH:
                    if not BATCH<=set(pending)|set(merged): continue
                    grp=[b for b in BATCH if b not in merged]
                    if not all(all(d in merged and merged[d]<=t for d in T[b][4]+T[b][5] if d not in BATCH) for b in grp): continue
                    if not bdone:
                        bdone=True
                        if rnd.random()<qb:
                            b=rnd.choice(grp); pending.remove(b); rework.append(b); submitted.pop(b,None); bdone=False; prog=True; break
                    for b in grp: pending.remove(b); merged[b]=t+MERGE+2
                    prog=True; break
                if any(T[d][0] in 'VS' for d in maf) and k not in integ:
                    integ.add(k)
                    if rnd.random()<qi:
                        pending.remove(k); rework.append(k); submitted.pop(k,None); prog=True; continue
                pending.remove(k); merged[k]=t+MERGE; prog=True
        nxt=[e for e,_ in busy]+[e for e,_ in revbusy]+[v for v in merged.values() if v>t]
        if not nxt:
            if rework: continue
            raise SystemExit(f'deadlock {sorted(set(T)-set(merged))} pend={pending}')
        t2=min(nxt); occ+=len(busy)*(t2-t); t=t2
        for e in list(busy):
            if e[0]<=t: busy.remove(e); submitted[e[1]]=t; revq.append(e[1])
        for e in list(revbusy):
            if e[0]<=t:
                revbusy.remove(e); k=e[1]
                if k!='T001c' and rounds[k]<2 and rnd.random()<p: rounds[k]+=1; rework.append(k); submitted.pop(k,None)
                else: pending.append(k)
    end=max(merged.values()); return end, occ/end, merged
if __name__=='__main__':
    Wt=sum(W.values())
    m2={}
    def sp2(k):
        if k not in m2: m2[k]=W[k]+max([sp2(d) for d in T[k][3]+T[k][4]+[x for x in T[k][5] if T[x][0]!='T']],default=0)
        return m2[k]
    S2=max(sp2(k) for k in T)
    m3={}
    def sp3(k):
        if k not in m3: m3[k]=W[k]+max([sp3(d) for d in T[k][3]+T[k][4]],default=0)
        return m3[k]
    S3=max(sp3(k) for k in T)
    print(f"S(start edges only)={S3:.0f} P={Wt/S3:.2f}")
    # путь
    k=max(T,key=sp2); path=[k]
    while True:
        pre=T[k][3]+T[k][4]+[x for x in T[k][5] if T[x][0]!='T']
        if not pre: break
        k=max(pre,key=sp2); path.append(k)
    print(f"tasks={len(T)} W={Wt:.0f} S={S2:.0f} P={Wt/S2:.2f} path={'<-'.join(path)} Kshare={sum(W[k] for k in T if T[k][0]=='K')/Wt:.2f}")
    for K in (3,4,5):
        mk,occ,m=run(K,R=max(3,K-1))
        res=[]
        for p,qi,qb in ((0.43,0.3,0.3),(0.3,0.2,0.2),(0.15,0.1,0.1)):
            xs=[run(K,R=max(3,K-1),p=p,qi=qi,qb=qb,seed=s) for s in range(300)]
            e=sorted(x[0] for x in xs)
            res.append(f"p={p}: {st.mean(e):.0f} [p80 {e[240]:.0f}] occ {st.mean(x[1] for x in xs):.2f}")
        print(f"K={K}: det {mk:.0f} occ {occ:.2f} | "+" | ".join(res))
    if 'sched' in V:
        STARTS.clear(); mk,occ,m=run(4)
        for k in sorted(STARTS,key=lambda x:STARTS[x]): print(k,T[k][0],f"start {STARTS[k]:.0f} sub {STARTS[k]+W[k]:.0f} merged {m[k]:.0f}")
