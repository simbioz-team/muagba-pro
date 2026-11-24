"""Калибровка: план r1 (evalchk/evsim.py A) в модели sim.py; все V ждут все K и все [T], как в evsim2."""
import sys; sys.path.insert(0, '../evalchk')
import io, contextlib
with contextlib.redirect_stdout(io.StringIO()):
    from evsim import A
import plan, probe, functools
T = {}
for k, w_ in A['K'].items(): T[k] = ('K', 'deep' if w_ > 20 else 'обычный', 'M', [], [], None)
for i, w_ in enumerate(A['T']): T[f'TT{i}'] = ('T', 'обычный', 'S', [], [], 'ALL')
Ks = list(A['K'])
for v, w_ in A['V'].items():
    st = [A['chain'][v]] if v in A['chain'] else []
    deps = Ks + ([A['mergeafter'][v]] if v in A['mergeafter'] else [])
    T[v] = ('V', 'deep' if w_ in (16, 24) else 'обычный', 'M', deps, st, 'ALL')
T['H'] = ('H', 'обычный', 'M', list(A['V']), [], None)
W = {k: w_ for k, w_ in A['K'].items()}; W.update({f'TT{i}': w_ for i, w_ in enumerate(A['T'])}); W.update(A['V']); W['H'] = A['H']
plan.T.clear(); plan.T.update(T); plan.W.clear(); plan.W.update(W)
succ = {k: [] for k in T}
for k, v in T.items():
    for d in v[3] + v[4]: succ[d].append(k)
for k, v in T.items():
    if v[0] == 'T': succ[k] += [x for x, y in T.items() if y[0] == 'V']
@functools.lru_cache(None)
def rank(k): return W[k] + max([rank(s) for s in succ[k]], default=0)
import sim
sim.T = T; sim.W = W; sim.rank = rank
# все [T] как одна история: ворота среза — все [T]
orig_sim = sim.sim
def gate_all(*a, **kw): return orig_sim(*a, **kw)
for N, R in ((4, 3), (2, 2)):
    for p in (0.43, 0.61):
        print('r1', N, R, p, 'c=6', sim.stats(N, R, p, 6))
