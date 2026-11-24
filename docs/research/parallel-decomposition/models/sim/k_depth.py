"""Глубина волны 0: К1||К2 против К1||К2 -> К3 (как у B). Остальное как в sim_a2."""
from sim_a2 import run, contract, M
g,typ,deep,gate=contract(tests=4)
g3=dict(g); t3=dict(typ); g3['C3']=['C1','C2']; t3[('C1','C3')]=t3[('C2','C3')]='c'
for k in g3:
    if k.startswith('V'): g3[k]=['C3']; t3[('C3',k)]='c'
for p in (0.3,0.15):
    a=M(g,typ,deep,gate,p=p,stack=True)[0]; b=M(g3,t3,deep|{'C3'},gate,p=p,stack=True)[0]
    print(f'p={p}: глубина 1 {a:.0f} мин, глубина 2 {b:.0f} мин (+{b-a:.0f})')
