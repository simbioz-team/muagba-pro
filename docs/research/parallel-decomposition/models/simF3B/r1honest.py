import sys,os; sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import f3b2, statistics as st
orig=f3b2.w
def w(k): return 34 if k=='K1' else orig(k)
f3b2.w=w
W=sum(w(k) for k in f3b2.T); S,_=f3b2.span(); print('r1 honest W',W,'S',S,'P',round(W/S,2))
for p in (0,0.15,0.3,0.43):
    rs=[f3b2.run(4,3,p,s,True,False) for s in range(400)]
    print(p, st.median(r[0] for r in rs), st.median(r[1] for r in rs))
