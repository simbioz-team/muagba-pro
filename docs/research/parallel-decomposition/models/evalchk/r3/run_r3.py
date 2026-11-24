import sys, io, contextlib
sys.path.insert(0,'.')
S='/tmp/claude-1000/-home-rustam-develop-simbioz-team-muagba-pro/e280ef6f-cbe4-4a58-b39a-164383171093/scratchpad'
sys.path.insert(0, S+'/f1A3'); sys.argv=['x']
with contextlib.redirect_stdout(io.StringIO()):
    import plan
sys.path.insert(0, S+'/decomp/f1B3')
import tasks3, probe3
import simB_attr as sb
origT=dict(tasks3.T); MECHB={'T066','T067','T068','T069','T070','T071','T072','T074'}
GA={i:dict(kind=x['kind'],deps=list(x['deps']),stack=list(x['stack']),tdeps=list(x['gates']),mdeps=[],ext=False,_w=plan.w(x)) for i,x in plan.T.items()}
def run(which,K,p,n=100,**kw):
    sb.T.clear(); sb.DESC.clear()
    if which=='A': sb.T.update(GA); sb.w=lambda i: sb.T[i]['_w']; sb.MECH=set()
    else: sb.T.update(origT); sb.w=probe3.w; sb.MECH=MECHB
    m,e=sb.sim(K,K-1,p,n,**kw); return f"{m['end']:.0f} (p90 {e[int(.9*len(e))]:.0f}) з{m['occ']:.2f} ci{m['checks']:.0f} зап{m['runs']/len(sb.T):.2f}"
for K in (3,4,5):
  for p,p2 in ((0.55,0.6),(0.72,0.6)):
    for tag,kw in (('приписка r.15',dict(r=.15,B=999,attr=True)),
                   ('приписка r.22',dict(r=.22,B=999,attr=True)),
                   ('приписка r.15, очередь гоняет группу 6-10',dict(r=.15,B=999,attr=True,mdur=(6,10))),
                   ('группы при сдаче r.05 + приписка',dict(r=.05,B=999,attr=True,gcheck=(6,12))),
                   ('CI общий с шагом 8: 22-42',dict(r=.15,B=999,attr=True,ci=(22,42)))):
      print(f"K={K} p={p}/{p2} {tag:42}: A {run('A',K,p,p2=p2,**kw)} | B {run('B',K,p,p2=p2,**kw)}",flush=True)
