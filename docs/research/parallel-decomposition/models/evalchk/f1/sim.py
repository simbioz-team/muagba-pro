"""Модель оценщика f1 r1. Добавлено к моделям команд:
- координатор: одна очередь на все действия (запуск, вердикт, вливание); вливание m мин
  (rebase, перегенерация, пробное слияние, check.sh группы), прочие действия c мин;
- CI партиями: всё влитое к концу прошлой проверки (>=3), длительность U(15,28);
  у каждой влитой задачи вероятность r покраснеть в полном прогоне (то, что группа не ловит);
  красная партия: бисекция ceil(log2 n) доп. прогонов, виновник снимается (зависимые, ещё
  не начатые, ждут), доработка 0.7w + ревью, повторное вливание;
- hidden: доп. работа у точки схождения (перевод неназначенных тестов), мин веса."""
import random, heapq, math, statistics as st, sys
from load import graphA, graphB
def sim(G, conv, K, R, p, r=0.15, m=(3,8), c=1.0, hidden=0, seed=0, ci=(15,28)):
    rnd=random.Random(seed)
    W={i:G[i]['w']+(hidden if i==conv else 0) for i in G}
    # rank (HLFET) by longest path to end via deps+stack+gates
    succ={i:[] for i in G}
    for i,x in G.items():
        for d in x['deps']+x['stack']+x['gates']: succ[d].append(i)
    memo={}
    def rk(i):
        if i not in memo: memo[i]=W[i]+max([rk(j) for j in succ[i]] or [0])
        return memo[i]
    for i in G: rk(i)
    submitted={}; merged={}; started=set(); rounds={i:0 for i in G}
    ready=[]; ev=[]; revq=[]; free=K; rfree=R
    coord=[0.0]; seq=[0]
    def push(t,*a): seq[0]+=1; heapq.heappush(ev,(t,seq[0])+a)
    def coord_do(now,dur):
        coord[0]=max(coord[0],now)+dur; return coord[0]
    def can_start(i):
        x=G[i]
        return all(d in merged for d in x['deps']) and all(d in submitted for d in x['stack'])
    def can_merge(i):
        x=G[i]
        return all(d in merged for d in x['deps']+x['stack']+x['gates'])
    approved=set(); inmq=set()
    def release(now):
        for i in G:
            if i not in started and can_start(i):
                started.add(i); heapq.heappush(ready,(-rk(i),i))
    def dispatch(now):
        nonlocal free,rfree
        while free>0 and ready:
            _,i=heapq.heappop(ready); free-=1
            t0=coord_do(now,c)
            dur=W[i]*(1 if rounds[i]==0 else 0.7)*rnd.uniform(0.7,1.4)
            push(t0+dur,'sub',i); WK[0]+=dur
        while rfree>0 and revq:
            i=revq.pop(0); rfree-=1
            t0=coord_do(now,c)
            push(t0+rnd.uniform(5,12)*(1 if rounds[i]==0 else 0.75),'rev',i)
    def try_merge(now):
        for i in sorted(approved, key=lambda j:-rk(j)):
            if i not in inmq and can_merge(i):
                inmq.add(i); t=coord_do(now, rnd.uniform(*m)); push(t,'mrg',i)
    WK=[0.0]; batch=[]; ci_busy=[False]; ci_runs=[0]; busy=0.0; last=[0.0]; reds=[0]
    release(0); dispatch(0); end=0
    while ev:
        now,_,e,i=heapq.heappop(ev)
        busy+=(K-free)*(now-last[0]); last[0]=now
        if e=='sub':
            free+=1; submitted.setdefault(i,now); revq.append(i); release(now)
        elif e=='rev':
            rfree+=1
            pf = p if rounds[i]==0 else (p/2 if rounds[i]==1 else 0)
            if rnd.random()<pf:
                rounds[i]+=1; heapq.heappush(ready,(-rk(i)-1000,i))
            else:
                if rounds[i]>=2 and rnd.random()<0.3: push(now+20,'appr',i)  # человек
                else: approved.add(i)
        elif e=='appr': approved.add(i)
        elif e=='mrg':
            approved.discard(i); inmq.discard(i); merged[i]=now; batch.append(i); end=max(end,now); release(now)
        elif e=='ciend':
            ci_busy[0]=False; b=i
            red=[x for x in b if not getattr(sim,'_cleared',set()).__contains__(x) and rnd.random()<r]
            if red:
                reds[0]+=1
                n=len(b); extra=math.ceil(math.log2(max(n,2)))*rnd.uniform(*ci); ci_runs[0]+=math.ceil(math.log2(max(n,2)))
                for x in red:
                    merged.pop(x,None)  # head reverted for x
                    push(now+extra,'redo',x)
        elif e=='redo':
            rounds[i]=max(rounds[i],1); heapq.heappush(ready,(-rk(i)-1000,i)); sim._cleared=getattr(sim,'_cleared',set())|{i}
        # CI start
        if not ci_busy[0] and (len(batch)>=3 or (batch and not ready and not revq and free==K)):
            b=batch[:]; batch.clear(); ci_busy[0]=True; ci_runs[0]+=1
            push(now+rnd.uniform(*ci),'ciend',b)
        try_merge(now); dispatch(now)
    sim._cleared=set()
    done=len(merged)==len(G)
    final=end+rnd.uniform(*ci)+30
    return final, WK[0]/max(end,1), ci_runs[0], reds[0], coord[0], done
def run(which, K, R, p, n=200, **kw):
    G,conv = graphA() if which=='A' else graphB()
    res=[sim(G,conv,K,R,p,seed=s,**kw) for s in range(n)]
    ends=sorted(x[0] for x in res)
    return dict(med=st.median(ends), p90=ends[int(.9*n)], busy=st.mean(x[1] for x in res),
                ci=st.mean(x[2] for x in res), reds=st.mean(x[3] for x in res), done=all(x[5] for x in res))
if __name__=='__main__':
    for which in 'AB':
        G,_=graphA() if which=='A' else graphB()
        print(which,'tasks',len(G),'W',round(sum(x['w'] for x in G.values())))
        for K,R in ((4,3),(5,4)):
            for p in (0.43,0.6):
                for label,kw in (('их модель~',dict(r=0,m=(2,3),c=0,hidden=0)),
                                 ('+коорд/влив',dict(r=0,m=(3,8),c=1,hidden=0)),
                                 ('+CI красн r=.15',dict(r=.15,m=(3,8),c=1,hidden=0)),
                                 ('+скрытые тесты',dict(r=.15,m=(3,8),c=1,hidden=40))):
                    o=run(which,K,R,p,**kw)
                    print(f"  K={K} R={R} p={p} {label:18s} med={o['med']:.0f} p90={o['p90']:.0f} busy={o['busy']:.2f} ci={o['ci']:.1f} red={o['reds']:.1f} done={o['done']}")
