"""Монте-Карло: граф задач x режим цикла -> время фичи и средняя занятость.
Длительности из наблюдений narta 20-24.11: impl 7-10 мин, review 5-12, доработка 19-33%."""
import random, statistics as st, sys

def layered():
    g={}
    g['F1']=[];g['F2']=['F1'];g['F3']=['F2']
    layers=['model','svc','api','client','ui','e2e']
    for s in range(4):
        prev=['F3']
        for i,l in enumerate(layers):
            t=f'S{s}{l}'
            deps=list(prev)
            if s>0 and l in('model','svc'): deps.append(f'S{s-1}{l}')  # общая сущность -> очередь
            g[t]=deps; prev=[t]
    g['P1']=[f'S{s}e2e' for s in range(4)];g['P2']=['P1'];g['P3']=['P2']
    return g

def planned():
    g={}
    g['C1']=[];g['C2']=[]          # контракт: схема/типы/порты, заглушки, 2 задачи параллельно
    g['C3']=['C1','C2']            # сгенерированный клиент + фикстуры приёмки
    for s in range(6):             # 6 срезов x 3 задачи: сервер, клиент, сценарий
        g[f'S{s}srv']=['C3'];g[f'S{s}cli']=['C3'];g[f'S{s}flow']=[f'S{s}srv',f'S{s}cli']
    g['I1']=[f'S{s}flow' for s in range(3)];g['I2']=[f'S{s}flow' for s in range(3,6)];g['D1']=['I1','I2']
    return g

PRIO=True
def ranks(g):
    succ={x:[y for y in g if x in g[y]] for x in g}; memo={}
    def r(x):
        if x not in memo: memo[x]=1+max((r(y) for y in succ[x]),default=0)
        return memo[x]
    return {x:r(x) for x in g}
def shape(g):
    rk=ranks(g); cp=max(rk.values()); return len(g),cp,len(g)/cp
def dur(a,b): return random.uniform(a,b)

def run(g,mode,K=4,R=4,p=0.3,merge=2.0):
    rank=ranks(g)
    # mode 'serial': слот исполнителя держится до вливания, преемник стартует после вливания
    # mode 'pipe' : слот свободен при сдаче; ревью в своём пуле; преемник по контракту
    #               стартует от сданного коммита (стек), при доработке +rebase 3 мин
    done={};handed={};t=0;busy=[];rev=[];events=[]
    ready_time={}
    order=list(g)
    remaining=set(g); impl_free=[0.0]*K; rev_free=[0.0]*R
    # простая дискретная симуляция по списку: жадно, топологически по готовности
    fin={}; start={}
    import heapq
    pending=set(g); running={}  # task->end
    clock=0.0; imp_busy=[]; util=0.0
    timeline=[]
    while pending:
        # кандидаты
        cand=[]
        for x in pending:
            if mode=='serial': okt=[fin.get(d) for d in g[x]]
            else: okt=[handed.get(d) for d in g[x]]
            if all(v is not None for v in okt): cand.append((max(okt,default=0),x))
        i=min(range(K),key=lambda k:impl_free[k])
        now=max(impl_free[i],min(c[0] for c in cand))
        avail=[c for c in cand if c[0]<=now] if PRIO else [min(cand)]
        tr,x=max(avail,key=lambda c:(rank[c[1]],-c[0])) if PRIO else avail[0]
        s=max(tr,impl_free[i]); im=dur(7,10)
        if mode=='pipe' and any(fin.get(d,0)>s for d in g[x]): im+=3*p  # ожидаемый rebase на доработку предка
        h=s+im
        j=min(range(R),key=lambda k:rev_free[k]); rs=max(h,rev_free[j]); re=rs+dur(5,12)
        if random.random()<p:
            rw=dur(5,9); rr=dur(4,8)
            if mode=='serial': end=re+rw+rr; impl_free[i]=end; rev_free[j]=end
            else:
                # доработку берёт свободный исполнитель новым запуском (кэш умер)
                i2=min(range(K),key=lambda k:impl_free[k]); ws=max(re,impl_free[i2]); impl_free[i2]=ws+rw
                end=ws+rw+rr; rev_free[j]=end; impl_free[i]=h
        else:
            end=re; impl_free[i]= end if mode=='serial' else h; rev_free[j]=re
        handed[x]=h; fin[x]=end+merge; start[x]=s
        timeline.append((s, h if mode=='pipe' else end))
        pending.discard(x)
    T=max(fin.values())
    work=sum(b-a for a,b in timeline)
    return T, work/T

for name,g in(('layered',layered()),('planned',planned())):
  n,cp,w=shape(g); print(f'{name}: задач {n}, критический путь {cp} задач, средняя ширина {w:.1f}')
  for K in (4,5):
    for mode in('serial','pipe'):
        rs=[run(g,mode,K=K,R=K) for _ in range(2000)]
        print(f'  K={K} {mode:6} tasks={len(g)} T={st.mean(r[0] for r in rs):6.0f} мин  занятость исполнителей={st.mean(r[1] for r in rs):.2f}')
print('чувствительность к доле отказов (K=4):')
import statistics as st
for p in (0.2,0.3,0.43):
    for name,g in(('layered',layered()),('planned',planned())):
        for mode in('serial','pipe'):
            T=st.mean(run(g,mode,K=4,R=4,p=p)[0] for _ in range(1500))
            print(f'  p={p} {name:8} {mode:6} T={T:5.0f}')
