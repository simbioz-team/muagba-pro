"""Круг 2 команды B: проверка спорных пунктов с командой A.
Событийная модель (как sim_a.py), длительности A: impl 10 (deep x1.6), review 8, rework 7, merge 2, разброс 0.7-1.4.
Режимы:
  block  - слот держится до вливания, зависимость по вливанию (сейчас)
  pipe   - слот свободен при сдаче, зависимость по вливанию (позиция A)
  stack  - pipe + преемник по контрактному ребру стартует от сданного; если предок ушёл на доработку,
           преемник, уже начавший, с вероятностью q делает доп. запуск 'rework' (каскад)
Графы:
  A-fan    - К1||К2 -> 22 полных среза -> хвост  (граф A)
  B-split  - К1||К2 -> 11 срезов x (srv||cli -> flow)=33 -> хвост
  B-fan2K  - то же число сценариев, но срезы полные, где сценариев >=2K; 8 срезов (мало)
  ladder   - мои послойные 4 истории х 6 слоёв + сущность, связывающая истории
"""
import random, statistics as st, heapq, sys
IMPL,REVIEW,REWORK,MERGE=10,8,7,2
def fan(n, kpar=True, size=1.0):
    g={'C1':[], 'C2':([] if kpar else ['C1'])}; w={}
    for i in range(n): g[f'V{i}']=['C1','C2']; w[f'V{i}']=size
    g['H']=[f'V{i}' for i in range(n)]
    return g,{'C1','C2'},w,set()
def split(n):
    g={'C1':[], 'C2':[]}; w={}; contract_edges=set()
    for i in range(n):
        g[f'S{i}s']=['C1','C2']; g[f'S{i}c']=['C1','C2']; g[f'S{i}f']=[f'S{i}s',f'S{i}c']
        for t in ('s','c'): w[f'S{i}{t}']=0.6
        w[f'S{i}f']=0.5
        contract_edges |= {(f'S{i}s',f'S{i}f'),(f'S{i}c',f'S{i}f')}
    g['H']=[f'S{i}f' for i in range(n)]
    return g,{'C1','C2'},w,contract_edges
def ladder():
    g={'F1':[],'F2':['F1']}; ce=set()
    L=['m','s','a','c','u','e']
    for s in range(4):
        prev='F2'
        for l in L:
            t=f'U{s}{l}'; g[t]=[prev]+([f'U{s-1}{l}'] if s and l in 'ms' else []); ce.add((prev,t)); prev=t
    g['H']=[f'U{s}e' for s in range(4)]
    return g,set(),{},ce
def ranks(g,w):
    succ={x:[y for y in g if x in g[y]] for x in g}; m={}
    def r(x):
        if x not in m: m[x]=w.get(x,1)+max((r(y) for y in succ[x]),default=0)
        return m[x]
    return {x:r(x) for x in g}
def run(G,N,R,p,mode,q,seed):
    g,deep,w,ce=G; rnd=random.Random(seed); rk=ranks(g,w)
    def dur(k,base): return base*w.get(k,1)*(1.6 if k in deep else 1)*rnd.uniform(.7,1.4)
    ev=[];t=0.0;free=N;frev=R;ready=[];revq=[];merged=set();handed=set();started=set();hold={}
    busy=0;area=0;reworkpending=set();extra=0
    def push(a,b,c): heapq.heappush(ev,(a,b,c))
    def dep_ok(c,d):
        if d in merged: return True
        return mode=='stack' and (d,c) in ce and d in handed
    def release():
        for c,ds in g.items():
            if c not in started and all(dep_ok(c,d) for d in ds):
                started.add(c); ready.append((c,'impl'))
    def disp():
        nonlocal free,frev,busy
        ready.sort(key=lambda x:(x[1]=='impl',-rk[x[0]]))
        while free and ready:
            k,kind=ready.pop(0); free-=1; busy+=1
            push(t+dur(k,IMPL if kind=='impl' else REWORK),'submit',(k,kind))
        while frev and revq:
            k=revq.pop(0); frev-=1; push(t+dur(k,REVIEW),'rev',k)
    release(); disp()
    while ev:
        nt,kind,x=heapq.heappop(ev); area+=busy*(nt-t); t=nt
        if kind=='submit':
            k,_=x
            if mode!='block': free+=1; busy-=1
            else: hold[k]=1
            handed.add(k); revq.append(k)
        elif kind=='rev':
            k=x; frev+=1
            if rnd.random()<p:
                if mode=='block': push(t+dur(k,REWORK),'sub2',k)
                else:
                    ready.append((k,'rework'))
                    if mode=='stack':  # каскад на уже начатых преемников по стеку
                        for c,ds in g.items():
                            if k in ds and c in started and (k,c) in ce and rnd.random()<q:
                                ready.append((c,'rework')); extra+=1
            else: push(t+MERGE,'merged',k)
        elif kind=='sub2': revq.append(x)
        elif kind=='merged':
            merged.add(x)
            if mode=='block' and hold.pop(x,None): free+=1; busy-=1
        release(); disp()
    return t, area/t
def m(G,N,R,p,mode,q=0.0,n=300):
    rs=[run(G,N,R,p,mode,q,s) for s in range(n)]
    return st.mean(r[0] for r in rs), st.mean(r[1] for r in rs)
if __name__=='__main__':
    graphs={'A-fan22':fan(22),'B-split11x3':split(11),'A-fan8':fan(8),'B-split4x3':split(4),'ladder':ladder()}
    print('граф            N  block      pipe       stack q=0  stack q=.5')
    for nm,G in graphs.items():
        for N in (4,5):
            row=[m(G,N,4,0.3,'block'),m(G,N,4,0.3,'pipe'),m(G,N,4,0.3,'stack',0),m(G,N,4,0.3,'stack',.5)]
            print(f'{nm:14s} {N}  '+'  '.join(f'{a:4.0f}/{b:.1f}' for a,b in row))
    print('--- R (ревьюеров) при N=4, p=0.43, A-fan22 pipe')
    for R in (1,2,3,4):
        print(' R',R, '%.0f/%.1f'%m(fan(22),4,R,0.43,'pipe'))
    print('--- K последовательно против параллельно, A-fan22 pipe N=4')
    print(' К1->К2 %.0f, К1||К2 %.0f'%(m(fan(22,False),4,4,.3,'pipe')[0], m(fan(22),4,4,.3,'pipe')[0]))
