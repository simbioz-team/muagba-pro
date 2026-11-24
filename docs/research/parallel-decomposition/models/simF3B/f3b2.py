"""Вариант круга 1 с e2e-подготовкой [T] и приоритетом ревью по рангу.
run(N,R,p,seed,revprio, spine_inline) -> (время до вливания H, до конца приёмок+CI, занятость, запуски исп., запуски ревью)
spine_inline: ревью по ходу на звеньях пути (K1,J,CJ,WS,QS): ревью после сдачи 3 мин вместо 8, но +1 запуск ревью по ходу."""
import random, heapq, statistics as st
import f3b
T=dict(f3b.T)
T['E1']=('T',0,'M',[],[]); T['E2']=('T',0,'M',['K3'],[])
MA=dict(f3b.MERGE_AFTER)
ACC={'A1':(['QS','QC','MIG','REF','J','E1'],25),'A2':(['A1','WS','FC','UC','RP','E2'],30)}
SPINE={'K1','J','CJ','WS','QS'}
def w(k):
    v,d,s,_,_=T[k]; return 10*(1.6 if d else 1)*(1.5 if s=='M' else 1)
def span():
    m={}
    def f(k):
        if k in m: return m[k]
        m[k]=w(k)+max([f(d) for d in T[k][3]+T[k][4]],default=0); return m[k]
    for k in T: f(k)
    return max(m.values()),m
def run(N,R,p,seed,revprio=True,inline=False,tailci=50):
    rnd=random.Random(seed)
    succ={k:[x for x in T if k in T[x][3]+T[x][4]] for k in T}; rank={}
    def r(k):
        if k not in rank: rank[k]=w(k)+max([r(x) for x in succ[k]],default=0)
        return rank[k]
    for k in T: r(k)
    t=0;ev=[];free=N;frev=R;ready=[];revq=[];handed=set();merged={};started=set();approved=set()
    rounds={k:0 for k in T};busy=0;area=0;runs=0;revruns=0;acc_free=1;acc_st=set();acc_done={}
    def can(k): return all(d in merged for d in T[k][3]) and all(d in handed for d in T[k][4])
    def try_merge():
        ch=True
        while ch:
            ch=False
            for k in list(approved):
                if k in merged: continue
                need=MA.get(k,[])+T[k][4]
                if all((d in merged) or (d in approved and k in MA.get(d,[])) for d in need):
                    merged[k]=t;ch=True
    def disp():
        nonlocal free,frev,busy,runs,revruns,acc_free
        for k in T:
            if k not in started and can(k): started.add(k);ready.append((k,'impl'))
        ready.sort(key=lambda x:(x[1]!='rework',-rank[x[0]]))
        while free and ready:
            k,kind=ready.pop(0);free-=1;busy+=1;runs+=1
            d=w(k)*rnd.uniform(.7,1.4) if kind=='impl' else 7*(w(k)/10)*rnd.uniform(.7,1.4)
            if inline and k in SPINE and kind=='impl': revruns+=1
            heapq.heappush(ev,(t+d,'hand',k))
        if revprio: revq.sort(key=lambda k:-rank[k])
        while frev and revq:
            k=revq.pop(0);frev-=1;revruns+=1
            base=3 if (inline and k in SPINE) else 8
            heapq.heappush(ev,(t+base*rnd.uniform(.7,1.4),'rev',k))
        for a,(ds,dur) in ACC.items():
            if a not in acc_st and acc_free and all((d in merged) or (d in acc_done) for d in ds):
                acc_st.add(a);acc_free-=1;heapq.heappush(ev,(t+dur*rnd.uniform(.8,1.4),'acc',a))
    disp()
    while ev:
        nt,e,k=heapq.heappop(ev);area+=busy*(nt-t);t=nt
        if e=='hand': free+=1;busy-=1;handed.add(k);revq.append(k)
        elif e=='rev':
            frev+=1
            pp=p*(0.7 if (inline and k in SPINE) else 1)
            if rounds[k]<2 and rnd.random()<pp: rounds[k]+=1;ready.append((k,'rework'))
            else: approved.add(k);heapq.heappush(ev,(t+2,'mrg',k))
        elif e=='mrg': try_merge()
        elif e=='acc': acc_free+=1;acc_done[k]=t
        disp()
    H=merged['H']; end=max(max(acc_done.values()),H)+tailci
    return H,end,area/H,runs,revruns
if __name__=='__main__':
    W=sum(w(k) for k in T);S,m=span();print(f'W={W:.0f} S={S:.0f} P={W/S:.2f}; K-фаза {sum(w(k) for k in T if T[k][0]=="K")/W:.0%}')
    for K in (3,4,5): print(f'  K={K}: {max(W/K,S):.0f}..{W/K+S:.0f}')
    for p in (0.0,0.15,0.3,0.43):
        for K in (3,4,5):
            for prio,inl in ((False,False),(True,False),(True,True)):
                rs=[run(K,max(K-1,2),p,s,prio,inl) for s in range(400)]
                print(f'p={p} K={K} prio={int(prio)} inline={int(inl)}: H {st.median(r[0] for r in rs):.0f}, конец {st.median(r[1] for r in rs):.0f} (P90 {sorted(r[1] for r in rs)[360]:.0f}), занятость {st.mean(r[2] for r in rs):.2f}, исп {st.mean(r[3] for r in rs):.1f}, ревью {st.mean(r[4] for r in rs):.1f}')
