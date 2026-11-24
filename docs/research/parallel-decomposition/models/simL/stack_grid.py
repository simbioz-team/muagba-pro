"""Ведущий: сетка p x q для стека по контрактному ребру на веере 22 (модель B sim2, ce = рёбра К->V)."""
import sys; sys.path.insert(0, sys.argv[1])
import sim2
def fanc(n):
    g,deep,w,_=sim2.fan(n); ce={(c,f'V{i}') for i in range(n) for c in ('C1','C2')}
    return g,deep,w,ce
for n in (22,8):
  G=fanc(n)
  print('веер',n)
  for p in (0.2,0.3,0.43):
    base=sim2.m(G,4,3,p,'pipe')[0]
    row=[sim2.m(G,4,3,p,'stack',q)[0] for q in (0.2,0.4,0.6)]
    print(f' p={p}: без стека {base:.0f}; стек q=.2/.4/.6: '+' / '.join(f'{x:.0f}' for x in row))
