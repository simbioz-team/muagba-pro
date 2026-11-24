"""Событийная модель f2-A-r2. Ближе к evalchk/evsim2.py, плюс:
- рёбра задачи свои (не «все V ждут все K»), K→K (T005), стек (T021 от сданного T020);
- очередь вливаний координатора: c мин на вливание, последовательно; ждущий ворот
  (своя [T], предки) координатора НЕ занимает (в evsim2 занимает и повторяется каждые 5 мин);
- режим 'batch': координатор берёт все годные разом, цена 4 + 2·n;
- ранг HLFET (с ребром [T] → срезы истории), доработка — ранг + 50;
- force: принудительный отказ задачи на первом ревью; bx: множитель веса задач из BX.
Итог = вливание хвоста + 21 (CI последней партии) + 30 (приёмка), как у оценщика."""
import random, heapq, statistics, sys
from plan import T, W
from probe import rank
COST = {'deep': 4.9, 'обычный': 0.94}
def sim(N, R, p, c, rnd, mode='serial', bx=None, force=()):
    Wl = dict(W)
    for k, m in (bx or {}).items(): Wl[k] *= m
    tests = {}
    for k, v in T.items():
        if v[0] == 'T': tests.setdefault(v[5], []).append(k)
    started, submitted, merged = set(), {}, {}
    rounds = {k: 0 for k in T}
    ready, ev, revq, mq = [], [], [], []
    free, rfree = N, R; coord_busy = False
    busy = 0.0; lastt = 0.0; cost = 0.0; runs = 0; reviews = 0
    def can_start(k):
        v = T[k]
        return all(d in merged for d in v[3]) and all(d in submitted for d in v[4])
    def push_ready():
        for k in T:
            if k not in started and can_start(k):
                started.add(k); heapq.heappush(ready, (-rank(k), k))
    def gate_ok(k):
        v = T[k]
        if v[0] in 'VS' and any(t not in merged for t in tests[v[5]]): return False
        return all(d in merged for d in v[3] + v[4])
    def dispatch(now):
        nonlocal free, rfree, coord_busy, cost, runs, reviews
        while free and ready:
            _, k = heapq.heappop(ready); free -= 1
            d = Wl[k] * (1 if rounds[k] == 0 else 0.7) * rnd.uniform(0.7, 1.4)
            cost += COST[T[k][1]]; runs += 1
            heapq.heappush(ev, (now + d, 'sub', k))
        revq.sort(key=lambda k: -rank(k))
        while rfree and revq:
            k = revq.pop(0); rfree -= 1; cost += 1.5; reviews += 1
            heapq.heappush(ev, (now + 8 * rnd.uniform(0.6, 1.5) * (1 if rounds[k] == 0 else 0.75), 'rev', k))
        if not coord_busy:
            ok = [k for k in mq if gate_ok(k)]
            if ok:
                if mode == 'serial':
                    ok = [max(ok, key=rank)]; dur = c
                else:
                    dur = 4 + 2 * len(ok)
                for k in ok: mq.remove(k)
                coord_busy = True
                heapq.heappush(ev, (now + dur, 'mrg', tuple(ok)))
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
            if fail:
                rounds[k] += 1; heapq.heappush(ready, (-(rank(k) + 50), k))
            else: mq.append(k)
        elif e == 'mrg':
            coord_busy = False
            for x in k: merged[x] = now
            push_ready()
        dispatch(now)
    last = max(merged.values())
    kend = max(merged[k] for k, v in T.items() if v[0] == 'K')
    return last + 21 + 30, busy / last, kend, cost, runs, reviews
def stats(N, R, p, c, mode='serial', bx=None, force=(), n=400):
    rnd = random.Random(11); r = [sim(N, R, p, c, rnd, mode, bx, force) for _ in range(n)]
    xs = sorted(x[0] for x in r)
    m = lambda i: statistics.mean(x[i] for x in r)
    return dict(med=round(statistics.median(xs)), p90=round(xs[int(.9 * n)]), busy=round(m(1), 2),
                kend=round(statistics.median(x[2] for x in r)), cost=round(m(3)), runs=round(m(4), 1), rev=round(m(5), 1))
if __name__ == '__main__':
    print('N R p c режим bx force -> медиана p90 занятость конецK $ запусков ревью')
    rows = []
    for N, R in ((4, 3), (5, 4), (3, 2), (2, 2)):
        for p in (0.43, 0.61, 0.25):
            for c, mode in ((0, 'serial'), (6, 'serial'), (6, 'batch'), (3, 'serial')):
                print(N, R, p, c, mode, '-', '-', stats(N, R, p, c, mode))
    for N, R in ((4, 3), (2, 2)):
        for bx, f in (({'T004': 3}, ('T004',)), ({'T003': 3}, ('T003',)), ({'T004': 3, 'T003': 3}, ('T004', 'T003'))):
            print(N, R, 0.43, 6, 'serial', bx, f, stats(N, R, 0.43, 6, 'serial', bx, f))
            print(N, R, 0.61, 6, 'serial', bx, f, stats(N, R, 0.61, 6, 'serial', bx, f))
