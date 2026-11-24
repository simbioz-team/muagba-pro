"""Мысленная проверка команды A: слои против контракт+срезы.
Дискретная симуляция: N исполнителей, R ревьюеров, вероятность доработки p.
Режим blocking: слот исполнителя занят до вливания (как сейчас).
Режим pipelined: исполнитель освобождается при сдаче; доработка — новый запуск в общую очередь.
Зависимость освобождается при вливании."""
import random, statistics, heapq

IMPL, REVIEW, REWORK, MERGE = 10, 8, 7, 2
def graph_layered():
    # Spec Kit-подобно: setup 2 подряд, foundational 4 (2 уровня по 2), 4 истории x 5 слоёв цепочкой, polish 2
    g = {}
    g['S1']=[]; g['S2']=['S1']
    g['F1']=['S2']; g['F2']=['S2']; g['F3']=['F1','F2']; g['F4']=['F1','F2']
    for s in range(4):
        prev=['F3','F4']
        for l in range(5):
            t=f'U{s}L{l}'; g[t]=prev[:]; prev=[t]
    last=[f'U{s}L4' for s in range(4)]
    g['P1']=last; g['P2']=['P1']
    return g, set()
def graph_contract():
    g={}
    g['C1']=[]; g['C2']=['C1']  # контракт: схемы+модели+миграция, затем заглушки/клиент/контрактные тесты
    for i in range(22):
        g[f'V{i}']=['C2']
    g['I1']=[f'V{i}' for i in range(22)]; g['I2']=['I1']  # сборка/регистрация и хвост
    return g, {'C1','C2'}
def run(g, deep, N, R, p, pipelined, seed):
    rnd=random.Random(seed)
    done=set(); merged_at={}
    t=0.0; ev=[]; free_impl=N; free_rev=R
    ready=[k for k,v in g.items() if not v]; revq=[]; started=set()
    busy=0; busy_area=0.0; last=0.0
    def dur(k,base): return base*(1.6 if k in deep else 1.0)*rnd.uniform(0.7,1.4)
    def push(time,kind,k): heapq.heappush(ev,(time,kind,k))
    def dispatch():
        nonlocal free_impl,free_rev,busy
        while free_impl>0 and ready:
            k,kind=ready.pop(0) if isinstance(ready[0],tuple) else (ready.pop(0),'impl')
            free_impl-=1; busy+=1
            push(t+dur(k,IMPL if kind=='impl' else REWORK),'submit',(k,kind))
        while free_rev>0 and revq:
            k=revq.pop(0); free_rev-=1
            push(t+dur(k,REVIEW),'reviewed',k)
    ready=[(k,'impl') for k in ready]
    holding={}
    dispatch()
    while ev:
        nt,kind,x=heapq.heappop(ev)
        busy_area+=busy*(nt-t); t=nt
        if kind=='submit':
            k,_=x
            if pipelined: free_impl+=1; busy-=1
            else: holding[k]=True
            revq.append(k)
        elif kind=='reviewed':
            k=x; free_rev+=1
            if rnd.random()<p:
                if pipelined: ready.insert(0,(k,'rework'))
                else: push(t+dur(k,REWORK),'submit2',k)
            else:
                push(t+MERGE,'merged',k)
        elif kind=='submit2':
            revq.append(x)
        elif kind=='merged':
            k=x; done.add(k)
            if not pipelined and holding.pop(k,None): free_impl+=1; busy-=1
            for c,deps in g.items():
                if c not in done and c not in started and all(d in done for d in deps):
                    started.add(c); ready.append((c,'impl'))
        dispatch()
    return t, busy_area/t
for name,(g,deep) in {'слои':graph_layered(),'контракт+срезы':graph_contract()}.items():
    for pip in (False,True):
        for N in (4,5):
            res=[run(g,deep,N,3,0.3,pip,s) for s in range(200)]
            print(f"{name:15s} N={N} {'конвейер' if pip else 'блок.   '} задач={len(g)} время={statistics.mean(r[0] for r in res):6.0f} мин  занято исполнителей={statistics.mean(r[1] for r in res):.2f}")
print('--- ревьюеры R и доля доработок p, контракт+срезы, конвейер, N=4')
g,deep=graph_contract()
for R in (2,3,4,6):
    for p in (0.3,0.15):
        res=[run(g,deep,4,R,p,True,s) for s in range(200)]
        print(f"R={R} p={p}: время={statistics.mean(r[0] for r in res):5.0f}")
g,deep=graph_layered()
res=[run(g,deep,4,6,0.3,True,s) for s in range(200)]
print('слои R=6:', round(statistics.mean(r[0] for r in res)))
print('--- контракт широкий: C1||C2, регистрация в контракте, один хвост')
def graph_contract2(n=22):
    g={'C1':[], 'C2':[]}
    for i in range(n): g[f'V{i}']=['C1','C2']
    g['I1']=[f'V{i}' for i in range(n)]
    return g,{'C1','C2'}
for N in (4,5):
  for p in (0.3,0.15):
    g,deep=graph_contract2()
    res=[run(g,deep,N,4,p,True,s) for s in range(300)]
    print(f"N={N} p={p}: время={statistics.mean(r[0] for r in res):5.0f} занято={statistics.mean(r[1] for r in res):.2f}")
