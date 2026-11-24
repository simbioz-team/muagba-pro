"""sim.py r3 + CI. ci='trail': ветка плана движется без ожидания CI, CI партии идёт следом
на `runners` раннерах (общих с шагом 6: доля `share` занята им); красная партия (вероятность red)
— одна задача партии откатывается revert'ом и идёт на доработку. ci='gate': потомки стартуют
и вливаются только от проверенного CI коммита (буквальное правило «ветка перематывается после
зелёного»). Итог = последнее проверенное CI + приёмка 30 (в 'trail' CI хвоста уже внутри)."""
import random, heapq, statistics, sys
from plan import T, W
from probe import rank
COST = {'deep': 4.9, 'обычный': 0.94}
def sim(N, R, p, c, rnd, ci='trail', red=0.0, runners=3, share=0.5, mode='serial', bx=None, force=()):
    Wl = dict(W)
    for k, m in (bx or {}).items(): Wl[k] *= m
    tests = {}
    for k, v in T.items():
        if v[0] == 'T': tests.setdefault(v[5], []).append(k)
    started, submitted, merged, verified = set(), {}, {}, {}
    rounds = {k: 0 for k in T}
    ready, ev, revq, mq, ciq = [], [], [], [], []
    free, rfree = N, R; coord_busy = False
    # раннеры: часть занята шагом 6 — моделируем как случайную задержку старта
    rfree_ci = runners
    busy = 0.0; lastt = 0.0; cost = 0.0
    class Vis:
        def __contains__(self, d):
            if ci == 'gate' or (ci == 'hybrid' and T[d][0] == 'K'): return d in verified
            return d in merged
    vis = Vis()
    def can_start(k):
        v = T[k]
        return all(d in vis for d in v[3]) and all(d in submitted for d in v[4])
    def push_ready():
        for k in T:
            if k not in started and can_start(k):
                started.add(k); heapq.heappush(ready, (-rank(k), k))
    def gate_ok(k):
        v = T[k]
        if v[0] in 'VS' and any(t not in vis for t in tests[v[5]]): return False
        return all(d in vis for d in v[3]) and all(d in merged for d in v[4])
    def dispatch(now):
        nonlocal free, rfree, coord_busy, cost, rfree_ci
        while free and ready:
            _, k = heapq.heappop(ready); free -= 1
            d = Wl[k] * (1 if rounds[k] == 0 else 0.7) * rnd.uniform(0.7, 1.4)
            cost += COST[T[k][1]]
            heapq.heappush(ev, (now + d, 'sub', k))
        revq.sort(key=lambda k: -rank(k))
        while rfree and revq:
            k = revq.pop(0); rfree -= 1; cost += 1.5
            heapq.heappush(ev, (now + 8 * rnd.uniform(0.6, 1.5) * (1 if rounds[k] == 0 else 0.75), 'rev', k))
        if not coord_busy:
            ok = [k for k in mq if gate_ok(k)]
            if ok:
                if mode == 'serial': ok = [max(ok, key=rank)]; dur = c
                else: dur = 4 + 2 * len(ok)
                for k in ok: mq.remove(k)
                coord_busy = True
                heapq.heappush(ev, (now + dur, 'mrg', tuple(ok)))
        if rfree_ci and ciq:
            batch = tuple(ciq); ciq.clear(); rfree_ci -= 1
            wait = rnd.uniform(0, 15) if rnd.random() < share else 0   # раннер занят шагом 6
            heapq.heappush(ev, (now + wait + rnd.uniform(15, 28), 'ci', batch))
    push_ready(); dispatch(0)
    while ev:
        now, e, k = heapq.heappop(ev)
        busy += (N - free) * (now - lastt); lastt = now
        if e == 'sub':
            free += 1; submitted.setdefault(k, now); revq.append(k)
        elif e == 'rev':
            rfree += 1
            if rounds[k] == 0 and k in force: fail = True
            else: fail = rounds[k] < 2 and rnd.random() < (p if rounds[k] == 0 else p / 2)
            if fail: rounds[k] += 1; heapq.heappush(ready, (-(rank(k) + 50), k))
            else: mq.append(k)
        elif e == 'mrg':
            coord_busy = False
            for x in k: merged[x] = now
            ciq.extend(k)
            push_ready()
        elif e == 'ci':
            rfree_ci += 1
            if rnd.random() < red and len(k):
                bad = rnd.choice(k); del merged[bad]; rounds[bad] += 1
                heapq.heappush(ready, (-(rank(bad) + 50), bad))
                k = tuple(x for x in k if x != bad)
            for x in k: verified[x] = now
            push_ready()
        dispatch(now)
    last = max(verified.values())
    return last + 30, busy / last, cost
def stats(N, R, p, c, n=400, **kw):
    rnd = random.Random(11); r = [sim(N, R, p, c, rnd, **kw) for _ in range(n)]
    xs = sorted(x[0] for x in r)
    return dict(med=round(statistics.median(xs)), p90=round(xs[int(.9 * n)]),
                busy=round(statistics.mean(x[1] for x in r), 2), cost=round(statistics.mean(x[2] for x in r)))
if __name__ == '__main__':
    for N, R in ((4, 3), (2, 2), (3, 2), (5, 4)):
        for p in (0.43, 0.61):
            for ci, red in (('trail', 0), ('trail', 0.15), ('hybrid', 0), ('hybrid', 0.15), ('gate', 0), ('gate', 0.15)):
                for mode in ('serial', 'batch'):
                    print(N, R, p, ci, red, mode, stats(N, R, p, 6, ci=ci, red=red, mode=mode))
