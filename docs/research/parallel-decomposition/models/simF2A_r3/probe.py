"""Проба плана по design §5: W, S, P, фаза K, ранги."""
from plan import T, W
import functools
succ = {k: [] for k in T}
for k, v in T.items():
    for d in v[3] + v[4]: succ[d].append(k)
# ребро [T] -> срезы истории (для ранга, design замечание r1 §9 п.1)
story = {}
for k, v in T.items():
    if v[0] in 'VS': story.setdefault(v[5], []).append(k)
for k, v in T.items():
    if v[0] == 'T': succ[k] += story[v[5]]
@functools.lru_cache(None)
def rank(k): return W[k] + max([rank(s) for s in succ[k]], default=0)
Wt = sum(W.values())
# S по рёбрам старта (без ребра [T] -> срез)
s2 = {k: [] for k in T}
for k, v in T.items():
    for d in v[3] + v[4]: s2[d].append(k)
@functools.lru_cache(None)
def r2(k): return W[k] + max([r2(s) for s in s2[k]], default=0)
S = max(r2(k) for k in T); Sr = max(rank(k) for k in T)
K = sum(W[k] for k, v in T.items() if v[0] == 'K')
from collections import Counter
print('задач', len(T), Counter(v[0] for v in T.values()), 'deep', sum(v[1] == 'deep' for v in T.values()))
print('W', Wt, 'S', S, 'S(с ребром [T])', Sr, 'P', round(Wt / S, 2), round(Wt / Sr, 2), 'K-фаза', K, round(K / Wt * 100, 1), '%')
for Kk in (2, 3, 4, 5): print('K', Kk, 'границы', round(max(Wt / Kk, S)), '…', round(Wt / Kk + S), '  P>=2K' if Wt / S >= 2 * Kk else ('  предупр.' if Wt / S >= Kk else '  красное'))
for k in sorted(T, key=lambda k: -rank(k)): print(k, T[k][0], W[k], 'ранг', rank(k))
