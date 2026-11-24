"""Оценщик f2 r1: грубая событийная модель K -> веер -> H с очередью координатора.
Не повторяет модели команд: добавляет (1) последовательную очередь вливаний координатора,
(2) p фичи 2 = 0.61, (3) раздувание широкой K-задачи, (4) делёж слотов с шагом 6."""
import random, statistics, heapq, sys
A = dict(
 K={'T001':24,'T002':15,'T003':24,'T004':15},
 T=[10,15,15,10,15,10,10,10],
 V={'T013':15,'T014':15,'T015':10,'T016':15,'T017':24,'T018':24,'T019':24,'T020':24,'T021':24,
    'T022':16,'T026':10,'T023':24,'T024':24,'T025':24,'T027':24,'T028':15,'T029':15,'T030':24,
    'T031':24,'T032':10,'T033':15,'T034':10,'T035':24,'T036':16,'T037':10,'T038':10,'T039':24,
    'T040':16,'T041':10,'T042':10},
 chain={'T024':'T023','T040':'T039','T041':'T040'},
 mergeafter={x:'T013' for x in ['T019','T025','T028','T030','T031','T033']},
 broad='T002', H=15)
B = dict(
 K={'K1':24,'K2':15,'K3':10},
 T=[10,10,15,10,10,10,10,10],
 V={'V1':24,'V2':10,'V3':15,'V4':24,'V5':24,'V6':15,'V7':16,'V8':10,'V12a':15,'V12b':10,'V12c':10,
    'V9a':15,'V9b':10,'V10':15,'V11':15,'V22':24,'V20a':10,'V20b':24,'V19a':15,'V19b':15,'V19c':24,
    'V17a':15,'V17b':24,'V13':10,'V14':15,'V16':10},
 chain={}, mergeafter={}, broad='K2', H=15)

def run(plan, N, R, p, c, broad_x, rnd):
    # one task lifecycle returns list of (work, review) rounds
    def rounds(w):
        out=[(w*rnd.uniform(0.7,1.4), 8*rnd.uniform(0.6,1.5))]
        if rnd.random()<p:
            out.append((0.7*w*rnd.uniform(0.7,1.4), 6*rnd.uniform(0.6,1.5)))
            if rnd.random()<p/2:
                out.append((0.7*w*rnd.uniform(0.7,1.4), 6*rnd.uniform(0.6,1.5)))
        return out
    t=0.0
    slots=[0.0]*N; rev=[0.0]*R; coord=0.0
    def do(task_w, ready):
        nonlocal coord
        end=ready
        for w,rv in rounds(task_w):
            i=min(range(N), key=lambda k:slots[k]); s=max(slots[i], end); slots[i]=s+w; d=s+w
            j=min(range(R), key=lambda k:rev[k]); r=max(rev[j], d); rev[j]=r+rv; end=r+rv
        return end
    def merge(done):
        nonlocal coord
        coord=max(coord,done)+c; return coord
    # K and T start at 0
    Kw=dict(plan['K'])
    if broad_x: Kw[plan['broad']]*=broad_x
    kdone=[merge(do(w,0)) for w in sorted(Kw.values(), reverse=True)]
    tdone=[merge(do(w,0)) for w in plan['T']]
    kmerged=max(kdone)
    merged={}
    order=sorted(plan['V'], key=lambda x:-plan['V'][x])
    # chains: successor after predecessor submitted (stack) ~ approximate after predecessor done
    pending=[]
    for x in order:
        if x in plan['chain']: continue
        pending.append((do(plan['V'][x], kmerged), x))
    fin={x:e for e,x in pending}
    for x,pred in plan['chain'].items():
        # wait until pred chain resolved
        pass
    # resolve chains in order
    for x in ['T024','T040','T041']:
        if x in plan['chain']:
            fin[x]=do(plan['V'][x], fin[plan['chain'][x]]-8)
    for x in sorted(fin, key=lambda x: fin[x]):
        gate=max(fin[x], merged.get(plan['mergeafter'].get(x,''),0), max(tdone))
        merged[x]=merge(gate)
    h=merge(do(plan['H'], max(merged.values())))
    busy=sum(Kw.values())+sum(plan['T'])+sum(plan['V'].values())+plan['H']
    return h+21+30, busy

def stats(plan, N,R,p,c,bx, n=400):
    rnd=random.Random(7); xs=[run(plan,N,R,p,c,bx,rnd)[0] for _ in range(n)]
    xs.sort(); return round(statistics.median(xs)), round(xs[int(0.9*n)])
print("plan N R p  coord  broadK2x  -> median p90 (мин, вкл. CI 21 + приёмку 30)")
for name,plan in (('A',A),('B',B)):
    for N,R in ((4,3),(2,2)):
        for p in (0.43,0.61):
            for c in (2,6):
                for bx in (1,3):
                    print(name,N,R,p,c,bx, stats(plan,N,R,p,c,bx))
