import sys,os; sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import f3b_r2 as M, variants as V
T,MA=M.graph(os.environ.get('MODE','r2pull')); T=dict(T); MA={k:list(v) for k,v in MA.items()}
getattr(V,sys.argv[1])(T,MA)
H,end,log,merged,acc,rank=M.run(T,MA,int(sys.argv[2]) if len(sys.argv)>2 else 4,3,0,-1,trace=True)
for k,ls in sorted(log.items(),key=lambda x:x[1][0][1]):
    for kind,a,b in ls: print(f'{k:4} {kind:6} {a:5.0f}-{b:5.0f} влита {merged.get(k,0):5.0f} ранг {rank[k]:.0f}')
print('H',H,'acc',acc,'end',end)
