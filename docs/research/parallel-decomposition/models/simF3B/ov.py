import sys,os; sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import f3b_r2 as M, statistics as st
T,MA=M.graph('r2pull')
for K in (3,4,5):
  for p in (0,0.15,0.3,0.43):
    for inl in (False,True):
      rs=[M.run(T,MA,K,max(K-1,2),p,s,inline=inl,overflow=True) for s in range(400)]
      print(f'OV K={K} p={p} inline={int(inl)}: H {st.median(r[0] for r in rs):.0f} (P90 {sorted(r[0] for r in rs)[360]:.0f}), конец {st.median(r[1] for r in rs):.0f} (P90 {sorted(r[1] for r in rs)[360]:.0f}), зан {st.mean(r[2] for r in rs):.2f}, исп {st.mean(r[3] for r in rs):.1f}, ревью {st.mean(r[4] for r in rs):.1f}')
