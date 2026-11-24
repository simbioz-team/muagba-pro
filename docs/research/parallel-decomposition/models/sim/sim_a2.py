"""Круг 2 команды A: стек по контрактному ребру с честным каскадом и
приёмочные тесты отдельной задачей. Событийная модель.
Задача стартует, когда каждое её ребро готово: 'c' (контракт) при STACK -
предок сдан; иначе - предок влит. Влить задачу можно только после вливания
предков. Если предок, на сданном коммите которого начат потомок, получил
'нельзя сливать', потомок с вероятностью q требует доработки (контракт
поменялся по сути), иначе rebase +3 мин."""
import random, statistics as st, heapq
IMPL,REVIEW,REWORK,MERGE,REBASE=10,8,7,2,3
def run(g,typ,deep,N,R,p,stack,q,seed,gate=None):
    rnd=random.Random(seed); gate=gate or {}
    d=lambda k,b: b*(1.6 if k in deep else 1)*rnd.uniform(0.7,1.4)
    sub=set(); mer=set(); started=set(); need_fix={}; extra={k:0.0 for k in g}
    ready=[]; revq=[]; ev=[]; t=0.0; fi=N; fr=R; seq=0; waiting_merge=set()
    busy=0; area=0.0
    def push(tt,kind,k):
        nonlocal seq; seq+=1; heapq.heappush(ev,(tt,seq,kind,k))
    def can_start(k):
        for x in g[k]:
            if stack and typ.get((x,k))=='c':
                if x not in sub: return False
            elif x not in mer: return False
        return True
    def can_merge(k): return all(x in mer for x in g[k]) and all(x in mer for x in gate.get(k,[])) and need_fix.get(k,0)==0
    def scan():
        for k in g:
            if k not in started and can_start(k): started.add(k); ready.append((k,'impl'))
        for k in list(waiting_merge):
            if can_merge(k): waiting_merge.discard(k); push(t+MERGE+extra[k],'merged',k)
    def disp():
        nonlocal fi,fr,busy
        while fi and ready:
            k,kind=ready.pop(0); fi-=1; busy+=1
            push(t+d(k,IMPL if kind=='impl' else REWORK),'submit',(k,kind))
        while fr and revq:
            k=revq.pop(0); fr-=1; push(t+d(k,REVIEW),'rev',k)
    scan(); disp()
    while ev:
        nt,_,kind,x=heapq.heappop(ev); area+=busy*(nt-t); t=nt
        if kind=='submit':
            k,kk=x; fi+=1; busy-=1
            if kk=='fix': need_fix[k]-=1; 
            if kk=='fix' and k in sub and k not in waiting_merge and k not in revq: revq.append(k)  # повторное ревью по находкам
            elif kk!='fix': sub.add(k); revq.append(k)
        elif kind=='rev':
            k=x; fr+=1
            if rnd.random()<p:
                ready.insert(0,(k,'rework'))
                # каскад на потомков, стартовавших от сданного коммита
                for c in g:
                    if k in g[c] and c in started and stack and typ.get((k,c))=='c':
                        if rnd.random()<q: need_fix[c]=need_fix.get(c,0)+1; ready.append((c,'fix'))
                        else: extra[c]+=REBASE
            else:
                waiting_merge.add(k)
        elif kind=='merged': mer.add(x)
        scan(); disp()
    return t, area/t
def contract(n=22,tests=0):
    g={'C1':[],'C2':[]}; typ={}; gate={}
    for i in range(n):
        g[f'V{i}']=['C1','C2']; typ[('C1',f'V{i}')]=typ[('C2',f'V{i}')]='c'
    for j in range(tests):
        g[f'AT{j}']=[]                      # пишутся по contracts.md, параллельно К
    if tests:
        for i in range(n): gate[f'V{i}']=[f'AT{i%tests}']
    g['H']=[f'V{i}' for i in range(n)]
    return g,typ,{'C1','C2'},gate
def layered():
    g={'F1':[],'F2':['F1'],'F3':['F2']}; typ={}
    for s in range(4):
        prev=['F3']
        for l in range(6):
            t=f'S{s}L{l}'; g[t]=prev+([f'S{s-1}L{l}'] if s and l<2 else []); prev=[t]
    g['P1']=[f'S{s}L5' for s in range(4)]; g['P2']=['P1']
    return g,typ,set(),{}
def M(g,typ,deep,gate,N=4,R=4,p=0.3,stack=False,q=0.3,n=300):
    r=[run(g,typ,deep,N,R,p,stack,q,s,gate) for s in range(n)]
    return st.mean(a for a,_ in r), st.mean(b for _,b in r)
print('1) послойный граф, все рёбра «поведение»: стека нет по правилу B')
g,typ,deep,gate=layered()
print('   конвейер без стека: %.0f мин' % M(g,typ,deep,gate)[0])
print('2) контракт К1||К2 (deep) + 22 среза + хвост, N=4, R=4, p=0.3')
g,typ,deep,gate=contract()
print('   без стека                      : %.0f мин, занято %.2f' % M(g,typ,deep,gate))
for q in (0.0,0.3,0.6):
    print('   стек по К, каскад q=%.1f        : %.0f мин, занято %.2f' % ((q,)+M(g,typ,deep,gate,stack=True,q=q)))
print('   p(K)=0.45 (ревью контракта строже), q=0.3: стек %.0f / без %.0f' % (
    M(g,typ,deep,gate,p=0.45,stack=True,q=0.3)[0], M(g,typ,deep,gate,p=0.45)[0]))
print('3) приёмочные тесты отдельными задачами по contracts.md, параллельно К')
for tests in (4,8):
    g,typ,deep,gate=contract(tests=tests)
    print('   %d задач тестов, без стека: %.0f мин, занято %.2f' % ((tests,)+M(g,typ,deep,gate)))
g,typ,deep,gate=contract(n=22+8)   # если тесты - задачи волны 0 на пути (как у B), грубо: +8 задач, блокирующих срезы
g2={'C1':[],'C2':[]}; t2={}
for j in range(8): g2[f'AT{j}']=['C1','C2']; t2[('C1',f'AT{j}')]=t2[('C2',f'AT{j}')]='c'
for i in range(22): g2[f'V{i}']=['C1','C2',f'AT{i%8}']; t2[('C1',f'V{i}')]=t2[('C2',f'V{i}')]='c'
g2['H']=[f'V{i}' for i in range(22)]
print('   8 задач тестов в волне 0 перед срезами (как у B), без стека: %.0f мин' % M(g2,t2,{'C1','C2'},{})[0])
print('4) p после мер (удержание+тесты по AC) = 0.15, лучший вариант')
g,typ,deep,gate=contract(tests=4)
print('   тесты параллельно К, стек q=0.3: %.0f мин; без стека: %.0f' % (M(g,typ,deep,gate,p=0.15,stack=True)[0], M(g,typ,deep,gate,p=0.15)[0]))
for N in (4,5):
    print('   N=%d: %.0f мин' % (N, M(g,typ,deep,gate,N=N,R=N,p=0.15,stack=True)[0]))
