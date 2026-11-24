# тот же граф, но режим "сегодня": слот держится до вливания, [T]-задач нет (тесты пишет исполнитель среза: +40% к весу среза), E-подготовки нет
import sys,os; sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import random, heapq, statistics as st, f3b_r3
T0,MA0=f3b_r3.graph("r3")
T={k:v[:5] for k,v in T0.items() if v[0]!='T' and k!='C0'}
T={k:(v[0],v[1],v[2],[d for d in v[3] if d in T],[d for d in v[4] if d in T]) for k,v in T.items()}
MA={k:[d for d in v if d in T] for k,v in MA0.items() if k in T}
def w(k):
    v,d,s,_,_=T[k]; base=10*(1.6 if d else 1)*(1.5 if s=='M' else 1)
    return base*(1.4 if v in ('V','S') else 1)
def run(N,R,p,seed):
    rnd=random.Random(seed); succ={k:[x for x in T if k in T[x][3]+T[x][4]] for k in T}; rank={}
    def r(k):
        if k not in rank: rank[k]=w(k)+max([r(x) for x in succ[k]],default=0)
        return rank[k]
    for k in T: r(k)
    t=0;ev=[];free=N;frev=R;ready=[];revq=[];merged={};started=set();rounds={k:0 for k in T};busy=0
    def can(k): return all(d in merged for d in T[k][3]+T[k][4])
    def disp():
        nonlocal free,frev
        for k in T:
            if k not in started and can(k): started.add(k);ready.append(k)
        ready.sort(key=lambda k:-rank[k])
        while free and ready:
            k=ready.pop(0);free-=1;heapq.heappush(ev,(t+w(k)*rnd.uniform(.7,1.4),'hand',k))
        while frev and revq:
            k=revq.pop(0);frev-=1;heapq.heappush(ev,(t+8*rnd.uniform(.7,1.4),'rev',k))
    disp()
    while ev:
        t,e,k=heapq.heappop(ev)
        if e=='hand': revq.append(k)
        elif e=='rev':
            frev+=1
            if rounds[k]<2 and rnd.random()<p: rounds[k]+=1;heapq.heappush(ev,(t+7*(w(k)/10)*rnd.uniform(.7,1.4),'hand',k))
            else: heapq.heappush(ev,(t+2,'mrg',k))
        elif e=='mrg': merged[k]=t;free+=1
        disp()
    return merged['H']
for p in (0.0,0.3,0.43):
    for K in (4,):
        print(p,K,st.median(run(K,K-1,p,s) for s in range(400)))
