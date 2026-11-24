import sys, io, contextlib, statistics as st
sys.path.insert(0, '../../../f1A2'); sys.path.insert(0, '../../f1B2')
with contextlib.redirect_stdout(io.StringIO()):
    import evsim2, runsim
    from tasks import T
    from probe import w
GB = {i: dict(w=w(i), deps=list(x['deps']), stack=list(x['stack']), gates=list(x['tdeps']) + list(x['mdeps']), kind=x['kind']) for i, x in T.items()}
GA, convA = runsim.graph()
def W(G): return sum(x['w'] for x in G.values())
print('A tasks', len(GA), 'W', W(GA), '| B tasks', len(GB), 'W', W(GB))
for name, G, conv in (('A', GA, convA), ('B', GB, 'T052')):
    for sc, kw in (('manual', dict(r=.15, m=(3, 8), c=1)), ('queue r.08', dict(r=.08, m=(2, 4), c=.5, sepmq=True)), ('queue r.15', dict(r=.15, m=(2, 4), c=.5, sepmq=True)), ('train1-2 c.3 r.15', dict(r=.15, m=(1, 2), c=.3, sepmq=True))):
        for K, R in ((3, 2), (4, 3), (5, 4)):
            res = [evsim2.sim(G, conv, K, R, 0.5, seed=s, **kw) for s in range(120)]
            e = sorted(x[0] for x in res)
            print(f'{name} {sc:18} K={K}: med {st.median(e):5.0f} p90 {e[int(.9*len(e))]:5.0f} busy {st.mean(x[1] for x in res):.2f} ci {st.mean(x[2] for x in res):.0f} done {all(x[5] for x in res)}')
