"""Детерминированное расписание (p = 0, без шума, ревью 8, вливание c) с журналом."""
import heapq, sys
from plan import T, W
from probe import rank
def run(N, R, c, batch=False, kci=21):
    tests = {v[5]: k for k, v in T.items() if v[0] == 'T'}
    started, sub, mer, vis = set(), {}, {}, {}; st = {}; slot_of = {}
    ready, ev, revq, mq = [], [], [], []; free = list(range(1, N + 1)); rfree = R; cb = False
    def can(k): v = T[k]; return all(d in vis for d in v[3]) and all(d in sub for d in v[4])
    def gate(k):
        v = T[k]
        return (v[0] not in 'VS' or tests[v[5]] in vis) and all(d in vis for d in v[3]) and all(d in mer for d in v[4])
    def push():
        for k in T:
            if k not in started and can(k): started.add(k); heapq.heappush(ready, (-rank(k), k))
    def disp(now):
        nonlocal rfree, cb
        while free and ready:
            _, k = heapq.heappop(ready); s = free.pop(0); slot_of[k] = s; st[k] = now
            heapq.heappush(ev, (now + W[k], 'sub', k))
        revq.sort(key=lambda k: -rank(k))
        while rfree and revq:
            k = revq.pop(0); rfree -= 1; heapq.heappush(ev, (now + 8, 'rev', k))
        if not cb:
            ok = [k for k in mq if gate(k)]
            if ok:
                if batch: grp = ok; dur = 4 + 2 * len(ok)
                else: grp = [max(ok, key=rank)]; dur = c
                for x in grp: mq.remove(x)
                cb = True; heapq.heappush(ev, (now + dur, 'mrg', tuple(grp)))
    push(); disp(0)
    while ev:
        now, e, k = heapq.heappop(ev)
        if e == 'sub': free.append(slot_of[k]); free.sort(); sub[k] = now; revq.append(k)
        elif e == 'rev': rfree += 1; mq.append(k)
        elif e == 'vis':
            for x in k: vis[x] = now
            push()
        else:
            cb = False
            for x in k:
                mer[x] = now
                if T[x][0] == 'K': heapq.heappush(ev, (now + kci, 'vis', (x,)))
                else: vis[x] = now
            push()
        disp(now)
    for k in sorted(T, key=lambda k: st[k]):
        print(f"| {k} {T[k][0]} | {slot_of[k]} | {st[k]:.0f} | {sub[k]:.0f} | {mer[k]:.0f} |" + (f" CI {vis[k]:.0f}" if T[k][0]=="K" else ""))
    print('конец', max(mer.values()))
run(int(sys.argv[1]), int(sys.argv[2]), float(sys.argv[3]), sys.argv[4] == 'batch', float(sys.argv[5]))
