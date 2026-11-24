"""Фича 3, команда B, круг 2. Граф r2 + та же событийная модель, что f3b2 (ревью 8, доработка 7*w/10, вливание 2,
слот свободен при сдаче, зависимость снимается вливанием, (стек) — сдачей).
C0 — контрактный коммит T001 (types.py+registry.py, сверка с текстом контракта скриптом): ревью 3 мин, вливается с K1.
mode: 'r2' — план круга 2; 'r2nostack' — без стека от C0 (T002/T003 ждут вливания T001)."""
import random, heapq, statistics as st, sys
def graph(mode='r3'):
    """Круг 3. T003 без кодов; T006 не ждёт T003; T010 разрезан на T010 (запись, step_edits) и T029 (ручки очереди);
    T013 deep; T014 разрезан на T014 (показ) и T030 (редактор списка шагов). C0 подтягивается (как r2pull)."""
    T = {  # id: (вид, deep, size, deps, stack, w_override)
     'C0':('K',1,'S',[],[],5), 'K1':('K',1,'M',[],['C0'],19),
     'KS':('K',1,'M',[],[],None), 'KB':('K',0,'M',[],[],None), 'KC':('K',0,'M',[],[],None),
     'TJ':('T',0,'M',[],[],None),'TM':('T',0,'S',[],[],None),'TR':('T',0,'M',[],[],None),'TQ':('T',0,'S',[],[],None),
     'TQC':('T',0,'S',[],[],None),'TW':('T',0,'M',[],[],None),'TF':('T',0,'M',[],[],None),'TK':('T',0,'S',[],[],None),
     'TRU':('T',0,'S',[],[],None),'E1':('T',0,'M',[],[],None),'E2':('T',0,'M',[],[],None),
     'RD':('S',1,'M',['KS','K1'],[],None), 'J':('S',1,'M',['KS','K1'],[],None),
     'CJ':('S',1,'S',['KB'],['J','RD'],None), 'MIG':('S',1,'M',['KS','K1'],[],None),
     'REF':('V',1,'M',['K1','KB','RD'],[],None),
     'QS':('V',1,'M',['CJ','KB'],[],None),        # T010 запись очереди (step_edits)
     'QV':('V',0,'M',['KB','KS'],[],None),        # T029 ручки очереди
     'QC':('V',0,'M',['KC'],[],None),
     'WS':('V',1,'M',['CJ','KB','RD'],[],None),
     'FC':('V',1,'M',['KC'],[],None),             # T013 deep
     'FM':('V',1,'M',['KC'],[],None),             # T031 слияние при 409 (Р-6)
     'UC':('V',0,'M',['KC'],[],None),             # T014 показ
     'UE':('V',0,'M',['KC'],[],None),             # T030 редактор списка
     'RP':('V',1,'M',['J','KB','K1'],[],None), 'RU':('V',1,'S',['KB'],[],None),
     'H':('H',0,'S',['QS','QV','QC','WS','FC','FM','UC','UE','RP','MIG','REF','RU'],[],None),
    }
    MA={'C0':['K1'],'K1':['C0'],'J':['TJ'],'RD':['TJ'],'MIG':['TM','QS','QV','QC'],
        'QS':['TQ','QC','QV','MIG'],'QV':['TQ','TR','QS','QC','MIG','REF'],'QC':['TQC','QS','QV','MIG'],
        'REF':['TR'],'WS':['TW','REF'],'FC':['TF','FM'],'FM':['TF'],'UC':['FC'],'UE':['FC'],'RP':['TK'],'RU':['TRU']}
    return T,MA
ACC={'A1':(['QS','QV','QC','MIG','REF','J','E1'],25),'A2':(['A1','WS','FC','FM','UC','UE','RP','RU','E2'],30)}
MARANK=True
SPINE={'K1','KS','J','CJ','WS','QS','RD','WG'}
def mk(T):
    def w(k):
        v,d,s,_,_,o=T[k]
        return o if o is not None else 10*(1.6 if d else 1)*(1.5 if s=='M' else 1)
    return w
def span(T,w):
    m={}
    def f(k):
        if k in m: return m[k]
        m[k]=w(k)+max([f(d) for d in T[k][3]+T[k][4]],default=0); return m[k]
    for k in T: f(k)
    return max(m.values()),m
def crit(T,w):
    S,bl0=None,{}
    succ={k:[x for x in T if k in T[x][3]+T[x][4]] for k in T}
    def bl(k):
        if k not in bl0: bl0[k]=w(k)+max([bl(x) for x in succ[k]],default=0)
        return bl0[k]
    S,tl=span(T,w)
    S=max(bl(k) for k in T)
    return {k for k in T if abs(tl[k]+bl(k)-w(k)-S)<1e-9}
def run(T,MA,N,R,p,seed,inline=False,tailci=50,trace=False,overflow=False):
    w=mk(T); rnd=random.Random(seed); CR=crit(T,w); xtra=[0]
    succ={k:[x for x in T if k in T[x][3]+T[x][4] or (MARANK and k in MA.get(x,[]) and x not in MA.get(k,[]))] for k in T}; rank={}
    def r(k):
        if k not in rank: rank[k]=w(k)+max([r(x) for x in succ[k]],default=0)
        return rank[k]
    for k in T: r(k)
    rank['K1']=10**6  # T001 — один исполнитель: после контрактного коммита продолжает в том же слоте
    t=0;ev=[];free=N;frev=R;ready=[];revq=[];handed=set();merged={};started=set();approved=set();log={}
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
        while ready and (free>0 or (overflow and free>-1 and ready[0][0] in CR and ready[0][1]=='impl')):
            k,kind=ready.pop(0);free-=1;busy+=1;runs+=1
            if free<0: xtra[0]+=1
            d=w(k)*(rnd.uniform(.7,1.4) if seed>=0 else 1) if kind=='impl' else 7*(w(k)/10)*(rnd.uniform(.7,1.4) if seed>=0 else 1)
            if inline and k in SPINE and kind=='impl': revruns+=1
            log.setdefault(k,[]).append((kind,t,t+d))
            heapq.heappush(ev,(t+d,'hand',k))
        revq.sort(key=lambda k:-rank[k])
        while frev and revq:
            k=revq.pop(0);frev-=1;revruns+=1
            base=3 if (k=='C0' or (inline and k in SPINE)) else 8
            heapq.heappush(ev,(t+base*(rnd.uniform(.7,1.4) if seed>=0 else 1),'rev',k))
        for a,(ds,dur) in ACC.items():
            if a not in acc_st and acc_free and all((d in merged) or (d in acc_done) for d in ds):
                acc_st.add(a);acc_free-=1;heapq.heappush(ev,(t+dur*(rnd.uniform(.8,1.4) if seed>=0 else 1),'acc',a))
    disp()
    while ev:
        nt,e,k=heapq.heappop(ev);area+=busy*(nt-t);t=nt
        if e=='hand': free+=1;busy-=1;handed.add(k);revq.append(k)
        elif e=='rev':
            frev+=1
            pp=0 if k=='C0' else p*(0.7 if (inline and k in SPINE) else 1)
            if rounds[k]<2 and seed>=0 and rnd.random()<pp: rounds[k]+=1;ready.append((k,'rework'))
            else: approved.add(k);heapq.heappush(ev,(t+2,'mrg',k))
        elif e=='mrg': try_merge()
        elif e=='acc': acc_free+=1;acc_done[k]=t
        disp()
    H=merged['H']; end=max(max(acc_done.values()),H)+tailci
    if trace: return H,end,log,merged,acc_done,rank
    return H,end,area/H,runs,revruns,xtra[0]
if __name__=='__main__':
    mode=sys.argv[1] if len(sys.argv)>1 else 'r3'
    T,MA=graph(mode); w=mk(T)
    W=sum(w(k) for k in T);S,m=span(T,w)
    print(f'{mode}: задач {len(T)-1} (C0 — коммит T001), W={W:.0f} S={S:.0f} P={W/S:.2f}; K-фаза {sum(w(k) for k in T if T[k][0]=="K")/W:.0%}')
    # путь
    k=max(m,key=m.get);path=[k]
    while T[k][3]+T[k][4]:
        k=max(T[k][3]+T[k][4],key=lambda d:m[d]);path.append(k)
    print(' путь:',' <- '.join(path))
    for K in (3,4,5): print(f'  K={K}: {max(W/K,S):.0f}..{W/K+S:.0f}')
    print(' критические:',sorted(crit(T,w)))
    for p in (0.0,0.15,0.3,0.43):
        for K in (3,4,5):
            for ov in (False,True):
                if ov and K!=4: continue
                rs=[run(T,MA,K,max(K-1,2),p,s,False,overflow=ov) for s in range(400)]
                q=lambda j,f=0.5: sorted(r[j] for r in rs)[int(f*399)]
                print(f'p={p} K={K} ov={int(ov)}: H {q(0):.0f} (P90 {q(0,.9):.0f}), конец {q(1):.0f} (P90 {q(1,.9):.0f}), зан {st.mean(r[2] for r in rs):.2f}, исп {st.mean(r[3] for r in rs):.1f}, ревью {st.mean(r[4] for r in rs):.1f}, сверх K {st.mean(r[5] for r in rs):.2f}')
