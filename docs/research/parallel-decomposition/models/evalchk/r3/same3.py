# Оценщик r3: оба графа в обеих моделях (A: evsim3, B: sim3).
import sys, io, contextlib, statistics as st, os
S='/tmp/claude-1000/-home-rustam-develop-simbioz-team-muagba-pro/e280ef6f-cbe4-4a58-b39a-164383171093/scratchpad'
sys.path.insert(0, S+'/f1A3'); sys.argv=[sys.argv[0]]
with contextlib.redirect_stdout(io.StringIO()):
    import plan
import evsim3
sys.path.insert(0, S+'/decomp/f1B3')
import tasks3, probe3, sim3
def gA():
    return {i:dict(w=plan.w(x),deps=list(x['deps']),stack=list(x['stack']),gates=list(x['gates']),kind=x['kind']) for i,x in plan.T.items()}
def gB():
    T=tasks3.T
    return {i:dict(w=probe3.w(i),deps=list(T[i]['deps']),stack=list(T[i]['stack']),gates=list(T[i]['tdeps'])+list(T[i]['mdeps']),kind=T[i]['kind']) for i in T}
def runA(G,K,R,p,n=120,**kw):
    res=[evsim3.sim(G,None,K,R,p,seed=s,**kw) for s in range(n)]
    e=sorted(x[0] for x in res); return st.median(e), st.mean(x[1] for x in res), st.mean(x[2] for x in res)
# A-граф в модель B
origT=dict(tasks3.T)
def toB(G):
    return {i:dict(kind=x['kind'] if x['kind'] in 'KTVSH' else 'V',deps=x['deps'],stack=x['stack'],tdeps=x['gates'],mdeps=[],ext=False,deep=False,M=False,_w=x['w'],files=set(),tests=set()) for i,x in G.items()}
def runB(G,K,R,p,n=100,**kw):
    TB=toB(G) if G is not None else origT
    sim3.T.clear(); sim3.T.update(TB); sim3.DESC.clear()
    if G is not None:
        sim3.w=lambda i: sim3.T[i]['_w']; sim3.MECH=set()
    else:
        sim3.w=probe3.w; sim3.MECH={'T066','T067','T068','T069','T070','T071','T072','T074'}
    m,ends=sim3.sim(K,R,p,n,**kw); return m['end'], m['occ'], m['checks'], m['runs']/len(TB)
A=gA(); B=gB()
print('W A',sum(x['w'] for x in A.values()),'W B',sum(x['w'] for x in B.values()))
QA=dict(r=.15,m=(2,4),c=.5,sepmq=True,attr=True)
for K in (3,4,5):
    for p in (0.55,0.72):
        a=runA(A,K,K-1,p,**QA); b=runA(B,K,K-1,p,**QA)
        print(f'модель A (очередь, приписка, r=.15) K={K} p={p}: граф A {a[0]:.0f}/{a[1]:.2f}/ci{a[2]:.0f}  граф B {b[0]:.0f}/{b[1]:.2f}/ci{b[2]:.0f}')
for K in (3,4,5):
    for p in (0.55,0.72):
        for tag,kw in (('как есть r.15 B4',dict(r=.15,B=4)),('группы r.05 B8',dict(r=.05,B=8,gcheck=(6,12))),('группы r.10 B8',dict(r=.10,B=8,gcheck=(6,12)))):
            a=runB(A,K,K-1,p,**kw); b=runB(None,K,K-1,p,**kw)
            print(f'модель B {tag} K={K} p={p}: граф A {a[0]:.0f}/{a[1]:.2f}/ci{a[2]:.0f}/запусков на задачу {a[3]:.2f}  граф B {b[0]:.0f}/{b[1]:.2f}/ci{b[2]:.0f}/{b[3]:.2f}')
