"""Событийная модель круга 3 (основа — f1B2/sim.py, проверка оценщика — evalchk/r2/simB_poison.py).
Изменения против круга 2:
  * красная партия: деление пополам находит виновника; виновник ОТКАТЫВАЕТСЯ с ветки плана (revert
    через поезд, 1–2 мин), вместе с влитыми после него потомками; потомки ждут повторного вливания
    виновника и вливаются заново без доработки; остальные члены партии идут в CI повторно
    (политика GitLab merge train: упавший MR выбывает, поезд пересобирается);
  * fix='forward' — исправление вперёд с отравлением ветки (как simB_poison: CI стоит до исправления);
  * приоритет фазы К: [K] выдаются раньше всех (иначе HLFET ставит T005 на 118-ю минуту);
  * p у [T] и [H] — 0.15; у перевода тестов p_mech (по умолчанию = p).
"""
import random, heapq, math, statistics as st, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tasks3 import T
from probe3 import w, allp
MECH = {'T066', 'T067', 'T068', 'T069', 'T070', 'T071', 'T072', 'T074'}
def rank(kfirst=True):
    succ = {i: [j for j in T if i in allp(j)] for i in T}; m = {}
    def r(i):
        if i not in m: m[i] = w(i) + max((r(j) for j in succ[i]), default=0)
        return m[i]
    return {i: r(i) + ((1000 if T[i]['kind'] == 'K' else 500 if T[i]['kind'] == 'T' else 0) if kfirst else 0) for i in T}
DESC = {}
def desc(i):
    if i not in DESC:
        DESC[i] = set()
        for j in T:
            if i in T[j]['deps'] + T[j]['stack']: DESC[i] |= {j} | desc(j)
    return DESC[i]

def run(K, R, p, seed, r=0.15, B=8, ci=(15, 28), mdur=(1, 2), cdur=0.3, accept=30, fix='revert', kfirst=True,
        p_mech=None, ext_delay=0, gcheck=None, attr=False, p2=None):
    RK = rank(kfirst); rnd = random.Random(seed); U = rnd.uniform
    pm = p if p_mech is None else p_mech
    ev = []; seq = [0]
    def push(t, kind, x=None): seq[0] += 1; heapq.heappush(ev, (t, seq[0], kind, x))
    now = 0.0; free = K; frev = R; busy = 0; area = 0.0
    ready = []; revq = []; mq = []; ciq = []
    started = set(); handed = set(); merged = set(); green = set(); waitm = set(); morder = []
    bad = set(); poison = set(); state = dict(mq=False, ci=False, coord=False); coordq = []
    cnt = dict(runs=0, revs=0, checks=0, reverts=0, red=0)
    rounds = {}; seen_bad = set()
    def startable(i):
        if T[i]['ext'] and now < ext_delay: return False
        return all(d in merged for d in T[i]['deps']) and all(d in handed for d in T[i]['stack'])
    def mergeable(i): return all(d in merged for d in allp(i))
    def release():
        for i in T:
            if i not in started and startable(i): started.add(i); ready.append((i, 'impl'))
        for i in list(waitm):
            if mergeable(i): waitm.discard(i); mq.append(('merge', i))
    def kick():
        nonlocal free, frev, busy
        ready.sort(key=lambda x: (x[1] == 'impl', -RK[x[0]]))
        while free and ready:
            i, k = ready.pop(0); free -= 1; busy += 1; cnt['runs'] += 1
            f = 1 if k == 'impl' else (0.7 if k == 'rework' else 0.5)
            push(now + cdur + w(i) * U(.7, 1.4) * f, 'submit', i)
        while frev and revq:
            i = revq.pop(0); frev -= 1; cnt['revs'] += 1; push(now + cdur + max(U(5, 12), U(*gcheck) if gcheck else 0), 'rev', i)
        if not state['mq'] and mq:
            mq.sort(key=lambda x: (x[0] != 'revert', -RK[x[1]])); job = mq.pop(0); state['mq'] = True
            push(now + U(*mdur), 'mq', job)
        if not state['ci'] and ciq and not (fix == 'forward' and poison):
            batch = ciq[:B]; del ciq[:B]; state['ci'] = True; cnt['checks'] += 1
            bads = [b for b in batch if b in bad]
            if attr:
                # приписка по группе: кандидаты ~половина партии, check.sh группы по 3 параллельно, откат 2 мин; CI ждёт (иначе голова отравлена)
                ex = (math.ceil(math.ceil(len(batch)/2)/3) * U(6, 10) + 2) if bads else 0
                push(now + U(*ci) + ex, 'ci', (tuple(batch), tuple(bads)))
            else:
                extra = len(bads) * math.ceil(math.log2(len(batch))) if bads and len(batch) > 1 else 0
                cnt['checks'] += extra
                push(now + sum(U(*ci) for _ in range(1 + extra)), 'ci', (tuple(batch), tuple(bads)))
    release(); kick()
    while ev:
        nt, _, kind, x = heapq.heappop(ev); area += busy * (nt - now); now = nt
        if kind == 'submit':
            free += 1; busy -= 1; handed.add(x); revq.append(x)
        elif kind == 'rev':
            frev += 1; n = rounds.get(x, 0)
            pp = 0.15 if T[x]['kind'] in 'TH' else (pm if x in MECH else p)
            pp = pp if (n == 0 or p2 is None or T[x]['kind'] in 'TH') else pp * p2
            if rnd.random() < pp and n < 3: rounds[x] = n + 1; ready.append((x, 'rework'))
            else: waitm.add(x)
        elif kind == 'mq':
            state['mq'] = False; op, i = x
            if op == 'merge':
                merged.add(i); morder.append(i); ciq.append(i); poison.discard(i)
                if i not in seen_bad and rnd.random() < r: bad.add(i)
                seen_bad.add(i)
            else:  # revert: убрать виновника и влитых после него потомков
                cnt['reverts'] += 1
        elif kind == 'ci':
            state['ci'] = False; batch, bads = x
            good = [b for b in batch if b not in bads]
            if not bads: green.update(batch)
            else:
                cnt['red'] += 1
                for c in bads:
                    bad.discard(c); seen_bad.discard(c)   # исправленная версия снова тянет r
                    if fix == 'forward':
                        poison.add(c); ready.append((c, 'fix'))
                    else:
                        d = desc(c); back = [b for b in morder if b in d and b in merged]
                        for b in [c] + back:
                            merged.discard(b); green.discard(b)
                            if b in ciq: ciq.remove(b)
                        morder[:] = [b for b in morder if b not in back and b != c]
                        mq.append(('revert', c)); handed.discard(c); ready.append((c, 'fix'))
                        for b in back: waitm.add(b); seen_bad.add(b)  # их код не менялся
                        good = [g for g in good if g not in back]
                green.update(good)
        release(); kick()
        if len(green) == len(T) and not ev: break
    end = now + accept
    return dict(end=end, occ=area / end, **cnt)

def sim(K, R, p, n=120, **kw):
    rs = [run(K, R, p, s, **kw) for s in range(n)]
    return {k: st.mean(x[k] for x in rs) for k in rs[0]}, sorted(x['end'] for x in rs)
