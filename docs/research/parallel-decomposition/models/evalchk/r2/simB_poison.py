"""Событийная модель фичи с ценой координатора, очереди вливаний и CI.
Ресурсы: K исполнителей, R ревьюеров, координатор (один, последовательно), очередь вливаний
(одна, последовательно), CI (одна проверка за раз, 15–28 мин, партия до B).
Режимы:
  manual — координатор сам: 1 мин на каждую выдачу (запуск исполнителя/ревьюера) и 3–8 мин на вливание;
  queue  — вливание делает скрипт (очередь последовательная, 3–8 мин: rebase, генерируемое, check группы),
           координатор только 1 мин на выдачу;
  auto   — и выдача скриптом (task_pairs.py next), координатор 0; очередь как в queue.
Ревью 5–12 мин, исполнитель вес×U(0.7,1.4), доработка 0.7×вес. p — доля «нельзя сливать» на круг.
CI: красная партия с вероятностью 1-(1-r)^n; деление пополам ceil(log2 n) лишних проверок;
виновник — исправление вперёд (0.5×вес, ревью, вливание) и снова в CI. Зависимые не ждут CI
(стартуют от ветки плана после вливания и check группы), конец — когда всё влито и зелено, + 30 мин приёмки.
"""
import random, heapq, math, statistics as st, sys
import sys; sys.path.insert(0, '../../f1B2')
from tasks import T
from probe import w, allp

def rank():
    succ = {i: [j for j in T if i in allp(j)] for i in T}; m = {}
    def r(i):
        if i not in m: m[i] = w(i) + max((r(j) for j in succ[i]), default=0)
        return m[i]
    return {i: r(i) for i in T}
RK = rank()

def run(K, R, p, seed, mode='queue', r=0.10, B=4, ext_delay=0, accept=30, mdur=(3, 8), cdur=1.0, ci=(15, 28)):
    rnd = random.Random(seed); U = rnd.uniform
    ev = []; seq = [0]
    def push(t, kind, i=None): seq[0] += 1; heapq.heappush(ev, (t, seq[0], kind, i))
    now = 0.0; free = K; frev = R
    ready = []; revq = []; coordq = []; mq = []; ciq = []
    started = set(); handed = set(); merged = set(); green = set(); waitm = set()
    coord_busy = False; mq_busy = False; ci_busy = False
    poison = set()
    busy = 0; area = 0.0; runs = 0; reviews = 0; checks = 0; coord_time = 0.0; merge_time = 0.0
    def startable(i):
        if T[i]['ext'] and now < ext_delay: return False
        return all(d in merged for d in T[i]['deps']) and all(d in handed for d in T[i]['stack'])
    def mergeable(i): return all(d in merged for d in T[i]['deps'] + T[i]['stack'] + T[i]['tdeps'] + T[i]['mdeps'])
    def coord(job):  # job = ('impl', i, kind) | ('rev', i) | ('merge', i)
        nonlocal coord_busy
        if mode == 'auto' and job[0] != 'merge': return dispatch_now(job)
        coordq.append(job); kick()
    def dispatch_now(job):
        nonlocal busy, runs, reviews
        if job[0] == 'impl':
            _, i, k = job; busy += 1; runs += 1
            dur = w(i) * U(.7, 1.4) * (1 if k == 'impl' else (0.7 if k == 'rework' else 0.5))
            push(now + dur, 'submit', i)
        elif job[0] == 'rev':
            reviews += 1; push(now + U(5, 12), 'rev', job[1])
    def kick():
        nonlocal coord_busy, mq_busy, ci_busy, coord_time, merge_time, checks
        if not coord_busy and coordq:
            coordq.sort(key=lambda j: (j[0] == 'merge', -RK[j[1]]))
            job = coordq.pop(0); coord_busy = True
            d = U(*mdur) if job[0] == 'merge' else cdur; coord_time += d
            push(now + d, 'coord_done', job)
        if not mq_busy and mq:
            mq.sort(key=lambda i: -RK[i]); i = mq.pop(0); mq_busy = True
            d = U(*mdur); merge_time += d; push(now + d, 'merged', i)
        if not ci_busy and ciq and not (POISON and poison):
            batch = ciq[:B]; del ciq[:B]; ci_busy = True; checks += 1
            if POISON and poison:
                red = 'poisoned'; extra = 0
            else:
                red = rnd.random() < 1 - (1 - r) ** len(batch)
                extra = math.ceil(math.log2(len(batch))) if red and len(batch) > 1 else 0
            checks += extra
            push(now + sum(U(*ci) for _ in range(1 + extra)), 'ci', (tuple(batch), red))
    def take():
        nonlocal free
        ready.sort(key=lambda x: (x[1] == 'impl', -RK[x[0]]))
        while free and ready:
            i, k = ready.pop(0); free -= 1
            if mode == 'auto': dispatch_now(('impl', i, k))
            else: coordq.append(('impl', i, k))
        nonlocal_frev()
        kick()
    def nonlocal_frev():
        nonlocal frev
        while frev and revq:
            i = revq.pop(0); frev -= 1
            if mode == 'auto': dispatch_now(('rev', i))
            else: coordq.append(('rev', i))
    def release():
        for i in T:
            if i not in started and startable(i): started.add(i); ready.append((i, 'impl'))
        for i in list(waitm):
            if mergeable(i):
                waitm.discard(i)
                if mode == 'manual': coordq.append(('merge', i))
                else: mq.append(i)
    release(); take()
    rounds = {}
    while ev:
        nt, _, kind, i = heapq.heappop(ev); area += busy * (nt - now); now = nt
        if kind == 'coord_done':
            coord_busy = False
            if i[0] == 'merge': push(now, 'merged', i[1])
            else: dispatch_now(i)
        elif kind == 'submit':
            free += 1; busy -= 1; handed.add(i); revq.append(i)
        elif kind == 'rev':
            frev += 1
            pp = 0.15 if T[i]['kind'] in 'TH' else p
            n = rounds.get(i, 0)
            if rnd.random() < pp and n < 3: rounds[i] = n + 1; ready.append((i, 'rework'))
            else: waitm.add(i)
        elif kind == 'merged':
            if mode != 'manual': mq_busy = False
            poison.discard(i)
            merged.add(i); ciq.append(i)
        elif kind == 'ci':
            ci_busy = False; batch, red = i
            if red == 'poisoned':
                ciq[:0] = list(batch)  # результата нет: ветка плана красная, перепроверить после исправления
            elif red:
                culprit = rnd.choice(batch)
                if POISON: poison.add(culprit); green.update(b for b in batch if b != culprit)
                merged.discard(culprit)  # исправление вперёд: снова исполнитель, ревью, вливание, CI
                handed.discard(culprit); ready.append((culprit, 'fix'))
                # merged.discard не откатывает уже стартовавших зависимых: они стартовали от ветки плана
                merged.add(culprit); merged_fix.add(culprit)
            else: green.update(batch)
        release(); take()
        if len(green) == len(T) and not ev: break
    end = now + accept
    return end, area / end, runs, reviews, checks, coord_time, merge_time
merged_fix = set()
POISON = True

def sim(K, R, p, n=200, **kw):
    rs = [run(K, R, p, s, **kw) for s in range(n)]
    return [st.mean(x[k] for x in rs) for k in range(7)]


if __name__ == '__main__':
    import sys
    for pz in (False, True):
        POISON = pz
        for r in (0.10, 0.20):
            for B in (3, 4, 8):
                e, occ, runs, revs, ch, ct, mt = sim(4, 3, 0.43, 120, mode='queue', r=r, B=B, mdur=(1, 2), cdur=0.3)
                print(f"poison={pz} r={r} B={B}: {e:5.0f} мин, занято {occ:.2f}, CI {ch:.0f}")
