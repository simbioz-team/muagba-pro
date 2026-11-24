import importlib.util, sys, io, contextlib
SP='/tmp/claude-1000/-home-rustam-develop-simbioz-team-muagba-pro/e280ef6f-cbe4-4a58-b39a-164383171093/scratchpad/'
def _load(path, name):
    spec=importlib.util.spec_from_file_location(name, path); m=importlib.util.module_from_spec(spec)
    with contextlib.redirect_stdout(io.StringIO()): spec.loader.exec_module(m)
    return m
def graphA():
    m=_load(SP+'f1A/plan.py','f1aplan')
    G={}
    for i,x in m.T.items():
        G[i]=dict(w=m.w(x), deps=list(x['deps']), stack=[], gates=list(x['gates']), kind=x['kind'])
    # stack T048->T049 (B3a->B3b)
    if 'B3b' in G and 'B3a' in G['B3b']['deps']:
        G['B3b']['deps'].remove('B3a'); G['B3b']['stack'].append('B3a')
    return G, 'S2'   # convergence task (T044)
def graphB():
    m=_load(SP+'decomp/f1B/plan.py','f1bplan')
    G={}
    for i,x in m.T.items():
        G[i]=dict(w=m.w(i), deps=list(x['deps']), stack=list(x['stack']), gates=list(x['tdeps']), kind=x['kind'])
    return G, 'T052'
