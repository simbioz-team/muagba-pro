"""Фича 3, команда B, круг 1: проба плана и событийная модель.
Вес: 10 мин x1.6 deep x1.5 M. Ревью 8, доработка 7*w (до 2 кругов), вливание 2.
Режим pipe: слот свободен при сдаче; зависимость снимается вливанием; (стек) - сданием.
Приёмки A1, A2 - отдельный пул acceptance (1 стенд trn, serial)."""
import random, heapq, statistics as st, sys
T = {  # id: (вид, deep, size, deps, stack_deps)
 'K1':('K',1,'M',[],[]), 'K2':('K',0,'M',[],[]), 'K3':('K',0,'M',[],[]),
 'TJ':('T',0,'M',[],[]), 'TM':('T',0,'S',[],[]), 'TR':('T',0,'M',[],[]), 'TQ':('T',0,'S',[],[]),
 'TW':('T',0,'M',[],[]), 'TF':('T',0,'M',[],[]), 'TQC':('T',0,'S',[],[]), 'TK':('T',0,'S',[],[]),
 'J':('S',1,'M',['K1'],[]), 'CJ':('S',1,'S',['K1'],['J']), 'MIG':('S',1,'M',['K1'],[]),
 'REF':('V',1,'M',['K1','K2'],[]), 'QS':('V',1,'M',['CJ','REF'],[]), 'QC':('V',0,'M',['K3'],[]),
 'WS':('V',1,'M',['CJ','REF','K2'],[]), 'FC':('V',0,'M',['K3'],[]), 'UC':('V',0,'M',['K3'],[]),
 'RP':('V',1,'S',['J','REF','K2'],[]),
 'H':('H',0,'S',['QS','QC','WS','FC','UC','RP','MIG'],[]),
}
# вливание среза — после своих [T]
MERGE_AFTER = {'J':['TJ'],'MIG':['TM','QS'],'REF':['TR'],'QS':['TQ','QC'],'QC':['TQC','QS'],
               'WS':['TW'],'FC':['TF'],'UC':['FC'],'RP':['TK']}
ACC = {'A1':['QS','QC','MIG','REF','J'], 'A2':['A1','WS','FC','UC','RP']}
ACC_DUR = 45
def w(k):
    v,d,s,_,_=T[k]; return 10*(1.6 if d else 1)*(1.5 if s=='M' else 1)
def W(): return sum(w(k) for k in T)
def span():
    m={}
    def f(k):
        if k in m: return m[k]
        m[k]=w(k)+max([f(d) for d in T[k][3]+T[k][4]],default=0); return m[k]
    return max(f(k) for k in T), m
def run(N,R,p,seed,rev=8,rework=7,merge=2):
    rnd=random.Random(seed); S,_=span()
    succ={k:[x for x in T if k in T[x][3]+T[x][4]] for k in T}
    rank={}
    def r(k):
        if k not in rank: rank[k]=w(k)+max([r(x) for x in succ[k]],default=0)
        return rank[k]
    for k in T: r(k)
    t=0; ev=[]; free=N; frev=R; ready=[]; revq=[]; handed=set(); merged=set(); started=set()
    approved=set(); rounds={k:0 for k in T}; busy_area=0; last=0; busy=0; runs=0; revruns=0
    acc_free=1; acc_started=set(); acc_done={}
    def push(a,b,c): heapq.heappush(ev,(a,b,c))
    def can_start(k):
        return all(d in merged for d in T[k][3]) and all(d in handed for d in T[k][4])
    def try_merge():
        ch=True
        while ch:
            ch=False
            for k in list(approved):
                if k in merged: continue
                need=MERGE_AFTER.get(k,[])+T[k][4]
                # половины (QS/QC) и MIG вливаются партией: достаточно одобрения
                ok=all((d in merged) or (d in approved and k in MERGE_AFTER.get(d,[])) for d in need)
                if ok:
                    merged.add(k); ch=True
    def dispatch():
        nonlocal free,frev,busy,runs,revruns,acc_free
        for k in T:
            if k not in started and can_start(k): started.add(k); ready.append((k,'impl'))
        ready.sort(key=lambda x:(x[1]!='rework',-rank[x[0]]))
        while free and ready:
            k,kind=ready.pop(0); free-=1; busy+=1; runs+=1
            d=w(k)*rnd.uniform(.7,1.4) if kind=='impl' else rework*(w(k)/10)*rnd.uniform(.7,1.4)
            push(t+d,'hand',k)
        while frev and revq:
            k=revq.pop(0); frev-=1; revruns+=1; push(t+rev*rnd.uniform(.7,1.4),'rev',k)
        for a,ds in ACC.items():
            if a not in acc_started and acc_free and all((d in merged) or (d in acc_done) for d in ds):
                acc_started.add(a); acc_free-=1; push(t+ACC_DUR*rnd.uniform(.8,1.3),'acc',a)
    dispatch()
    while ev:
        nt,e,k=heapq.heappop(ev); busy_area+=busy*(nt-t); t=nt
        if e=='hand':
            free+=1; busy-=1; handed.add(k); revq.append(k)
        elif e=='rev':
            frev+=1
            if rounds[k]<2 and rnd.random()<p: rounds[k]+=1; ready.append((k,'rework'))
            else: approved.add(k); push(t+merge,'mrg',k)
        elif e=='mrg': try_merge()
        elif e=='acc': acc_free+=1; acc_done[e and k]=t
        dispatch()
    impl_end=max(acc_done.values())
    return t, busy_area/t, runs, revruns
if __name__=='__main__':
    S,m=span(); print(f'W={W():.0f} S={S:.0f} P={W()/S:.2f}')
    path=[];k=max(T,key=lambda x:m[x])
    for K in (3,4,5):
        print(f'K={K}: границы {max(W()/K,S):.0f}..{W()/K+S:.0f}')
    for p in (0.0,0.2,0.3,0.43):
        for K in (3,4,5):
            res=[run(K,max(K-1,2),p,s) for s in range(300)]
            print(f'p={p} K={K} R={max(K-1,2)}: T={st.median(r[0] for r in res):.0f} мин, занятость {st.mean(r[1] for r in res):.2f}, запусков исп. {st.mean(r[2] for r in res):.1f}, ревью {st.mean(r[3] for r in res):.1f}')
