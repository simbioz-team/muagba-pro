"""Событийная модель оценщика (f2 r1). Отличия от моделей команд:
coord — последовательная очередь вливаний координатора (мин на вливание);
p фичи 2 по бейзлайну 0.61; bx — раздувание широкой K-задачи (T002/K2);
N — слоты, доступные фиче 2 (делёж с шагом 6)."""
import random, statistics, heapq
from evsim import A, B
def sim(plan,N,R,p,c,bx,rnd):
    W={}; kind={}; dep={}; mdep={}
    for k,w in plan['K'].items(): W[k]=w*(bx if k==plan['broad'] else 1); kind[k]='K'; dep[k]=[]
    for i,w in enumerate(plan['T']): t=f'TT{i}'; W[t]=w; kind[t]='T'; dep[t]=[]
    Ks=list(plan['K']); Ts=[f'TT{i}' for i in range(len(plan['T']))]
    for v,w in plan['V'].items():
        W[v]=w; kind[v]='V'; dep[v]=Ks if v not in plan['chain'] else [plan['chain'][v]]
    W['H']=plan['H']; kind['H']='H'; dep['H']=list(plan['V'])
    # stack edges: chain successor may start when predecessor submitted
    stack=set(plan['chain'])
    prio={k: (3 if kind[k]=='K' else 2 if kind[k]=='T' else 1)*100+W[k] for k in W}
    submitted={}; mergedt={}; rounds={k:0 for k in W}
    t=0; free=N; rfree=R; ready=[]; ev=[]; revq=[]; mq=[]; coord=0.0
    started=set()
    def can_start(k):
        if k in started: return False
        for d in dep[k]:
            if k in stack:
                if d not in submitted: return False
            elif d not in mergedt: return False
        return True
    def push_ready(now):
        for k in W:
            if k not in started and can_start(k):
                started.add(k); heapq.heappush(ready,(-prio[k],k,'work'))
    push_ready(0)
    def dispatch(now):
        nonlocal free,rfree
        while free>0 and ready:
            _,k,_=heapq.heappop(ready); free-=1
            w=W[k]*(1 if rounds[k]==0 else 0.7)*rnd.uniform(0.7,1.4)
            heapq.heappush(ev,(now+w,'sub',k))
        while rfree>0 and revq:
            k=revq.pop(0); rfree-=1
            heapq.heappush(ev,(now+8*rnd.uniform(0.6,1.5)*(1 if rounds[k]==0 else 0.75),'rev',k))
    dispatch(0); last=0; busy=0.0; lastt=0
    while ev:
        now,e,k=heapq.heappop(ev)
        busy+=(N-free)*(now-lastt); lastt=now
        if e=='sub':
            free+=1; submitted.setdefault(k,now); revq.append(k)
        elif e=='rev':
            rfree+=1
            fail = rounds[k]<2 and rnd.random() < (p if rounds[k]==0 else p/2)
            if fail:
                rounds[k]+=1; heapq.heappush(ready,(-(prio[k]+50),k,'work'))
            else:
                gate=now
                if kind[k]=='V':
                    # merge after story's [T] (approx: all T) and mergeafter
                    pass
                coord=max(coord,now)+c
                heapq.heappush(ev,(coord,'mrg',k))
        elif e=='mrg':
            ma=plan['mergeafter'].get(k)
            if kind[k]=='V' and (any(t_ not in mergedt for t_ in Ts) or (ma and ma not in mergedt)):
                heapq.heappush(ev,(now+5,'mrg',k)); continue
            mergedt[k]=now; last=now; push_ready(now)
        dispatch(now)
    kend=max(mergedt[k] for k in Ks)
    return last+21+30, busy/last, kend
def stats(plan,N,R,p,c,bx,n=400):
    rnd=random.Random(11); r=[sim(plan,N,R,p,c,bx,rnd) for _ in range(n)]
    xs=sorted(x[0] for x in r)
    return round(statistics.median(xs)), round(xs[int(.9*n)]), round(statistics.mean(x[1] for x in r),2), round(statistics.median(x[2] for x in r))
if __name__=='__main__':
    print('план N R p coord bx -> медиана p90 занятость конецK (мин; +CI 21 +приёмка 30)')
    for name,plan in (('A',A),('B',B)):
        for N,R in ((4,3),(5,4),(2,2)):
            for p in (0.43,0.61):
                for c,bx in ((0,1),(6,1),(6,3)):
                    print(name,N,R,p,c,bx,stats(plan,N,R,p,c,bx))
